from flask import Blueprint, jsonify
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from errors import ApiIssue, require_resource
from models import Author, BookAuthor, db
from validation import read_json


authors_bp = Blueprint("authors", __name__, url_prefix="/api/v1/authors")


def fetch_author(author_id):
    statement = (
        select(Author)
        .options(selectinload(Author.book_links).selectinload(BookAuthor.book))
        .where(Author.id == author_id)
    )
    return require_resource(db.session.scalar(statement), "tác giả")


@authors_bp.get("")
def list_authors():
    rows = db.session.scalars(select(Author).order_by(Author.name, Author.id)).all()
    return jsonify(data=[author.to_dict() for author in rows], total=len(rows))


@authors_bp.post("")
def create_author():
    payload = read_json("author-create")
    author = Author(name=payload["name"].strip(), bio=payload.get("bio"))
    db.session.add(author)
    db.session.commit()
    return jsonify(author.to_dict()), 201, {"Location": f"/api/v1/authors/{author.id}"}


@authors_bp.get("/<int:author_id>")
def get_author(author_id):
    return jsonify(fetch_author(author_id).to_dict(include_books=True))


@authors_bp.patch("/<int:author_id>")
def update_author(author_id):
    author = fetch_author(author_id)
    payload = read_json("author-update")
    if "name" in payload:
        author.name = payload["name"].strip()
    if "bio" in payload:
        author.bio = payload["bio"]
    db.session.commit()
    return jsonify(author.to_dict(include_books=True))


@authors_bp.delete("/<int:author_id>")
def delete_author(author_id):
    author = fetch_author(author_id)
    if any(len(link.book.author_links) == 1 for link in author.book_links):
        raise ApiIssue(
            "author_in_use",
            "Không thể xóa tác giả duy nhất của một sách.",
            409,
        )
    db.session.delete(author)
    db.session.commit()
    return "", 204


@authors_bp.get("/<int:author_id>/books")
def list_author_books(author_id):
    author = fetch_author(author_id)
    books = [
        {
            "id": f"book_{link.book.id}",
            "title": link.book.title,
            "role": link.role,
        }
        for link in sorted(author.book_links, key=lambda item: item.book.id)
    ]
    return jsonify(data=books, total=len(books))
