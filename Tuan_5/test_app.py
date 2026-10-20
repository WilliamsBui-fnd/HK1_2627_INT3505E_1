import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from app import create_app
from models import db


class BooksPaginationTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            }
        )
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.engine.dispose()

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    def test_offset_pagination(self):
        response = self.client.get(
            "/api/v1/books?strategy=offset&offset=2&limit=4&sort=id"
        )
        body = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in body["data"]],
            ["book_3", "book_4", "book_5", "book_6"],
        )
        self.assertEqual(body["pagination"]["total"], 15)
        self.assertEqual(body["pagination"]["nextOffset"], 6)

    def test_filter_genre_case_insensitive(self):
        response = self.client.get(
            "/api/v1/books?strategy=offset&genre=TECH&limit=100&sort=title"
        )
        body = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["pagination"]["total"], 7)
        self.assertTrue(all(item["genre"]["slug"] == "tech" for item in body["data"]))

    def test_filter_category_id(self):
        response = self.client.get(
            "/api/v1/books?strategy=offset&category=1&limit=100&sort=id"
        )
        body = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["pagination"]["total"], 7)
        self.assertTrue(all(item["genre"]["id"] == "genre_1" for item in body["data"]))

    def test_genre_and_category_are_mutually_exclusive(self):
        response = self.client.get("/api/v1/books?genre=tech&category=1")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "incompatible_parameter")

    def test_multi_key_sort(self):
        response = self.client.get(
            "/api/v1/books?strategy=offset&limit=100&sort=-price,title"
        )
        books = response.get_json()["data"]
        pairs = [(book["price"]["amount"], book["title"]) for book in books]
        self.assertEqual(pairs, sorted(pairs, key=lambda item: (-item[0], item[1])))

    def test_cursor_traverses_every_book_once_with_duplicate_values(self):
        cursor = None
        received = []
        while True:
            path = "/api/v1/books?strategy=cursor&limit=3&sort=-price,title"
            if cursor:
                path += f"&cursor={cursor}"
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            body = response.get_json()
            received.extend(item["id"] for item in body["data"])
            cursor = body["pagination"]["nextCursor"]
            if cursor is None:
                break
        expected = self.client.get(
            "/api/v1/books?strategy=offset&limit=100&sort=-price,title"
        ).get_json()["data"]
        self.assertEqual(received, [item["id"] for item in expected])
        self.assertEqual(len(received), len(set(received)))

    def test_cursor_rejects_changed_sort(self):
        first = self.client.get(
            "/api/v1/books?strategy=cursor&limit=2&sort=-price"
        ).get_json()
        response = self.client.get(
            "/api/v1/books",
            query_string={
                "strategy": "cursor",
                "limit": 2,
                "sort": "title",
                "cursor": first["pagination"]["nextCursor"],
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "cursor_mismatch")

    def test_cursor_rejects_changed_filter(self):
        first = self.client.get(
            "/api/v1/books?strategy=cursor&limit=2&genre=tech&sort=id"
        ).get_json()
        response = self.client.get(
            "/api/v1/books",
            query_string={
                "strategy": "cursor",
                "limit": 2,
                "genre": "fiction",
                "sort": "id",
                "cursor": first["pagination"]["nextCursor"],
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "cursor_mismatch")

    def test_invalid_cursor(self):
        response = self.client.get(
            "/api/v1/books?strategy=cursor&cursor=not-a-cursor"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "invalid_cursor")

    def test_invalid_sort(self):
        response = self.client.get("/api/v1/books?sort=-secret")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "invalid_sort")

    def test_limit_is_enforced(self):
        for value in (0, 101, "abc"):
            response = self.client.get("/api/v1/books", query_string={"limit": value})
            self.assertEqual(response.status_code, 400)

    def test_incompatible_pagination_parameters(self):
        offset_response = self.client.get(
            "/api/v1/books?strategy=offset&cursor=abc"
        )
        cursor_response = self.client.get(
            "/api/v1/books?strategy=cursor&offset=2"
        )
        self.assertEqual(offset_response.status_code, 400)
        self.assertEqual(cursor_response.status_code, 400)

    def test_book_response_matches_schema(self):
        schema_path = Path(__file__).with_name("schemas") / "book.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        book = self.client.get(
            "/api/v1/books?strategy=offset&limit=1"
        ).get_json()["data"][0]
        Draft202012Validator(schema).validate(book)


class LabOneCrudTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()

    def book_payload(self, isbn="9786040000001"):
        return {
            "title": "REST API Thực Chiến",
            "isbn": isbn,
            "priceVnd": 390000,
            "stock": 12,
            "categoryId": 1,
            "publishedAt": "2026-10-20",
            "authors": [
                {"authorId": 1, "role": "lead"},
                {"authorId": 2, "role": "co"},
            ],
        }

    def test_create_book(self):
        response = self.client.post("/api/v1/books", json=self.book_payload())
        body = response.get_json()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.headers["Location"], "/api/v1/books/16")
        self.assertEqual(body["title"], "REST API Thực Chiến")
        self.assertEqual(len(body["authors"]), 2)

    def test_create_book_validation(self):
        payload = self.book_payload()
        payload["isbn"] = "invalid"
        response = self.client.post("/api/v1/books", json=payload)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.get_json()["error"]["code"], "validation_failed")

    def test_duplicate_isbn_returns_conflict(self):
        payload = self.book_payload("9780132350884")
        response = self.client.post("/api/v1/books", json=payload)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["error"]["code"], "conflict")

    def test_get_update_delete_book(self):
        update = self.client.patch(
            "/api/v1/books/15",
            json={"priceVnd": 360000, "stock": 0, "categoryId": 1},
        )
        self.assertEqual(update.status_code, 200)
        self.assertEqual(update.get_json()["price"]["amount"], 360000)
        self.assertFalse(update.get_json()["inStock"])
        self.assertEqual(self.client.get("/api/v1/books/15").status_code, 200)
        self.assertEqual(self.client.delete("/api/v1/books/15").status_code, 204)
        self.assertEqual(self.client.get("/api/v1/books/15").status_code, 404)

    def test_author_crud(self):
        created = self.client.post(
            "/api/v1/authors",
            json={"name": "Nguyễn Văn A", "bio": "Tác giả kỹ thuật."},
        )
        self.assertEqual(created.status_code, 201)
        author_id = int(created.get_json()["id"].split("_")[1])
        updated = self.client.patch(
            f"/api/v1/authors/{author_id}",
            json={"bio": "Thông tin đã cập nhật."},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.get_json()["bio"], "Thông tin đã cập nhật.")
        self.assertEqual(self.client.delete(f"/api/v1/authors/{author_id}").status_code, 204)

    def test_book_author_relationship(self):
        added = self.client.post(
            "/api/v1/books/1/authors",
            json={"authorId": 2, "role": "editor"},
        )
        self.assertEqual(added.status_code, 201)
        listed = self.client.get("/api/v1/books/1/authors").get_json()
        self.assertEqual(listed["total"], 2)
        self.assertEqual(self.client.delete("/api/v1/books/1/authors/2").status_code, 204)

    def test_book_must_keep_one_author(self):
        response = self.client.delete("/api/v1/books/1/authors/1")
        author_response = self.client.delete("/api/v1/authors/1")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["error"]["code"], "last_author")
        self.assertEqual(author_response.status_code, 409)
        self.assertEqual(author_response.get_json()["error"]["code"], "author_in_use")

    def test_category_crud(self):
        created = self.client.post(
            "/api/v1/categories",
            json={"name": "Thiết kế", "slug": "design"},
        )
        self.assertEqual(created.status_code, 201)
        category_id = int(created.get_json()["id"].split("_")[1])
        updated = self.client.patch(
            f"/api/v1/categories/{category_id}",
            json={"name": "Thiết kế hệ thống"},
        )
        self.assertEqual(updated.get_json()["name"], "Thiết kế hệ thống")
        self.assertEqual(self.client.delete(f"/api/v1/categories/{category_id}").status_code, 204)

    def test_category_in_use_cannot_be_deleted(self):
        response = self.client.delete("/api/v1/categories/1")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["error"]["code"], "category_in_use")

    def test_user_crud(self):
        created = self.client.post(
            "/api/v1/users",
            json={"email": "lan@example.com", "displayName": "Lan"},
        )
        self.assertEqual(created.status_code, 201)
        user_id = int(created.get_json()["id"].split("_")[1])
        updated = self.client.patch(
            f"/api/v1/users/{user_id}",
            json={"displayName": "Lan Anh", "status": "suspended"},
        )
        self.assertEqual(updated.get_json()["displayName"], "Lan Anh")
        self.assertEqual(updated.get_json()["status"], "suspended")
        self.assertEqual(self.client.delete(f"/api/v1/users/{user_id}").status_code, 204)

    def test_user_with_review_cannot_be_deleted(self):
        response = self.client.delete("/api/v1/users/1")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["error"]["code"], "user_in_use")

    def test_review_crud(self):
        created = self.client.post(
            "/api/v1/books/2/reviews",
            json={"userId": 2, "rating": 5, "content": "Rất hữu ích."},
        )
        self.assertEqual(created.status_code, 201)
        review_id = int(created.get_json()["id"].split("_")[1])
        updated = self.client.patch(
            f"/api/v1/reviews/{review_id}",
            json={"rating": 4, "content": "Nội dung tốt."},
        )
        self.assertEqual(updated.get_json()["rating"], 4)
        self.assertEqual(self.client.get(f"/api/v1/reviews/{review_id}").status_code, 200)
        self.assertEqual(self.client.delete(f"/api/v1/reviews/{review_id}").status_code, 204)

    def test_duplicate_review_returns_conflict(self):
        response = self.client.post(
            "/api/v1/books/1/reviews",
            json={"userId": 1, "rating": 3},
        )
        self.assertEqual(response.status_code, 409)

    def test_review_filters(self):
        response = self.client.get("/api/v1/reviews?bookId=1&userId=1&rating=5")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["total"], 1)
        invalid = self.client.get("/api/v1/reviews?rating=6")
        self.assertEqual(invalid.status_code, 400)

    def test_relationship_navigation(self):
        author_books = self.client.get("/api/v1/authors/1/books").get_json()
        user_reviews = self.client.get("/api/v1/users/1/reviews").get_json()
        self.assertEqual(author_books["total"], 1)
        self.assertEqual(user_reviews["total"], 1)

    def test_structured_errors_and_media_type(self):
        missing = self.client.get("/api/v1/books/999")
        wrong_type = self.client.post(
            "/api/v1/authors",
            data="name=Test",
            content_type="application/x-www-form-urlencoded",
        )
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.get_json()["error"]["code"], "not_found")
        self.assertEqual(wrong_type.status_code, 415)
        self.assertEqual(wrong_type.get_json()["error"]["code"], "unsupported_media_type")


class SchemaTestCase(unittest.TestCase):
    def test_all_schemas_are_valid(self):
        schema_dir = Path(__file__).with_name("schemas")
        paths = sorted(schema_dir.glob("*.json"))
        self.assertEqual(len(paths), 14)
        for path in paths:
            schema = json.loads(path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)


if __name__ == "__main__":
    unittest.main(verbosity=2)
