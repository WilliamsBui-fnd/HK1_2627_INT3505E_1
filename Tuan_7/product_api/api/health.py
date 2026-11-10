from flask import Blueprint, jsonify
from sqlalchemy import text

from ..extensions import db

health_bp = Blueprint("health", __name__)


@health_bp.get("/healthz")
def healthz():
    return jsonify(status="ok")


@health_bp.get("/ready")
def ready():
    try:
        db.session.execute(text("SELECT 1"))
    except Exception:
        return jsonify(status="degraded", checks={"db": "err"}), 503
    return jsonify(status="ok", checks={"db": "ok"})
