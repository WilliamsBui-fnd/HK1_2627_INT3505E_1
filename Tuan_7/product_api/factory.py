import os

from flask import Flask

from .api.health import health_bp
from .api.orders import orders_bp
from .api.products import products_bp
from .config import DefaultConfig
from .errors import register_error_handlers
from .extensions import db, migrate


def create_app(config=None):
    app = Flask(__name__)
    if isinstance(config, dict):
        app.config.from_object(DefaultConfig)
        app.config.from_mapping(config)
    else:
        app.config.from_object(config or os.environ.get("APP_CONFIG", DefaultConfig))
    db.init_app(app)
    migrate.init_app(app, db, directory=os.path.join(app.root_path, "..", "migrations"))
    app.register_blueprint(products_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(health_bp)
    register_error_handlers(app)
    return app
