import gateway
from app import app

c = app.test_client()


def post(acct, **h):
    return c.post("/orders", json={"account_id": acct}, headers=h)


assert post("any", **{"X-Cohort": "beta"}).headers["X-Order-Handler"] == "v2"
assert post("acct_42").headers["X-Order-Handler"] == "v2"
gateway.V2_PERCENT = 0
r = post("ordinary"); assert r.headers["X-Order-Handler"] == "v1" and r.status_code == 200
gateway.V2_PERCENT = 100
r = post("ordinary"); assert r.headers["X-Order-Handler"] == "v2" and r.status_code == 201
print("lab4 ok")
