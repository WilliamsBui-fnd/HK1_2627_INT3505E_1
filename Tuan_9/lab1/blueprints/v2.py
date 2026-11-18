from flask import Blueprint
from .users_data import get_user

bp = Blueprint("v2", __name__)


@bp.route("/<int:uid>")
def get(uid):
    u = get_user(uid)
    if not u:
        return {"error": "nf"}, 404
    return {"id": uid,
            "first_name": u["first_name"],
            "last_name": u["last_name"],
            "email": u["email"]}
