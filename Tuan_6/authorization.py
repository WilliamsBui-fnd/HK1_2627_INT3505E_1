from functools import wraps

from flask import g
from flask_jwt_extended import get_jwt

from common import ApiError
from database import get_db


def require_roles(*allowed):
    def decorator(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            if not set(g.current_user["roles"]) & set(allowed):
                raise ApiError("forbidden", "Role không được phép thực hiện thao tác.", 403)
            return function(*args, **kwargs)
        return wrapped
    return decorator


def require_scopes(*needed):
    def decorator(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            granted = set(get_jwt().get("scopes", [])) & set(g.current_user["scopes"])
            if not set(needed).issubset(granted):
                raise ApiError("insufficient_scope", "Token thiếu scope cần thiết.", 403, {
                    "WWW-Authenticate": 'Bearer error="insufficient_scope", scope="' + " ".join(needed) + '"'
                })
            return function(*args, **kwargs)
        return wrapped
    return decorator


def user_owns_resource(param="order_id"):
    def decorator(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            row = get_db().execute("SELECT * FROM orders WHERE id = ?", (kwargs[param],)).fetchone()
            if row is None:
                raise ApiError("not_found", "Không tìm thấy order.", 404)
            if row["owner_id"] != g.current_user["id"] and "admin" not in g.current_user["roles"]:
                raise ApiError("forbidden", "Order thuộc người dùng khác.", 403)
            g.order = dict(row)
            return function(*args, **kwargs)
        return wrapped
    return decorator
