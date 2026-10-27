import json
import sqlite3
from pathlib import Path

import bcrypt
import click
from flask import current_app, g


ROLE_SCOPES = {
    "admin": ["orders:read", "orders:write", "users:read", "posts:read", "posts:write"],
    "manager": ["orders:read", "orders:write", "posts:read"],
    "editor": ["orders:read", "orders:write", "posts:read", "posts:write"],
    "viewer": ["orders:read", "posts:read"],
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash BLOB NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'manager', 'editor', 'viewer')),
    scopes TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY,
    owner_id INTEGER NOT NULL REFERENCES users(id),
    item TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0)
);
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY,
    owner_id INTEGER NOT NULL REFERENCES users(id),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    visibility TEXT NOT NULL CHECK (visibility IN ('public', 'private'))
);
CREATE TABLE IF NOT EXISTS api_keys (
    id INTEGER PRIMARY KEY,
    prefix TEXT NOT NULL,
    hash TEXT NOT NULL UNIQUE,
    last4 TEXT NOT NULL,
    owner_id INTEGER NOT NULL REFERENCES users(id),
    scopes TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    expires_at INTEGER,
    revoked_at INTEGER,
    ip_allowlist TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    refresh_jti TEXT NOT NULL UNIQUE,
    expires_at INTEGER NOT NULL,
    revoked_at INTEGER
);
CREATE TABLE IF NOT EXISTS auth_attempts (
    id INTEGER PRIMARY KEY,
    bucket TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_auth_attempts_bucket ON auth_attempts(bucket, created_at);
"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"], timeout=10)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(error=None):
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def load_user(user_id):
    row = get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        return None
    user = dict(row)
    user["roles"] = [user["role"]]
    user["scopes"] = json.loads(user["scopes"])
    return user


def public_user(user):
    return {key: user[key] for key in ("id", "email", "roles", "scopes")}


def create_user(email, password, role="viewer"):
    if not isinstance(email, str) or "@" not in email or len(email) > 254:
        raise ValueError("Email không hợp lệ.")
    if not isinstance(password, str) or not 12 <= len(password) or len(password.encode()) > 72:
        raise ValueError("Mật khẩu cần ít nhất 12 ký tự và không quá 72 byte UTF-8.")
    if role not in ROLE_SCOPES:
        raise ValueError("Role không hợp lệ.")
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(current_app.config["BCRYPT_ROUNDS"]))
    cursor = get_db().execute(
        "INSERT INTO users (email, password_hash, role, scopes) VALUES (?, ?, ?, ?)",
        (email.strip().lower(), hashed, role, json.dumps(ROLE_SCOPES[role])),
    )
    return cursor.lastrowid


def init_database(app):
    app.teardown_appcontext(close_db)
    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
    with app.app_context():
        get_db().executescript(SCHEMA)

    @app.cli.command("init-demo")
    @click.password_option(prompt="Mật khẩu chung cho 4 tài khoản demo")
    def init_demo(password):
        connection = get_db()
        if connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
            raise click.ClickException("Database đã có người dùng, không ghi đè dữ liệu.")
        accounts = [
            ("an@vnu.edu.vn", "editor"),
            ("binh@vnu.edu.vn", "viewer"),
            ("admin@vnu.edu.vn", "admin"),
            ("manager@vnu.edu.vn", "manager"),
        ]
        try:
            for email, role in accounts:
                user_id = create_user(email, password, role)
                connection.execute(
                    "INSERT INTO orders (owner_id, item, quantity) VALUES (?, ?, ?)",
                    (user_id, "Sách SOA", 1),
                )
                for visibility in ("public", "private"):
                    connection.execute(
                        "INSERT INTO posts (owner_id, title, content, visibility) VALUES (?, ?, ?, ?)",
                        (user_id, f"Bài viết {visibility}", "Nội dung thực hành Authentication", visibility),
                    )
            connection.commit()
        except ValueError as error:
            connection.rollback()
            raise click.ClickException(str(error)) from error
        for email, role in accounts:
            click.echo(f"{email}: {role}")
