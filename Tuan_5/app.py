from pathlib import Path

from flask import Flask, jsonify
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException

from errors import ApiIssue, issue_response
from models import db, seed_database
from routes import BLUEPRINTS


def create_app(config=None):
    application = Flask(__name__)
    database_path = Path(__file__).with_name("week5.db")
    application.config.from_mapping(
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{database_path}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    if config:
        application.config.update(config)

    db.init_app(application)
    for blueprint in BLUEPRINTS:
        application.register_blueprint(blueprint)

    @application.get("/health")
    def health():
        return jsonify(status="ok")

    @application.errorhandler(ApiIssue)
    def handle_api_issue(issue):
        return issue_response(issue)

    @application.errorhandler(IntegrityError)
    def handle_integrity_error(error):
        db.session.rollback()
        return issue_response(
            ApiIssue(
                "conflict",
                "Dữ liệu trùng hoặc vi phạm ràng buộc quan hệ.",
                409,
            )
        )

    @application.errorhandler(HTTPException)
    def handle_http_error(error):
        return issue_response(
            ApiIssue(
                error.name.lower().replace(" ", "_"),
                error.description,
                error.code,
            )
        )

    with application.app_context():
        db.create_all()
        seed_database()
    return application


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
