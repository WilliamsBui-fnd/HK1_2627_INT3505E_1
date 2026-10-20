from flask import Blueprint, jsonify, request
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from errors import ApiIssue, require_resource
from models import Review, db
from validation import read_json


reviews_bp = Blueprint("reviews", __name__, url_prefix="/api/v1/reviews")


def fetch_review(review_id):
    statement = (
        select(Review)
        .options(selectinload(Review.user), selectinload(Review.book))
        .where(Review.id == review_id)
    )
    return require_resource(db.session.scalar(statement), "đánh giá")


@reviews_bp.get("")
def list_reviews():
    statement = select(Review).options(selectinload(Review.user), selectinload(Review.book))
    if "bookId" in request.args:
        try:
            statement = statement.where(Review.book_id == int(request.args["bookId"]))
        except ValueError as exc:
            raise ApiIssue("invalid_integer", "bookId phải là số nguyên.", 400, "bookId") from exc
    if "userId" in request.args:
        try:
            statement = statement.where(Review.user_id == int(request.args["userId"]))
        except ValueError as exc:
            raise ApiIssue("invalid_integer", "userId phải là số nguyên.", 400, "userId") from exc
    if "rating" in request.args:
        try:
            rating = int(request.args["rating"])
        except ValueError as exc:
            raise ApiIssue("invalid_integer", "rating phải là số nguyên.", 400, "rating") from exc
        if not 1 <= rating <= 5:
            raise ApiIssue("out_of_range", "rating phải từ 1 đến 5.", 400, "rating")
        statement = statement.where(Review.rating == rating)
    rows = db.session.scalars(statement.order_by(Review.created_at.desc(), Review.id.desc())).all()
    return jsonify(data=[review.to_dict() for review in rows], total=len(rows))


@reviews_bp.get("/<int:review_id>")
def get_review(review_id):
    return jsonify(fetch_review(review_id).to_dict())


@reviews_bp.patch("/<int:review_id>")
def update_review(review_id):
    review = fetch_review(review_id)
    payload = read_json("review-update")
    if "rating" in payload:
        review.rating = payload["rating"]
    if "content" in payload:
        review.content = payload["content"]
    db.session.commit()
    return jsonify(review.to_dict())


@reviews_bp.delete("/<int:review_id>")
def delete_review(review_id):
    review = fetch_review(review_id)
    db.session.delete(review)
    db.session.commit()
    return "", 204
