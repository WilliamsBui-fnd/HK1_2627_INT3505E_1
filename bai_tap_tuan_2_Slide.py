from flask import Flask, jsonify, make_response, request

app = Flask(__name__)
BOOKS = []
_next_id = 1

DEFAULT_SIZE, MAX_SIZE = 20, 100


@app.get("/books")
def list_books():
    try:
        page = int(request.args.get("page", 1))
        size = int(request.args.get("size", DEFAULT_SIZE))
    except ValueError:
        return jsonify(error="page and size must be int"), 400

    page = max(page, 1)
    size = max(min(size, MAX_SIZE), 1)

    flt = BOOKS
    author_filter = request.args.get("author")
    if author_filter:
        flt = [b for b in flt if b.get("author", "").lower() == author_filter.lower()]

    q = (request.args.get("q") or "").lower()
    if q:
        flt = [b for b in flt if q in b.get("title", "").lower()]

    total = len(flt)
    start = (page - 1) * size
    end = start + size
    items = flt[start:end]
    last = max((total + size - 1) // size, 1)

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
    global _next_id
    if not request.is_json:
        return jsonify(error="expected JSON"), 415
    p = request.get_json(silent=True) or {}
    t = (p.get("title") or "").strip()
    a = (p.get("author") or "").strip()
    if not t or not a:
        return jsonify(error="title and author required"), 422
    book = {
        "id": _next_id,
        "title": t,
        "author": a,
        "isbn": p.get("isbn"),
        "price": p.get("price"),
    }
    BOOKS.append(book)
    _next_id += 1
    resp = make_response(jsonify(book), 201)
    resp.headers["Location"] = f"/books/{book['id']}"
    return resp


@app.get("/books/<int:bid>")
def fetch_book(bid):
    i = next((k for k, b in enumerate(BOOKS) if b["id"] == bid), None)
    if i is None:
        return jsonify(error="not found"), 404
    resp = make_response(jsonify(BOOKS[i]), 200)
    resp.headers["Cache-Control"] = "max-age=60"
    return resp


@app.put("/books/<int:bid>")
def put_book(bid):
    i = next((k for k, b in enumerate(BOOKS) if b["id"] == bid), None)
    if i is None:
        return jsonify(error="not found"), 404
    p = request.get_json(silent=True) or {}
    t, a = p.get("title"), p.get("author")
    if not t or not a:
        return jsonify(error="need title+author"), 422
    BOOKS[i] = {
        "id": bid,
        "title": t.strip(),
        "author": a.strip(),
        "isbn": p.get("isbn"),
        "price": p.get("price"),
    }
    return jsonify(BOOKS[i]), 200


@app.patch("/books/<int:bid>")
def patch_book(bid):
    i = next((k for k, b in enumerate(BOOKS) if b["id"] == bid), None)
    if i is None:
        return jsonify(error="not found"), 404
    p = request.get_json(silent=True) or {}
    if p.get("price", 0) < 0:
        return jsonify(error="price must be positive"), 422
    for k in "title author isbn price".split():
        if k in p:
            BOOKS[i][k] = p[k]
    return jsonify(BOOKS[i]), 200


@app.delete("/books/<int:bid>")
def delete_book(bid):
    i = next((k for k, b in enumerate(BOOKS) if b["id"] == bid), None)
    if i is None:
        return jsonify(error="not found"), 404
    BOOKS.pop(i)
    return "", 204


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
