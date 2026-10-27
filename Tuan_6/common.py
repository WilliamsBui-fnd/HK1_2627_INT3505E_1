import hashlib
import time
from pathlib import Path

import bcrypt
from flask import Flask, current_app, g, jsonify, request
from flask_httpauth import HTTPBasicAuth
from werkzeug.exceptions import HTTPException

from database import get_db, init_database, load_user


class ApiError(Exception):
    def __init__(self, error, detail, status=400, headers=None):
        self.error = error
        self.detail = detail
        self.status = status
        self.headers = headers or {}


def base_app(name, config=None):
    app = Flask(name)
    app.config.from_mapping(
        DATABASE=str(Path(__file__).resolve().parent / "instance" / f"{name}.sqlite3"),
        BCRYPT_ROUNDS=12,
        AUTH_RATE_LIMIT=10,
        AUTH_RATE_WINDOW=60,
        MAX_CONTENT_LENGTH=16384,
    )
    if config:
        app.config.update(config)
    init_database(app)
    app.extensions["dummy_password_hash"] = bcrypt.hashpw(
        b"unused-dummy-password", bcrypt.gensalt(app.config["BCRYPT_ROUNDS"])
    )

    @app.errorhandler(ApiError)
    def api_error(error):
        return jsonify(error=error.error, detail=error.detail), error.status, error.headers

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(
            error=error.name.lower().replace(" ", "_"), detail=error.description
        ), error.code

    @app.after_request
    def protect_response(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    return app


def json_body(allowed, required=()):
    if not request.is_json:
        raise ApiError("unsupported_media_type", "Cần Content-Type application/json.", 415)
    data = request.get_json()
    if not isinstance(data, dict):
        raise ApiError("invalid_request", "JSON body phải là object.")
    if set(data) - set(allowed) or set(required) - set(data):
        raise ApiError("invalid_request", "Thiếu trường bắt buộc hoặc có trường không được phép.")
    return data


def rate_limit(subject):
    connection = get_db()
    now = int(time.time())
    window = current_app.config["AUTH_RATE_WINDOW"]
    limit = current_app.config["AUTH_RATE_LIMIT"]
    buckets = [
        f"ip:{request.remote_addr}",
        "account:" + hashlib.sha256(str(subject).strip().lower().encode()).hexdigest(),
    ]
    connection.execute("BEGIN IMMEDIATE")
    try:
        connection.execute("DELETE FROM auth_attempts WHERE created_at <= ?", (now - window,))
        for bucket in buckets:
            row = connection.execute(
                "SELECT COUNT(*), MIN(created_at) FROM auth_attempts WHERE bucket = ?", (bucket,)
            ).fetchone()
            if row[0] >= limit:
                retry_after = max(1, row[1] + window - now)
                raise ApiError(
                    "rate_limited", "Quá nhiều lần xác thực. Vui lòng thử lại sau.", 429,
                    {"Retry-After": str(retry_after)},
                )
        connection.executemany(
            "INSERT INTO auth_attempts (bucket, created_at) VALUES (?, ?)",
            [(bucket, now) for bucket in buckets],
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def verify_credentials(email, password):
    normalized = email.strip().lower() if isinstance(email, str) else ""
    row = get_db().execute("SELECT id FROM users WHERE email = ?", (normalized,)).fetchone()
    user = load_user(row["id"]) if row else None
    password_bytes = password.encode() if isinstance(password, str) else b""
    valid_length = 0 < len(password_bytes) <= 72
    stored = user["password_hash"] if user else current_app.extensions["dummy_password_hash"]
    valid = bcrypt.checkpw(password_bytes if valid_length else b"invalid", stored)
    if not user or not user["active"] or not valid or not valid_length:
        return None
    return user


def configure_basic(app):
    auth = HTTPBasicAuth(realm="orders")

    @auth.verify_password
    def verify_password(email, password):
        rate_limit(email)
        user = verify_credentials(email, password)
        if user:
            g.current_user = user
            return user
        return None

    @auth.error_handler
    def unauthorized(status):
        return jsonify(error="unauthorized", detail="Thiếu hoặc sai thông tin xác thực."), 401, {
            "WWW-Authenticate": 'Basic realm="orders", charset="UTF-8"'
        }

    return auth


def owner_orders(owner_id):
    rows = get_db().execute(
        "SELECT id, owner_id, item, quantity FROM orders WHERE owner_id = ? ORDER BY id", (owner_id,)
    ).fetchall()
    return [dict(row) for row in rows]


def new_order(owner_id):
    data = json_body({"item", "quantity"}, {"item", "quantity"})
    if not isinstance(data["item"], str) or not 1 <= len(data["item"].strip()) <= 200:
        raise ApiError("invalid_request", "item cần từ 1 đến 200 ký tự.")
    if type(data["quantity"]) is not int or not 1 <= data["quantity"] <= 10000:
        raise ApiError("invalid_request", "quantity phải là số nguyên từ 1 đến 10000.")
    connection = get_db()
    cursor = connection.execute(
        "INSERT INTO orders (owner_id, item, quantity) VALUES (?, ?, ?)",
        (owner_id, data["item"].strip(), data["quantity"]),
    )
    connection.commit()
    return dict(connection.execute(
        "SELECT id, owner_id, item, quantity FROM orders WHERE id = ?", (cursor.lastrowid,)
    ).fetchone())
