from flask import Blueprint, jsonify, url_for
from sqlalchemy import update
from sqlalchemy.orm import selectinload

from ..errors import ApiError
from ..extensions import db
from ..models import Order, OrderItem, Product
from ..schemas import OrderIn, OrderOut
from .products import json_body

orders_bp = Blueprint("orders", __name__, url_prefix="/api/v1/orders")
order_out = OrderOut()


def order_query():
    return db.select(Order).options(selectinload(Order.items).joinedload(OrderItem.product))


def load_order(order_id):
    order = db.session.execute(order_query().where(Order.id == order_id)).scalar_one_or_none()
    if order is None:
        raise ApiError("not_found", "Order not found", 404)
    return order


@orders_bp.get("")
def list_orders():
    orders = db.session.execute(order_query().order_by(Order.id)).scalars().all()
    return jsonify(items=order_out.dump(orders, many=True))


@orders_bp.get("/<int:order_id>")
def get_order(order_id):
    return order_out.dump(load_order(order_id)), 200


@orders_bp.post("")
def create_order():
    data = OrderIn().load(json_body())
    order = Order()
    db.session.add(order)
    for item_data in data["items"]:
        product_id = item_data["product_id"]
        qty = item_data["qty"]
        product = db.session.get(Product, product_id)
        if product is None or product.archived:
            db.session.rollback()
            raise ApiError("not_found", f"Product {product_id} not found", 404)
        result = db.session.execute(
            update(Product)
            .where(Product.id == product_id, Product.archived.is_(False), Product.qty_in_stock >= qty)
            .values(qty_in_stock=Product.qty_in_stock - qty)
        )
        if result.rowcount == 0:
            db.session.rollback()
            raise ApiError("out_of_stock", f"Product {product_id} has insufficient stock", 409)
        order.items.append(OrderItem(product=product, qty=qty, unit_price_cents=product.price_cents))
    db.session.commit()
    response = jsonify(order_out.dump(load_order(order.id)))
    response.status_code = 201
    response.headers["Location"] = url_for("orders.get_order", order_id=order.id)
    return response
