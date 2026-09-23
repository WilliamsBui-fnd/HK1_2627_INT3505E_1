import hashlib
import json
import sqlite3
from flask import Flask, jsonify, make_response, request

app = Flask(__name__)
DB_FILE = "database.db"
DEFAULT_SIZE, MAX_SIZE = 20, 100


def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            isbn TEXT,
            price REAL
        )
    """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            status TEXT NOT NULL
        )
    """
    )
    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM books")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO books (title, author, isbn, price) VALUES (?, ?, ?, ?)",
            ("Clean Code", "Robert C. Martin", "9780132350884", 30.0),
        )
        cursor.execute(
            "INSERT INTO books (title, author, isbn, price) VALUES (?, ?, ?, ?)",
            (
                "The Pragmatic Programmer",
                "Andrew Hunt",
                "9780135957059",
                42.5,
            ),
        )
    cursor.execute("SELECT COUNT(*) FROM orders")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO orders (item, quantity, price, status) VALUES (?, ?, ?, ?)",
            ("Clean Code", 1, 30.0, "PENDING"),
        )
        cursor.execute(
            "INSERT INTO orders (item, quantity, price, status) VALUES (?, ?, ?, ?)",
            ("The Pragmatic Programmer", 2, 85.0, "COMPLETED"),
        )
    conn.commit()
    conn.close()


def generate_etag(data_dict):
    raw = json.dumps(data_dict, sort_keys=True)
    return f'"{hashlib.md5(raw.encode("utf-8")).hexdigest()}"'


@app.get("/books")
def list_books():
    try:
        page = int(request.args.get("page", 1))
        size = int(request.args.get("size", DEFAULT_SIZE))
    except ValueError:
        return jsonify(error="page and size must be int"), 400

    page = max(page, 1)
    size = max(min(size, MAX_SIZE), 1)

    author_filter = request.args.get("author")
    q = request.args.get("q")

    conn = get_db()
    cursor = conn.cursor()

    query = "SELECT * FROM books WHERE 1=1"
    params = []

    if author_filter:
        query += " AND LOWER(author) = LOWER(?)"
        params.append(author_filter)
    if q:
        query += " AND LOWER(title) LIKE LOWER(?)"
        params.append(f"%{q}%")

    cursor.execute(query, params)
    all_rows = [dict(row) for row in cursor.fetchall()]

    total = len(all_rows)
    start = (page - 1) * size
    end = start + size
    items = all_rows[start:end]
    last = max((total + size - 1) // size, 1)
    conn.close()

    def u(p):
        return f"/books?page={p}&size={size}"

    links = {
        "self": {"href": u(page)},
        "first": {"href": u(1)},
        "last": {"href": u(last)},
    }
    if page > 1:
        links["prev"] = {"href": u(page - 1)}
    if end < total:
        links["next"] = {"href": u(page + 1)}

    body = {
        "data": items,
        "pagination": {
            "page": page,
            "size": size,
            "total": total,
            "total_pages": last,
        },
        "_links": links,
    }
    resp = make_response(jsonify(body), 200)
    resp.headers["Cache-Control"] = "public, max-age=30"
    return resp


@app.post("/books")
def create_book():
    if not request.is_json:
        return jsonify(error="expected JSON"), 415
    p = request.get_json(silent=True) or {}
    t = (p.get("title") or "").strip()
    a = (p.get("author") or "").strip()
    if not t or not a:
        return jsonify(error="title and author required"), 422

    isbn = p.get("isbn")
    price = p.get("price")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO books (title, author, isbn, price) VALUES (?, ?, ?, ?)",
        (t, a, isbn, price),
    )
    new_id = cursor.lastrowid
    conn.commit()
    cursor.execute("SELECT * FROM books WHERE id = ?", (new_id,))
    book = dict(cursor.fetchone())
    conn.close()

    resp = make_response(jsonify(book), 201)
    resp.headers["Location"] = f"/books/{new_id}"
    return resp


