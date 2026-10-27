from flask import g, jsonify
from flask_jwt_extended import jwt_required

from authorization import require_roles, require_scopes, user_owns_resource
from common import new_order, owner_orders
from database import get_db, load_user, public_user
from tokens import jwt_app


def create_app(config=None):
    app = jwt_app("lab4_rbac", config)

    @app.get("/api/orders")
    @jwt_required()
    @require_scopes("orders:read")
    def list_orders():
        return jsonify(orders=owner_orders(g.current_user["id"]))

    @app.post("/api/orders")
    @jwt_required()
    @require_roles("admin", "manager", "editor")
    @require_scopes("orders:write")
    def create_order():
        result = new_order(g.current_user["id"])
        return jsonify(result), 201, {"Location": f"/api/orders/{result['id']}"}

    @app.get("/api/orders/<int:order_id>")
    @jwt_required()
    @require_scopes("orders:read")
    @user_owns_resource()
    def get_order(order_id):
        return jsonify(g.order)

    @app.delete("/api/orders/<int:order_id>")
    @jwt_required()
    @require_roles("admin", "manager")
    @require_scopes("orders:read", "orders:write")
    @user_owns_resource()
    def delete_order(order_id):
        get_db().execute("DELETE FROM orders WHERE id = ?", (order_id,))
        get_db().commit()
        return "", 204

    @app.get("/api/admin/users")
    @jwt_required()
    @require_roles("admin")
    @require_scopes("users:read")
    def list_users():
        rows = get_db().execute("SELECT id FROM users ORDER BY id").fetchall()
        return jsonify(users=[public_user(load_user(row["id"])) for row in rows])

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5004, ssl_context="adhoc")
