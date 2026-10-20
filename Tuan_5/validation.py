import json
from functools import lru_cache
from pathlib import Path

from flask import request
from jsonschema import Draft202012Validator, FormatChecker

from errors import ApiIssue


SCHEMA_DIR = Path(__file__).with_name("schemas")


@lru_cache
def validator_for(name):
    path = SCHEMA_DIR / f"{name}.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=FormatChecker())


def read_json(name):
    if request.mimetype != "application/json":
        raise ApiIssue(
            "unsupported_media_type",
            "Content-Type phải là application/json.",
            415,
        )
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ApiIssue("invalid_json", "Body phải là JSON object hợp lệ.", 400)
    errors = sorted(validator_for(name).iter_errors(payload), key=lambda item: list(item.path))
    if errors:
        error = errors[0]
        field = ".".join(str(part) for part in error.absolute_path) or "body"
        raise ApiIssue("validation_failed", error.message, 422, field)
    return payload
