from flask import jsonify
from marshmallow import ValidationError
from werkzeug.exceptions import HTTPException


class ApiError(Exception):
    def __init__(self, error: str, detail: str, status: int):
        super().__init__(detail)
        self.error = error
        self.detail = detail
        self.status = status


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def api_error(exc):
        return jsonify(error=exc.error, detail=exc.detail), exc.status

    @app.errorhandler(ValidationError)
    def validation_error(exc):
        return jsonify(error="validation_error", detail=exc.messages), 422

    @app.errorhandler(HTTPException)
    def http_error(exc):
        return jsonify(error=exc.name.lower().replace(" ", "_"), detail=exc.description), exc.code

    @app.errorhandler(Exception)
    def unexpected_error(exc):
        app.logger.exception("unhandled_error")
        return jsonify(error="internal_error", detail="Internal server error"), 500
