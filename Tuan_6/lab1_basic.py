from flask import g, jsonify

from common import base_app, configure_basic, owner_orders


def create_app(config=None):
    app = base_app("lab1_basic", config)
    auth = configure_basic(app)

    @app.get("/api/orders")
    @auth.login_required
    def list_orders():
        return jsonify(principal=g.current_user["email"], orders=owner_orders(g.current_user["id"]))

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5001, ssl_context="adhoc")
