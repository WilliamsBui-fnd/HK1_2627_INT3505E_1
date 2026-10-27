import os
import time
import uuid
from datetime import timedelta

from flask import g, jsonify
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_jwt,
    jwt_required,
)

from common import ApiError, base_app, json_body, rate_limit, verify_credentials
from database import get_db, load_user, public_user


def token_response(user, session_id, expires_at, fresh=False):
    remaining = expires_at - int(time.time())
    if remaining <= 0:
        raise ApiError("invalid_token", "Phiên đăng nhập đã hết hạn.", 401)
    claims = {"sid": session_id, "roles": user["roles"], "scopes": user["scopes"]}
    access = create_access_token(identity=str(user["id"]), additional_claims=claims, fresh=fresh)
    refresh = create_refresh_token(
        identity=str(user["id"]), additional_claims=claims, expires_delta=timedelta(seconds=remaining)
    )
    response = {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "Bearer",
        "expires_in": max(0, decode_token(access)["exp"] - int(time.time())),
        "scope": " ".join(sorted(user["scopes"])),
    }
    return response, decode_token(refresh)["jti"]


def jwt_app(name, config=None, prefix="/api/auth", include_logout=True):
    settings = {
        "JWT_SECRET_KEY": os.environ.get("JWT_SECRET_KEY", ""),
        "JWT_ALGORITHM": "HS256",
        "JWT_DECODE_ALGORITHMS": ["HS256"],
        "JWT_ENCODE_ISSUER": "soa-week6",
        "JWT_DECODE_ISSUER": "soa-week6",
        "JWT_ENCODE_AUDIENCE": name,
        "JWT_DECODE_AUDIENCE": name,
        "JWT_ACCESS_TOKEN_EXPIRES": timedelta(minutes=15),
        "JWT_REFRESH_TOKEN_EXPIRES": timedelta(days=30),
        "JWT_TOKEN_LOCATION": ["headers"],
    }
    if config:
        settings.update(config)
    secret = settings["JWT_SECRET_KEY"]
    if not isinstance(secret, str) or len(secret.encode()) < 32:
        raise RuntimeError("Cần đặt JWT_SECRET_KEY ngẫu nhiên, dài ít nhất 32 byte.")
    app = base_app(name, settings)
    manager = JWTManager(app)

    def token_error(error, detail):
        return jsonify(error=error, detail=detail), 401, {
            "WWW-Authenticate": 'Bearer error="invalid_token"'
        }

    @manager.unauthorized_loader
    def missing_token(reason):
        return token_error("unauthorized", "Cần Authorization: Bearer <token>.")

    @manager.invalid_token_loader
    def invalid_token(reason):
        return token_error("invalid_token", "Token không hợp lệ.")

    @manager.expired_token_loader
    def expired_token(header, claims):
        return token_error("token_expired", "Token đã hết hạn.")

    @manager.revoked_token_loader
    def revoked_token(header, claims):
        return token_error("token_revoked", "Token hoặc phiên đã bị thu hồi.")

    @manager.user_lookup_error_loader
    def missing_user(header, claims):
        return token_error("invalid_token", "Người dùng không còn hoạt động.")

    @manager.token_verification_loader
    def required_claims(header, claims):
        return (
            header.get("alg") == "HS256"
            and all(key in claims for key in ("exp", "iat", "nbf", "jti", "sub", "iss", "aud", "sid"))
            and isinstance(claims["sub"], str)
            and isinstance(claims["sid"], str)
            and isinstance(claims["jti"], str)
            and bool(claims["jti"])
            and claims.get("type") in {"access", "refresh"}
            and isinstance(claims.get("scopes"), list)
            and all(isinstance(scope, str) for scope in claims["scopes"])
            and isinstance(claims.get("roles"), list)
            and all(isinstance(role, str) for role in claims["roles"])
        )

    @manager.token_verification_failed_loader
    def invalid_claims(header, claims):
        return token_error("invalid_token", "Token thiếu claims bắt buộc.")

    @manager.token_in_blocklist_loader
    def session_revoked(header, claims):
        session_id = claims.get("sid")
        if not isinstance(session_id, str):
            return True
        connection = get_db()
        row = connection.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if row is None or row["revoked_at"] is not None or row["expires_at"] <= int(time.time()):
            return True
        if str(row["user_id"]) != claims.get("sub"):
            return True
        if claims.get("type") == "refresh" and row["refresh_jti"] != claims.get("jti"):
            connection.execute("UPDATE sessions SET revoked_at = ? WHERE id = ?", (int(time.time()), session_id))
            connection.commit()
            return True
        return False

    @manager.user_lookup_loader
    def current_user(header, claims):
        user = load_user(claims["sub"])
        if user and user["active"]:
            g.current_user = user
            return user
        return None

    @app.post(f"{prefix}/login")
    def login():
        data = json_body({"email", "password"}, {"email", "password"})
        email, password = data["email"], data["password"]
        if not isinstance(email, str) or not 1 <= len(email) <= 254 or not isinstance(password, str):
            raise ApiError("invalid_request", "email và password phải là chuỗi hợp lệ.")
        if not 1 <= len(password.encode()) <= 72:
            raise ApiError("invalid_request", "password phải từ 1 đến 72 byte UTF-8.")
        rate_limit(email)
        user = verify_credentials(email, password)
        if user is None:
            raise ApiError("invalid_credentials", "Email hoặc mật khẩu không đúng.", 401)
        session_id = str(uuid.uuid4())
        expires_at = int(time.time() + app.config["JWT_REFRESH_TOKEN_EXPIRES"].total_seconds())
        response, refresh_jti = token_response(user, session_id, expires_at, fresh=True)
        connection = get_db()
        connection.execute(
            "INSERT INTO sessions (id, user_id, refresh_jti, expires_at) VALUES (?, ?, ?, ?)",
            (session_id, user["id"], refresh_jti, expires_at),
        )
        connection.commit()
        return jsonify(response)

    @app.post(f"{prefix}/refresh")
    @jwt_required(refresh=True)
    def refresh():
        connection = get_db()
        claims = get_jwt()
        row = connection.execute("SELECT * FROM sessions WHERE id = ?", (claims["sid"],)).fetchone()
        response, refresh_jti = token_response(g.current_user, row["id"], row["expires_at"])
        cursor = connection.execute(
            "UPDATE sessions SET refresh_jti = ? WHERE id = ? AND refresh_jti = ? "
            "AND revoked_at IS NULL AND expires_at > ?",
            (refresh_jti, row["id"], claims["jti"], int(time.time())),
        )
        if cursor.rowcount != 1:
            connection.execute("UPDATE sessions SET revoked_at = ? WHERE id = ?", (int(time.time()), row["id"]))
            connection.commit()
            raise ApiError("token_revoked", "Refresh token đã được sử dụng. Phiên bị thu hồi.", 401)
        connection.commit()
        return jsonify(response)

    if include_logout:
        @app.post(f"{prefix}/logout")
        @jwt_required()
        def logout():
            get_db().execute(
                "UPDATE sessions SET revoked_at = ? WHERE id = ?", (int(time.time()), get_jwt()["sid"])
            )
            get_db().commit()
            return "", 204

        @app.get("/api/me")
        @jwt_required()
        def me():
            return jsonify(public_user(g.current_user))

    return app