@app.get("/books/<int:bid>")
def fetch_book(bid):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books WHERE id = ?", (bid,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return jsonify(error="not found"), 404

    book = dict(row)
    etag = generate_etag(book)

    if request.headers.get("If-None-Match") == etag:
        resp = make_response("", 304)
        resp.headers["ETag"] = etag
        return resp

    resp = make_response(jsonify(book), 200)
    resp.headers["Cache-Control"] = "max-age=60"
    resp.headers["ETag"] = etag
    return resp


@app.put("/books/<int:bid>")
def put_book(bid):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books WHERE id = ?", (bid,))
    if cursor.fetchone() is None:
        conn.close()
        return jsonify(error="not found"), 404

    p = request.get_json(silent=True) or {}
    t, a = p.get("title"), p.get("author")
    if not t or not a:
        conn.close()
        return jsonify(error="need title+author"), 422

    cursor.execute(
        "UPDATE books SET title = ?, author = ?, isbn = ?, price = ? WHERE id = ?",
        (t.strip(), a.strip(), p.get("isbn"), p.get("price"), bid),
    )
    conn.commit()
    cursor.execute("SELECT * FROM books WHERE id = ?", (bid,))
    updated = dict(cursor.fetchone())
    conn.close()
    return jsonify(updated), 200


@app.patch("/books/<int:bid>")
def patch_book(bid):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books WHERE id = ?", (bid,))
    row = cursor.fetchone()
    if row is None:
        conn.close()
        return jsonify(error="not found"), 404

    p = request.get_json(silent=True) or {}
    if p.get("price", 0) < 0:
        conn.close()
        return jsonify(error="price must be positive"), 422

    current = dict(row)
    for k in ["title", "author", "isbn", "price"]:
        if k in p:
            current[k] = p[k]

    cursor.execute(
        "UPDATE books SET title = ?, author = ?, isbn = ?, price = ? WHERE id = ?",
        (current["title"], current["author"], current["isbn"], current["price"], bid),
    )
    conn.commit()
    cursor.execute("SELECT * FROM books WHERE id = ?", (bid,))
    updated = dict(cursor.fetchone())
    conn.close()
    return jsonify(updated), 200


@app.delete("/books/<int:bid>")
def delete_book(bid):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books WHERE id = ?", (bid,))
    if cursor.fetchone() is None:
        conn.close()
        return jsonify(error="not found"), 404

    cursor.execute("DELETE FROM books WHERE id = ?", (bid,))
    conn.commit()
    conn.close()
    return "", 204


@app.get("/orders")
def list_orders():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders")
    orders = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({"data": orders, "total": len(orders)}), 200


@app.post("/orders")
def create_order():
    if not request.is_json:
        return jsonify(error="expected JSON"), 415
    p = request.get_json(silent=True) or {}
    item = (p.get("item") or "").strip()
    qty = p.get("quantity")
    price = p.get("price")
    status = p.get("status", "PENDING").strip()

    if not item or not qty or price is None:
        return jsonify(error="item, quantity and price required"), 422

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO orders (item, quantity, price, status) VALUES (?, ?, ?, ?)",
        (item, qty, price, status),
    )
    new_id = cursor.lastrowid
    conn.commit()
    cursor.execute("SELECT * FROM orders WHERE id = ?", (new_id,))
    order = dict(cursor.fetchone())
    conn.close()

    resp = make_response(jsonify(order), 201)
    resp.headers["Location"] = f"/orders/{new_id}"
    return resp


@app.get("/orders/<int:oid>")
def fetch_order(oid):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE id = ?", (oid,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return jsonify(error="not found"), 404

    order = dict(row)
    etag = generate_etag(order)

    if request.headers.get("If-None-Match") == etag:
        resp = make_response("", 304)
        resp.headers["ETag"] = etag
        return resp

    resp = make_response(jsonify(order), 200)
    resp.headers["ETag"] = etag
    return resp


@app.delete("/orders/<int:oid>")
def delete_order(oid):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE id = ?", (oid,))
    if cursor.fetchone() is None:
        conn.close()
        return jsonify(error="not found"), 404

    cursor.execute("DELETE FROM orders WHERE id = ?", (oid,))
    conn.commit()
    conn.close()
    return "", 204


init_db()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
