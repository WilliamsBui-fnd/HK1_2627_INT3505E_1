def v1_create_order(body):
    return {"version": "v1", "account_id": body.get("account_id")}


def v2_create_order(body):
    return {"version": "v2", "account_id": body.get("account_id"), "status": "created"}
