from datetime import date

from flask import Blueprint, jsonify
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from errors import ApiIssue, require_resource
from models import Author, Book, BookAuthor, Category, Review, User, db
from pagination import list_books
from validation import read_json


books_bp = Blueprint("books", __name__, url_prefix="/api/v1/books")


def fetch_book(book_id):
    statement = (
        select(Book)
        .options(
            selectinload(Book.author_links).selectinload(BookAuthor.author),
            selectinload(Book.category),
        )
        .where(Book.id == book_id)
    )
    return require_resource(db.session.scalar(statement), "sách")


def resolve_authors(items):
    ids = [item["authorId"] for item in items]
    if len(ids) != len(set(ids)):
        raise ApiIssue("duplicate_author", "authorId không được lặp.", 422, "authors")
    authors = db.session.scalars(select(Author).where(Author.id.in_(ids))).all()
    by_id = {author.id: author for author in authors}
    missing = [author_id for author_id in ids if author_id not in by_id]
    if missing:
        raise ApiIssue("author_not_found", f"Không tìm thấy authorId {missing[0]}.", 422, "authors")
    return [(by_id[item["authorId"]], item.get("role", "co")) for item in items]


@books_bp.get("")
def list_books_route():
    return list_books()


@books_bp.post("")
def create_book():
    payload = read_json("book-create")
    category = require_resource(db.session.get(Category, payload["categoryId"]), "thể loại")
    author_rows = resolve_authors(payload["authors"])
    book = Book(
        title=payload["title"].strip(),
        isbn=payload["isbn"],
        price_vnd=payload["priceVnd"],
        stock=payload.get("stock", 0),
        published_at=date.fromisoformat(payload["publishedAt"]),
        category=category,
    )
    for author, role in author_rows:
        book.author_links.append(BookAuthor(author=author, role=role))
    db.session.add(book)
    db.session.commit()
    return jsonify(book.to_dict()), 201, {"Location": f"/api/v1/books/{book.id}"}


@books_bp.get("/<int:book_id>")
def get_book(book_id):
    return jsonify(fetch_book(book_id).to_dict())


@books_bp.patch("/<int:book_id>")
def update_book(book_id):
    book = fetch_book(book_id)
    payload = read_json("book-update")
    if "title" in payload:
        book.title = payload["title"].strip()
    if "isbn" in payload:
        book.isbn = payload["isbn"]
    if "priceVnd" in payload:
        book.price_vnd = payload["priceVnd"]
    if "stock" in payload:
        book.stock = payload["stock"]
    if "publishedAt" in payload:
        book.published_at = date.fromisoformat(payload["publishedAt"])
    if "categoryId" in payload:
        book.category = require_resource(db.session.get(Category, payload["categoryId"]), "thể loại")
    if "authors" in payload:
        author_rows = resolve_authors(payload["authors"])
        book.author_links.clear()
        for author, role in author_rows:
            book.author_links.append(BookAuthor(author=author, role=role))
    db.session.commit()
    return jsonify(book.to_dict())


@books_bp.delete("/<int:book_id>")
def delete_book(book_id):
    book = fetch_book(book_id)
    db.session.delete(book)
    db.session.commit()
    return "", 204


@books_bp.get("/<int:book_id>/authors")
def list_book_authors(book_id):
    book = fetch_book(book_id)
    data = [
        {
            "id": f"author_{link.author.id}",
            "name": link.author.name,
            "bio": link.author.bio,
            "role": link.role,
        }
        for link in sorted(book.author_links, key=lambda item: item.author.id)
    ]
    return jsonify(data=data, total=len(data))


@books_bp.post("/<int:book_id>/authors")
def add_book_author(book_id):
    book = fetch_book(book_id)
    payload = read_json("book-author-create")
    author = require_resource(db.session.get(Author, payload["authorId"]), "tác giả")
    existing = db.session.get(BookAuthor, (book.id, author.id))
    if existing is not None:
        raise ApiIssue("relationship_exists", "Tác giả đã được gắn với sách.", 409)
    link = BookAuthor(book=book, author=author, role=payload.get("role", "co"))
    db.session.add(link)
    db.session.commit()
    return jsonify(id=f"author_{author.id}", name=author.name, role=link.role), 201


@books_bp.delete("/<int:book_id>/authors/<int:author_id>")
def remove_book_author(book_id, author_id):
    book = fetch_book(book_id)
    link = db.session.get(BookAuthor, (book.id, author_id))
    require_resource(link, "quan hệ sách - tác giả")
    if len(book.author_links) == 1:
        raise ApiIssue("last_author", "Sách phải có ít nhất một tác giả.", 409)
    db.session.delete(link)
    db.session.commit()
    return "", 204


@books_bp.get("/<int:book_id>/reviews")
def list_book_reviews(book_id):
    book = fetch_book(book_id)
    rows = db.session.scalars(
        select(Review)
        .options(selectinload(Review.user), selectinload(Review.book))
        .where(Review.book_id == book.id)
        .order_by(Review.created_at.desc(), Review.id.desc())
    ).all()
    return jsonify(data=[review.to_dict() for review in rows], total=len(rows))


@books_bp.post("/<int:book_id>/reviews")
def create_book_review(book_id):
    book = fetch_book(book_id)
    payload = read_json("review-create")
    user = require_resource(db.session.get(User, payload["userId"]), "người dùng")
    review = Review(
        book=book,
        user=user,
        rating=payload["rating"],
        content=payload.get("content"),
    )
    db.session.add(review)
    db.session.commit()
    return jsonify(review.to_dict()), 201, {"Location": f"/api/v1/reviews/{review.id}"}
