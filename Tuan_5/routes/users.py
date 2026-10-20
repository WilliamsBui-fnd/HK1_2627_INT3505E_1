from flask import Blueprint, jsonify
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from errors import ApiIssue, require_resource
from models import Review, User, db
from validation import read_json


users_bp = Blueprint("users", __name__, url_prefix="/api/v1/users")


def fetch_user(user_id):
    return require_resource(db.session.get(User, user_id), "người dùng")


@users_bp.get("")
def list_users():
    rows = db.session.scalars(select(User).order_by(User.id)).all()
    return jsonify(data=[user.to_dict() for user in rows], total=len(rows))


@users_bp.post("")
def create_user():
    payload = read_json("user-create")
    user = User(
        email=payload["email"].strip().lower(),
        display_name=payload["displayName"].strip(),
        status=payload.get("status", "active"),
    )
    db.session.add(user)
    db.session.commit()
    return jsonify(user.to_dict()), 201, {"Location": f"/api/v1/users/{user.id}"}


@users_bp.get("/<int:user_id>")
def get_user(user_id):
    return jsonify(fetch_user(user_id).to_dict())


@users_bp.patch("/<int:user_id>")
def update_user(user_id):
    user = fetch_user(user_id)
    payload = read_json("user-update")
    if "email" in payload:
        user.email = payload["email"].strip().lower()
    if "displayName" in payload:
        user.display_name = payload["displayName"].strip()
    if "status" in payload:
        user.status = payload["status"]
    db.session.commit()
    return jsonify(user.to_dict())


@users_bp.delete("/<int:user_id>")
def delete_user(user_id):
    user = fetch_user(user_id)
    if user.reviews:
        raise ApiIssue("user_in_use", "Không thể xóa người dùng đang có đánh giá.", 409)
    db.session.delete(user)
    db.session.commit()
    return "", 204


@users_bp.get("/<int:user_id>/reviews")
def list_user_reviews(user_id):
    user = fetch_user(user_id)
    rows = db.session.scalars(
        select(Review)
        .options(selectinload(Review.user), selectinload(Review.book))
        .where(Review.user_id == user.id)
        .order_by(Review.created_at.desc(), Review.id.desc())
    ).all()
    return jsonify(data=[review.to_dict() for review in rows], total=len(rows))
