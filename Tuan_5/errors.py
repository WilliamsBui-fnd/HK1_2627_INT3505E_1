from dataclasses import dataclass

from flask import jsonify


@dataclass(frozen=True)
class ApiIssue(Exception):
    code: str
    message: str
    status: int = 400
    field: str | None = None


def issue_response(issue):
    error = {"code": issue.code, "message": issue.message}
    if issue.field is not None:
        error["field"] = issue.field
        error["parameter"] = issue.field
    return jsonify(error=error), issue.status


def require_resource(resource, name):
    if resource is None:
        raise ApiIssue("not_found", f"Không tìm thấy {name}.", 404)
    return resource
