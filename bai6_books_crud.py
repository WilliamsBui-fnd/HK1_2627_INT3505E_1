from flask import Flask, jsonify, request

app = Flask(__name__)

_next = 3
BOOKS = [
    {"id": 1, "title": "Clean Code", "author": "Robert C. Martin", "year": 2008},
    {"id": 2, "title": "Designing Data-Intensive Applications", "author": "Martin Kleppmann", "year": 2017},
]

def find_book(bid):
    return next((b for b in BOOKS if b["id"] == bid), None)

@app.route("/books", methods=["GET"])
def list_books():
    q = request.args.get("q", "").strip().lower()
    sort_by = request.args.get("sort", "").strip().lower()
    limit = int(request.args.get("limit", 100))

    result = BOOKS
    if q:
        result = [b for b in result if q in b["title"].lower() or q in b["author"].lower()]

    if sort_by == "title":
        result = sorted(result, key=lambda b: b["title"].lower())
    elif sort_by == "year":
        result = sorted(result, key=lambda b: b["year"])

    return jsonify(result[:limit]), 200

@app.route("/books/<int:bid>", methods=["GET"])
def get_book(bid):
    book = find_book(bid)
    if not book:
        return jsonify({"error": "not found"}), 404
    return jsonify(book), 200

@app.route("/books", methods=["POST"])
def create_book():
    global _next
    body = request.get_json(silent=True) or {}
    title = body.get("title")
    author = body.get("author")
    year = body.get("year")

    if not title or not author:
        return jsonify({"error": "title and author are required"}), 400

    if year is None or not isinstance(year, int) or year < 1900:
        return jsonify({"error": "year must be an integer >= 1900"}), 400

    book = {
        "id": _next,
        "title": title,
        "author": author,
        "year": year
    }
    _next += 1
    BOOKS.append(book)

    return jsonify(book), 201, {"Location": f"/books/{book['id']}"}

@app.route("/books/<int:bid>", methods=["PUT"])
def update_book(bid):
    book = find_book(bid)
    if not book:
        return jsonify({"error": "not found"}), 404

    body = request.get_json(silent=True) or {}
    
    if "year" in body:
        year = body["year"]
        if not isinstance(year, int) or year < 1900:
            return jsonify({"error": "year must be an integer >= 1900"}), 400

    book.update({k: v for k, v in body.items() if k in ("title", "author", "year")})
    return jsonify(book), 200

@app.route("/books/<int:bid>", methods=["DELETE"])
def delete_book(bid):
    book = find_book(bid)
    if not book:
        return jsonify({"error": "not found"}), 404

    BOOKS.remove(book)
    return "", 204

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
