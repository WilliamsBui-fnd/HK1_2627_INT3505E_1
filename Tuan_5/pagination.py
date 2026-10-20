import base64
import binascii
import json
from datetime import date, datetime

from flask import jsonify, request
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import selectinload

from errors import ApiIssue
from models import Book, BookAuthor, Category, db


DEFAULT_LIMIT = 20
MAX_LIMIT = 100


SORT_FIELDS = {
    "id": (Book.id, lambda book: book.id, "integer"),
    "title": (Book.title, lambda book: book.title, "string"),
    "price": (Book.price_vnd, lambda book: book.price_vnd, "integer"),
    "stock": (Book.stock, lambda book: book.stock, "integer"),
    "genre": (Category.slug, lambda book: book.category.slug, "string"),
    "publishedAt": (Book.published_at, lambda book: book.published_at, "date"),
    "createdAt": (Book.created_at, lambda book: book.created_at, "datetime"),
}


def parse_integer(name, default, minimum, maximum=None):
    raw = request.args.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ApiIssue("invalid_integer", f"{name} phải là số nguyên.", 400, name) from exc
    if value < minimum or maximum is not None and value > maximum:
        bound = f"từ {minimum} đến {maximum}" if maximum is not None else f"từ {minimum}"
        raise ApiIssue("out_of_range", f"{name} phải {bound}.", 400, name)
    return value


def parse_sort(raw):
    value = raw or "-id"
    tokens = value.split(",")
    if any(not token for token in tokens):
        raise ApiIssue("invalid_sort", "sort không được chứa khóa rỗng.", 400, "sort")
    specs = []
    seen = set()
    for token in tokens:
        direction = "desc" if token.startswith("-") else "asc"
        name = token[1:] if token.startswith("-") else token
        if name not in SORT_FIELDS:
            allowed = ", ".join(SORT_FIELDS)
            raise ApiIssue("invalid_sort", f"Khóa sort phải thuộc: {allowed}.", 400, "sort")
        if name in seen:
            raise ApiIssue("duplicate_sort", f"Khóa sort {name} bị lặp.", 400, "sort")
        seen.add(name)
        specs.append((name, direction))
    if "id" not in seen:
        specs.append(("id", specs[-1][1]))
    return specs


