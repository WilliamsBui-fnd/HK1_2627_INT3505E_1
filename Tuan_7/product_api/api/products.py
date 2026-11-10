from flask import Blueprint, jsonify, request, url_for
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from ..errors import ApiError
from ..extensions import db
from ..models import Product
from ..schemas import ProductIn, ProductOut, ProductPatch, ReserveIn

products_bp = Blueprint("products", __name__, url_prefix="/api/v1/products")
product_out = ProductOut()


def json_body():
    if not request.is_json:
        raise ApiError("bad_request", "Content-Type must be application/json", 400)
    body = request.get_json()
    if not isinstance(body, dict):
        raise ApiError("bad_request", "JSON body must be an object", 400)
    return body


def active_product(product_id):
    product = db.session.get(Product, product_id)
    if product is None or product.archived:
        raise ApiError("not_found", "Product not found", 404)
    return product


def positive_query_arg(key, default):
    raw = request.args.get(key, str(default))
    try:
        value = int(raw)
    except (ValueError, TypeError):
        raise ApiError("validation_error", f"{key} must be a positive integer", 422) from None
    if value < 1 or str(value) != raw:
        raise ApiError("validation_error", f"{key} must be a positive integer", 422)
    return value


@products_bp.get("")
def list_products():
    page = positive_query_arg("page", 1)
    size = positive_query_arg("size", 20)
    if size > 100:
        raise ApiError("validation_error", "size must be at most 100", 422)
    base = db.select(Product).where(Product.archived.is_(False))
    rows = db.session.execute(base.order_by(Product.id).offset((page - 1) * size).limit(size)).scalars().all()
    total = db.session.scalar(db.select(db.func.count()).select_from(Product).where(Product.archived.is_(False)))
    return jsonify(items=product_out.dump(rows, many=True), page=page, size=size, total=total)


@products_bp.get("/<int:product_id>")
def get_product(product_id):
    return product_out.dump(active_product(product_id)), 200


@products_bp.post("")
def create_product():
    data = ProductIn().load(json_body())
    product = Product(**data)
    db.session.add(product)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ApiError("conflict", "sku already exists", 409) from None
    response = jsonify(product_out.dump(product))
    response.status_code = 201
    response.headers["Location"] = url_for("products.get_product", product_id=product.id)
    return response


@products_bp.post("/<int:product_id>/reserve")
def reserve_product(product_id):
    qty = ReserveIn().load(json_body())["qty"]
    result = db.session.execute(
        update(Product)
        .where(Product.id == product_id, Product.archived.is_(False), Product.qty_in_stock >= qty)
        .values(qty_in_stock=Product.qty_in_stock - qty)
    )
    if result.rowcount == 0:
        product = active_product(product_id)
        raise ApiError("out_of_stock", f"Only {product.qty_in_stock} units available", 409)
    db.session.commit()
    return product_out.dump(active_product(product_id)), 200


@products_bp.patch("/<int:product_id>")
def patch_product(product_id):
    data = ProductPatch().load(json_body())
    if not data:
        raise ApiError("validation_error", "At least one field is required", 422)
    product = active_product(product_id)
    for key, value in data.items():
        setattr(product, key, value)
    db.session.commit()
    return product_out.dump(product), 200


@products_bp.delete("/<int:product_id>")
def delete_product(product_id):
    product = active_product(product_id)
    product.archived = True
    db.session.commit()
    return "", 204
