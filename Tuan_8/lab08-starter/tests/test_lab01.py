import pytest
from jsonschema import ValidationError, validate

from tools import get_book_schema


def test_list_books_empty(client):
    response = client.get("/books")

    assert response.status_code == 200
    assert response.get_json() == []


def test_get_book_not_found(client):
    response = client.get("/books/9999")

    assert response.status_code == 404
    assert response.get_json()["code"] == "NOT_FOUND"


def test_create_book_missing_title(client):
    response = client.post("/books", json={"author": "X"})

    assert response.status_code == 400
    fields = [error["field"] for error in response.get_json()["errors"]]
    assert "title" in fields


def test_get_after_delete(client):
    book_id = client.post("/books", json={"title": "DDIA", "author": "Kleppmann"}).get_json()["id"]

    assert client.delete(f"/books/{book_id}").status_code == 204
    assert client.get(f"/books/{book_id}").status_code == 404


def test_response_extra_field_blocked(client):
    schema = get_book_schema()
    book = client.post("/books", json={
        "title": "DDIA", "author": "Kleppmann", "year": 2017, "isbn": "9781449373320",
    }).get_json()

    validate(book, schema)

    leaked = dict(book, password_hash="fake-hash")
    with pytest.raises(ValidationError):
        validate(leaked, schema)
