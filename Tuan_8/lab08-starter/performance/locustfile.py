"""Lab 4 starter: weighted tasks, optional 404, no deliberate server errors.

Run: locust -f performance/locustfile.py --headless -H http://127.0.0.1:5000 \
         -u 10 -r 2 -t 30s --html reports/A.html
"""
import itertools
import random

from locust import HttpUser, between, task

_counter = itertools.count(1)


class BooksUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def list_books(self):
        self.client.get("/books", name="GET /books")

    @task(2)
    def read_book(self):
        book_id = random.randint(1, 50)
        with self.client.get(
            f"/books/{book_id}", name="GET /books/{id}", catch_response=True
        ) as response:
            # Expected 404 (random id absent) is not an operational failure.
            if response.status_code in (200, 404):
                response.success()
            else:
                response.failure(f"Unexpected status {response.status_code}")

    @task(1)
    def create_book(self):
        unique = next(_counter)
        self.client.post(
            "/books",
            json={"title": f"Load test {unique}", "author": "locust"},
            name="POST /books",
        )

    @task(1)
    def search_by_year(self, year=None):
        year = year or random.randint(2000, 2025)
        with self.client.get(
            f"/books?year={year}", name="GET /books?year=", catch_response=True
        ) as response:
            if random.random() < 0.01:
                response.failure("Simulated 500")
            elif response.status_code == 200:
                response.success()
            else:
                response.failure(f"Unexpected status {response.status_code}")
