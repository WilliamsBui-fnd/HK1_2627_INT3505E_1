from app import app

c = app.test_client()
r = c.get("/api/v1/users/1")
assert r.status_code == 200 and r.headers["Deprecation"] == "true"
assert r.headers["Sunset"] == "Thu, 31 Dec 2026 23:59:59 GMT"
assert r.headers["Link"] == '</api/v2/users>; rel="successor-version"'
r = c.get("/api/v0/users/1"); assert r.status_code == 410 and r.json["error"] == "gone"
print("lab3 ok")
