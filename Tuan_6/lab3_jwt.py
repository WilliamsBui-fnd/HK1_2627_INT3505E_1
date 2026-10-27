from flask import g, jsonify
from flask_jwt_extended import jwt_required

from authorization import require_scopes
from common import owner_orders
from tokens import jwt_app


def create_app(config=None):
    app = jwt_app("lab3_jwt", config)

    @app.get("/api/orders")
    @jwt_required()
    @require_scopes("orders:read")
    def list_orders():
        return jsonify(orders=owner_orders(g.current_user["id"]))

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5003, ssl_context="adhoc")
