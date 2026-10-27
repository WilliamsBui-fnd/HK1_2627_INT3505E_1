from flask import g, jsonify
from flask_jwt_extended import jwt_required

from authorization import require_scopes
from common import ApiError
from database import get_db
from tokens import jwt_app


def create_app(config=None):
    app = jwt_app("social_api", config, prefix="/auth", include_logout=False)

    @app.get("/posts/<id>")
    @jwt_required()
    @require_scopes("posts:read")
    def get_post(id):
        if not id.isascii() or not id.isdecimal() or not 1 <= len(id) <= 18 or int(id) < 1:
            raise ApiError("invalid_request", "id phải là số nguyên dương, tối đa 18 chữ số.")
        row = get_db().execute("SELECT * FROM posts WHERE id = ?", (int(id),)).fetchone()
        if row is None:
            raise ApiError("not_found", "Không tìm thấy bài viết.", 404)
        if row["visibility"] == "private" and row["owner_id"] != g.current_user["id"] and (
            "admin" not in g.current_user["roles"]
        ):
            raise ApiError("forbidden", "Không có quyền đọc bài viết riêng tư.", 403)
        return jsonify(dict(row))

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5005, ssl_context="adhoc")