def serializable_value(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def restore_value(raw, value_type):
    if value_type == "integer":
        if isinstance(raw, bool) or not isinstance(raw, int):
            raise ValueError
        return raw
    if value_type == "string":
        if not isinstance(raw, str):
            raise ValueError
        return raw
    if not isinstance(raw, str):
        raise ValueError
    return date.fromisoformat(raw) if value_type == "date" else datetime.fromisoformat(raw)


def encode_cursor(specs, filters, book):
    payload = {
        "version": 1,
        "sort": [[name, direction] for name, direction in specs],
        "filters": filters,
        "values": [
            serializable_value(SORT_FIELDS[name][1](book)) for name, _ in specs
        ],
    }
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(token, specs, filters):
    try:
        padding = "=" * (-len(token) % 4)
        raw = base64.b64decode(token + padding, altchars=b"-_", validate=True)
        payload = json.loads(raw.decode("utf-8"))
        expected_sort = [[name, direction] for name, direction in specs]
        if payload.get("version") != 1:
            raise ValueError
        if payload.get("sort") != expected_sort or payload.get("filters") != filters:
            raise ApiIssue(
                "cursor_mismatch",
                "cursor không khớp với sort hoặc bộ lọc hiện tại.",
                400,
                "cursor",
            )
        values = payload.get("values")
        if not isinstance(values, list) or len(values) != len(specs):
            raise ValueError
        return [
            restore_value(value, SORT_FIELDS[name][2])
            for value, (name, _) in zip(values, specs)
        ]
    except ApiIssue:
        raise
    except (ValueError, TypeError, KeyError, UnicodeDecodeError, binascii.Error, json.JSONDecodeError) as exc:
        raise ApiIssue("invalid_cursor", "cursor không hợp lệ.", 400, "cursor") from exc


def apply_cursor(statement, specs, values):
    branches = []
    for index, (name, direction) in enumerate(specs):
        prefix = [
            SORT_FIELDS[prefix_name][0] == values[prefix_index]
            for prefix_index, (prefix_name, _) in enumerate(specs[:index])
        ]
        column = SORT_FIELDS[name][0]
        comparison = column > values[index] if direction == "asc" else column < values[index]
        branches.append(and_(*prefix, comparison))
    return statement.where(or_(*branches))


def parse_filters():
    genre_raw = request.args.get("genre")
    genre = genre_raw.strip().lower() if genre_raw else None
    if genre_raw is not None and not genre:
        raise ApiIssue("invalid_genre", "genre không được để trống.", 400, "genre")
    category = parse_integer("category", None, 1) if "category" in request.args else None
    if genre is not None and category is not None:
        raise ApiIssue(
            "incompatible_parameter",
            "Chỉ dùng một trong hai filter genre hoặc category.",
            400,
            "category",
        )
    return {"genre": genre, "category": category}


def book_statement(filters, specs):
    statement = (
        select(Book)
        .join(Book.category)
        .options(selectinload(Book.author_links).selectinload(BookAuthor.author))
    )
    if filters["genre"] is not None:
        statement = statement.where(Category.slug == filters["genre"])
    if filters["category"] is not None:
        statement = statement.where(Book.category_id == filters["category"])
    order = [
        SORT_FIELDS[name][0].desc() if direction == "desc" else SORT_FIELDS[name][0].asc()
        for name, direction in specs
    ]
    return statement.order_by(*order)


def count_statement(filters):
    statement = select(func.count(Book.id)).join(Book.category)
    if filters["genre"] is not None:
        statement = statement.where(Category.slug == filters["genre"])
    if filters["category"] is not None:
        statement = statement.where(Book.category_id == filters["category"])
    return statement


def build_response(books, strategy, limit, specs, filters, has_more, **metadata):
    pagination = {"strategy": strategy, "limit": limit, "hasMore": has_more, **metadata}
    return jsonify(
        data=[book.to_dict() for book in books],
        pagination=pagination,
        sort=[{"field": name, "direction": direction} for name, direction in specs],
        filters=filters,
    )


def list_books():
    strategy = request.args.get("strategy", "cursor")
    if strategy not in {"offset", "cursor"}:
        raise ApiIssue("invalid_strategy", "strategy phải là offset hoặc cursor.", 400, "strategy")
    limit = parse_integer("limit", DEFAULT_LIMIT, 1, MAX_LIMIT)
    filters = parse_filters()
    specs = parse_sort(request.args.get("sort"))
    statement = book_statement(filters, specs)

    if strategy == "offset":
        if "cursor" in request.args:
            raise ApiIssue(
                "incompatible_parameter",
                "cursor không dùng với strategy=offset.",
                400,
                "cursor",
            )
        offset = parse_integer("offset", 0, 0)
        total = db.session.scalar(count_statement(filters)) or 0
        books = db.session.scalars(statement.offset(offset).limit(limit)).all()
        has_more = offset + len(books) < total
        return build_response(
            books,
            "offset",
            limit,
            specs,
            filters,
            has_more,
            offset=offset,
            total=total,
            nextOffset=offset + limit if has_more else None,
        )

    if "offset" in request.args:
        raise ApiIssue(
            "incompatible_parameter",
            "offset không dùng với strategy=cursor.",
            400,
            "offset",
        )
    token = request.args.get("cursor")
    if token:
        values = decode_cursor(token, specs, filters)
        statement = apply_cursor(statement, specs, values)
    rows = db.session.scalars(statement.limit(limit + 1)).all()
    has_more = len(rows) > limit
    books = rows[:limit]
    next_cursor = encode_cursor(specs, filters, books[-1]) if books and has_more else None
    return build_response(
        books,
        "cursor",
        limit,
        specs,
        filters,
        has_more,
        nextCursor=next_cursor,
    )
