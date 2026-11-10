import pytest
from flask_migrate import upgrade
from sqlalchemy import event
from sqlalchemy.exc import OperationalError

from product_api import create_app
from product_api.extensions import db


@pytest.fixture
def app(tmp_path):
    application = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    })
    with application.app_context():
        upgrade()
    yield application
    with application.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


def product(client, sku="SKU-001", qty=5, price=100):
    return client.post("/api/v1/products", json={
        "sku": sku, "name": f"Product {sku}", "price_cents": price, "qty_in_stock": qty
    })


def test_product_crud_validation_pagination_and_soft_delete(client):
    created = product(client)
    assert created.status_code == 201
    product_id = created.json["id"]
    assert created.headers["Location"] == f"/api/v1/products/{product_id}"
    assert product(client).status_code == 409
    assert client.post("/api/v1/products", json={"sku": "x", "name": "", "price_cents": -1}).status_code == 422
    assert client.get("/api/v1/products?page=bad").status_code == 422
    assert client.get("/api/v1/products?size=101").status_code == 422
    assert product(client, "SKU-002").status_code == 201
    listing = client.get("/api/v1/products?page=2&size=1").json
    assert (listing["page"], listing["size"], listing["total"]) == (2, 1, 2)
    assert len(listing["items"]) == 1
    assert client.patch(f"/api/v1/products/{product_id}", json={"name": "New name"}).json["name"] == "New name"
    assert client.get(f"/api/v1/products/{product_id}").json["price_cents"] == 100
    assert client.delete(f"/api/v1/products/{product_id}").status_code == 204
    assert client.get(f"/api/v1/products/{product_id}").status_code == 404
    assert client.get("/api/v1/products").json["total"] == 1
    assert client.patch(f"/api/v1/products/{product_id}", json={"name": "No"}).status_code == 404


def test_reserve_never_makes_stock_negative(client):
    product_id = product(client, qty=2).json["id"]
    url = f"/api/v1/products/{product_id}/reserve"
    assert client.post(url, json={"qty": 0}).status_code == 422
    assert client.post(url, json={"qty": 3}).status_code == 409
    assert client.post(url, json={"qty": 2}).json["qty_in_stock"] == 0
    assert client.post(url, json={"qty": 1}).status_code == 409


def test_order_items_stock_rollback_and_price_snapshot(client):
    first = product(client, "SKU-001", qty=3, price=100).json["id"]
    second = product(client, "SKU-002", qty=1, price=250).json["id"]
    url = "/api/v1/orders"
    bad = client.post(url, json={"items": [
        {"product_id": first, "qty": 2}, {"product_id": second, "qty": 2}
    ]})
    assert bad.status_code == 409
    assert client.get(f"/api/v1/products/{first}").json["qty_in_stock"] == 3
    assert client.get(url).json["items"] == []
    assert client.post(url, json={"items": [
        {"product_id": first, "qty": 1}, {"product_id": first, "qty": 1}
    ]}).status_code == 422
    created = client.post(url, json={"items": [
        {"product_id": first, "qty": 2}, {"product_id": second, "qty": 1}
    ]})
    assert created.status_code == 201
    assert created.json["total_cents"] == 450
    assert len(created.json["items"]) == 2
    assert created.headers["Location"] == f"/api/v1/orders/{created.json['id']}"
    assert client.get(f"/api/v1/products/{first}").json["qty_in_stock"] == 1
    client.patch(f"/api/v1/products/{first}", json={"price_cents": 500})
    assert client.get(created.headers["Location"]).json["total_cents"] == 450
    assert client.get("/api/v1/orders/999").status_code == 404


def test_get_orders_eager_loading_query_count(app, client):
    ids = [product(client, f"SKU-{n:03d}", qty=10).json["id"] for n in range(4)]
    for _ in range(3):
        response = client.post("/api/v1/orders", json={"items": [
            {"product_id": product_id, "qty": 1} for product_id in ids
        ]})
        assert response.status_code == 201
    statements = []

    def record(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    with app.app_context():
        event.listen(db.engine, "before_cursor_execute", record)
        try:
            response = client.get("/api/v1/orders")
        finally:
            event.remove(db.engine, "before_cursor_execute", record)
    assert response.status_code == 200
    assert len(response.json["items"]) == 3
    assert all(len(order["items"]) == 4 for order in response.json["items"])
    assert len(statements) == 2, statements


def test_health_checks(client):
    assert client.get("/healthz").json == {"status": "ok"}
    assert client.get("/ready").json == {"status": "ok", "checks": {"db": "ok"}}


def test_order_rolls_back_when_a_product_is_missing_or_archived(client):
    first = product(client, "SKU-001", qty=3).json["id"]
    second = product(client, "SKU-002", qty=3).json["id"]
    assert client.delete(f"/api/v1/products/{second}").status_code == 204
    for unavailable in [second, 999]:
        response = client.post("/api/v1/orders", json={"items": [
            {"product_id": first, "qty": 2}, {"product_id": unavailable, "qty": 1}
        ]})
        assert response.status_code == 404
        assert client.get(f"/api/v1/products/{first}").json["qty_in_stock"] == 3
        assert client.get("/api/v1/orders").json["items"] == []
    assert client.post(f"/api/v1/products/{second}/reserve", json={"qty": 1}).status_code == 404


def test_bad_json_and_partial_updates(client):
    malformed = client.post("/api/v1/products", data="{bad", content_type="application/json")
    assert malformed.status_code == 400
    assert malformed.json["error"] == "bad_request"
    assert client.post("/api/v1/products", json=[]).status_code == 400
    assert client.post("/api/v1/products", data="{}").status_code == 400
    created = client.post("/api/v1/products", json={
        "sku": "SKU-001", "name": "Product", "price_cents": 100
    })
    assert created.status_code == 201
    assert created.json["qty_in_stock"] == 0
    url = created.headers["Location"]
    assert client.patch(url, json={}).status_code == 422
    assert client.patch(url, json={"qty_in_stock": -1}).status_code == 422
    assert client.patch(url, json={"price_cents": 1.5}).status_code == 422
    assert client.patch(url, json={"archived": True}).status_code == 422
    patched = client.patch(url, json={"description": "Updated"})
    assert patched.status_code == 200
    assert patched.json["name"] == "Product"
    assert patched.json["price_cents"] == 100
    assert patched.json["description"] == "Updated"


def test_readiness_failure_does_not_affect_liveness(client, monkeypatch):
    def unavailable(*args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception("Database unavailable"))

    monkeypatch.setattr(db.session, "execute", unavailable)
    assert client.get("/healthz").status_code == 200
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json == {"status": "degraded", "checks": {"db": "err"}}
