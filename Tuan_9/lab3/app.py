from datetime import datetime, timezone
from flask import Flask
from sunset import deprecate_at

app = Flask(__name__)
app.json.ensure_ascii = False

V1_SUNSET = datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
V1_OLD_SUNSET = datetime(2025, 1, 1, tzinfo=timezone.utc)


@app.route("/api/v1/users/<int:uid>")
@deprecate_at(V1_SUNSET, replacement="/api/v2/users")
def get_v1(uid):
    return {"id": uid, "full_name": "Nguyễn Văn A"}


@app.route("/api/v0/users/<int:uid>")
@deprecate_at(V1_OLD_SUNSET, replacement="/api/v2/users")
def get_v0(uid):
    return {"id": uid, "full_name": "Nguyễn Văn A"}


@app.route("/api/v2/users/<int:uid>")
def get_v2(uid):
    return {"id": uid, "first_name": "Văn", "last_name": "Nguyễn"}


if __name__ == "__main__":
    app.run(port=5057)
