from flask import Blueprint
from .users_data import get_user

bp = Blueprint("v1", __name__)


@bp.route("/<int:uid>")
def get(uid):
    u = get_user(uid)
    if not u:
        return {"error": "nf"}, 404
    return {"id": uid,
            "full_name": f"{u['first_name']} {u['last_name']}",
            "email": u["email"]}
