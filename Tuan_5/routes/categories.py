from flask import Blueprint, jsonify
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from errors import ApiIssue, require_resource
from models import Category, db
from validation import read_json


categories_bp = Blueprint("categories", __name__, url_prefix="/api/v1/categories")


def fetch_category(category_id):
    statement = select(Category).options(selectinload(Category.books)).where(Category.id == category_id)
    return require_resource(db.session.scalar(statement), "thể loại")


@categories_bp.get("")
def list_categories():
    rows = db.session.scalars(
        select(Category).options(selectinload(Category.books)).order_by(Category.name, Category.id)
    ).all()
    return jsonify(data=[category.to_dict(True) for category in rows], total=len(rows))


@categories_bp.post("")
def create_category():
    payload = read_json("category-create")
    category = Category(name=payload["name"].strip(), slug=payload["slug"].lower())
    db.session.add(category)
    db.session.commit()
    return jsonify(category.to_dict(True)), 201, {"Location": f"/api/v1/categories/{category.id}"}


@categories_bp.get("/<int:category_id>")
def get_category(category_id):
    return jsonify(fetch_category(category_id).to_dict(True))


@categories_bp.patch("/<int:category_id>")
def update_category(category_id):
    category = fetch_category(category_id)
    payload = read_json("category-update")
    if "name" in payload:
        category.name = payload["name"].strip()
    if "slug" in payload:
        category.slug = payload["slug"].lower()
    db.session.commit()
    return jsonify(category.to_dict(True))


@categories_bp.delete("/<int:category_id>")
def delete_category(category_id):
    category = fetch_category(category_id)
    if category.books:
        raise ApiIssue("category_in_use", "Không thể xóa thể loại đang có sách.", 409)
    db.session.delete(category)
    db.session.commit()
    return "", 204
