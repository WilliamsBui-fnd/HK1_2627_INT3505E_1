from app import app

c = app.test_client()
r = c.get("/users/1"); assert r.json["first_name"] == "Văn" and r.headers["X-API-Version-Served"] == "2"
r = c.get("/users/1", headers={"X-API-Version": "1"}); assert r.json["full_name"] == "Văn Nguyễn"
r = c.get("/users/1", headers={"X-API-Version": "2024-06-20"}); assert r.status_code == 200
r = c.get("/users/1", headers={"X-API-Version": "99"}); assert r.status_code == 400
print("lab2 ok")
