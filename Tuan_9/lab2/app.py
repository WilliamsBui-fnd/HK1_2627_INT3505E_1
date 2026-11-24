from functools import wraps
from flask import Flask, jsonify, request

LATEST = "2"
SUPPORTED = {"1", "2", "2024-06-20"}
USERS = {1: {"f": "Văn", "l": "Nguyễn", "e": "a@vnu.vn"}}

app = Flask(__name__)
app.json.ensure_ascii = False


def api_version(supported=SUPPORTED, default=LATEST):
    def decorate(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            v = request.headers.get("X-API-Version", default)
            if v not in supported:
                return jsonify(error="unsupported version"), 400
            result = fn(v, *args, **kwargs)
            response = jsonify(result)
            response.headers["X-API-Version-Served"] = v
            return response
        return wrapper
    return decorate


@app.route("/users/<int:uid>")
@api_version()
def get_user(version, uid):
    u = USERS.get(uid)
    if not u:
        return {"error": "not found"}
    if version == "1":
        return {"id": uid, "full_name": u["f"] + " " + u["l"]}
    return {"id": uid, "first_name": u["f"],
            "last_name": u["l"], "email": u["e"]}


if __name__ == "__main__":
    app.run(port=5056)
