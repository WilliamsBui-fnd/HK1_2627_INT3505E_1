import hashlib
import ipaddress
import json
import secrets
import time
from functools import wraps

from flask import g, jsonify, request

from common import ApiError, base_app, configure_basic, json_body, new_order, owner_orders
from database import get_db, load_user


def key_metadata(row):
    data = dict(row)
    data.pop("hash")
    data["scopes"] = json.loads(data["scopes"])
    data["ip_allowlist"] = json.loads(data["ip_allowlist"])
    return data


def mint_key(user, scopes, expires_in=3600, ip_allowlist=None):
    ip_allowlist = [] if ip_allowlist is None else ip_allowlist
    if not isinstance(scopes, list) or not scopes or any(not isinstance(s, str) for s in scopes):
        raise ApiError("invalid_request", "scopes phải là danh sách chuỗi không rỗng.")
    if not set(scopes).issubset(user["scopes"]):
        raise ApiError("insufficient_scope", "Không thể cấp quyền vượt quá quyền của chủ key.", 403)
    if type(expires_in) is not int or not 1 <= expires_in <= 2592000:
        raise ApiError("invalid_request", "expires_in phải từ 1 đến 2592000 giây.")
    if not isinstance(ip_allowlist, list) or any(not isinstance(ip, str) for ip in ip_allowlist):
        raise ApiError("invalid_request", "ip_allowlist phải là danh sách CIDR.")
    try:
        networks = [str(ipaddress.ip_network(ip, strict=False)) for ip in ip_allowlist]
    except ValueError as error:
        raise ApiError("invalid_request", "CIDR không hợp lệ.") from error
    raw = secrets.token_urlsafe(32)
    checksum = hashlib.sha256(raw.encode()).hexdigest()[:8]
    plain = f"sk_live_{raw}_{checksum}"
    now = int(time.time())
    connection = get_db()
    cursor = connection.execute(
        "INSERT INTO api_keys (prefix, hash, last4, owner_id, scopes, created_at, expires_at, ip_allowlist) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("sk_live", hashlib.sha256(plain.encode()).hexdigest(), plain[-4:], user["id"],
         json.dumps(sorted(set(scopes))), now, now + expires_in, json.dumps(networks)),
    )
    row = connection.execute("SELECT * FROM api_keys WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return {"api_key": plain, "key": key_metadata(row)}


def require_api_key(*scopes):
    def decorator(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            plain = request.headers.get("X-Api-Key", "")
            row = get_db().execute(
                "SELECT * FROM api_keys WHERE hash = ?",
                (hashlib.sha256(plain.encode()).hexdigest(),),
            ).fetchone() if plain else None
            now = int(time.time())
            if row is None or row["revoked_at"] is not None or (
                row["expires_at"] is not None and row["expires_at"] <= now
            ):
                raise ApiError("invalid_api_key", "Thiếu key, key không hợp lệ, hết hạn hoặc đã thu hồi.", 401)
            user = load_user(row["owner_id"])
            if not user or not user["active"]:
                raise ApiError("invalid_api_key", "Key không còn hiệu lực.", 401)
            networks = json.loads(row["ip_allowlist"])
            if networks:
                try:
                    address = ipaddress.ip_address(request.remote_addr)
                except ValueError as error:
                    raise ApiError("forbidden", "Không xác định được IP của client.", 403) from error
                if not any(address in ipaddress.ip_network(network) for network in networks):
                    raise ApiError("forbidden", "IP không thuộc allowlist.", 403)
            granted = set(json.loads(row["scopes"])) & set(user["scopes"])
            if not set(scopes).issubset(granted):
                raise ApiError("insufficient_scope", "API key thiếu scope cần thiết.", 403)
            g.api_key_id = row["id"]
            g.owner_id = row["owner_id"]
            g.api_scopes = granted
            return function(*args, **kwargs)
        return wrapped
    return decorator


def owned_key(key_id):
    row = get_db().execute("SELECT * FROM api_keys WHERE id = ?", (key_id,)).fetchone()
    if row is None:
        raise ApiError("not_found", "Không tìm thấy key.", 404)
    if row["owner_id"] != g.current_user["id"]:
        raise ApiError("forbidden", "Key thuộc người dùng khác.", 403)
    return row


def create_app(config=None):
    app = base_app("lab2_api_key", config)
    auth = configure_basic(app)

    @app.post("/api/keys")
    @auth.login_required
    def create_key():
        data = json_body({"scopes", "expires_in", "ip_allowlist"}, {"scopes"})
        result = mint_key(g.current_user, data["scopes"], data.get("expires_in", 3600), data.get("ip_allowlist"))
        get_db().commit()
        return jsonify(result), 201, {"Location": f"/api/keys/{result['key']['id']}"}

    @app.get("/api/keys")
    @auth.login_required
    def list_keys():
        rows = get_db().execute(
            "SELECT * FROM api_keys WHERE owner_id = ? ORDER BY id", (g.current_user["id"],)
        ).fetchall()
        return jsonify(keys=[key_metadata(row) for row in rows])

    @app.get("/api/keys/<int:key_id>")
    @auth.login_required
    def get_key(key_id):
        return jsonify(key_metadata(owned_key(key_id)))

    @app.delete("/api/keys/<int:key_id>")
    @auth.login_required
    def revoke_key(key_id):
        owned_key(key_id)
        get_db().execute(
            "UPDATE api_keys SET revoked_at = COALESCE(revoked_at, ?) WHERE id = ?",
            (int(time.time()), key_id),
        )
        get_db().commit()
        return "", 204

    @app.post("/api/keys/<int:key_id>/rotate")
    @auth.login_required
    def rotate_key(key_id):
        connection = get_db()
        connection.execute("BEGIN IMMEDIATE")
        row = owned_key(key_id)
        now = int(time.time())
        if row["revoked_at"] is not None or (row["expires_at"] is not None and row["expires_at"] <= now):
            raise ApiError("invalid_api_key", "Không thể rotate key đã hết hiệu lực.", 401)
        result = mint_key(
            g.current_user, json.loads(row["scopes"]),
            row["expires_at"] - now if row["expires_at"] else 3600,
            json.loads(row["ip_allowlist"]),
        )
        connection.execute("UPDATE api_keys SET revoked_at = ? WHERE id = ?", (now, key_id))
        connection.commit()
        return jsonify(result), 201, {"Location": f"/api/keys/{result['key']['id']}"}

    @app.get("/api/orders")
    @require_api_key("orders:read")
    def list_orders():
        return jsonify(orders=owner_orders(g.owner_id))

    @app.post("/api/orders")
    @require_api_key("orders:write")
    def create_order():
        result = new_order(g.owner_id)
        return jsonify(result), 201, {"Location": f"/api/orders/{result['id']}"}

    @app.get("/api/orders/<int:order_id>")
    @require_api_key("orders:read")
    def get_order(order_id):
        row = get_db().execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if row is None:
            raise ApiError("not_found", "Không tìm thấy order.", 404)
        if row["owner_id"] != g.owner_id:
            raise ApiError("forbidden", "Order thuộc người dùng khác.", 403)
        return jsonify(dict(row))

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5002, ssl_context="adhoc")
