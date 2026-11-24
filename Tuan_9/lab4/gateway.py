import hashlib
from flask import request
from handlers import v1_create_order, v2_create_order

V2_PERCENT = 5
V2_COHORTS = {"beta", "internal"}
V2_FORCE_ACCOUNTS = {"acct_42", "acct_99"}


def route_to_v2(body):
    cohort = request.headers.get("X-Cohort", "").lower()
    if cohort in V2_COHORTS:
        return True
    acct = body.get("account_id", "")
    if acct in V2_FORCE_ACCOUNTS:
        return True
    if V2_PERCENT == 0:
        return False
    h = int(hashlib.md5(acct.encode()).hexdigest(), 16)
    return h % 100 < V2_PERCENT


def dispatch(body):
    if route_to_v2(body):
        return "v2", v2_create_order(body)
    return "v1", v1_create_order(body)
