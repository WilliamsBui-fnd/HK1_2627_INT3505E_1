import base64
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

ORDERS = [
    {"id": 1, "status": "paid", "customer_id": 101, "total": 250.0},
    {"id": 2, "status": "pending", "customer_id": 102, "total": 150.0},
    {"id": 3, "status": "paid", "customer_id": 101, "total": 300.0},
    {"id": 4, "status": "cancelled", "customer_id": 103, "total": 50.0},
    {"id": 5, "status": "paid", "customer_id": 104, "total": 450.0},
    {"id": 6, "status": "pending", "customer_id": 101, "total": 120.0},
]

def encode_cursor(order_id):
    return base64.b64encode(str(order_id).encode()).decode()

def decode_cursor(cursor_str):
    try:
        return int(base64.b64decode(cursor_str).decode())
    except Exception:
        return None

@app.route("/orders", methods=["GET"])
def get_orders():
    status = request.args.get("status")
    customer_id = request.args.get("customer_id")
    sort_by = request.args.get("sort", "id")
    fields = request.args.get("fields")
    limit = int(request.args.get("limit", 10))
    cursor = request.args.get("cursor")

    results = ORDERS

    if status:
        results = [o for o in results if o["status"] == status]
    if customer_id:
        try:
            cid = int(customer_id)
            results = [o for o in results if o["customer_id"] == cid]
        except ValueError:
            return jsonify({"error": "Invalid customer_id"}), 400

    reverse = False
    if sort_by.startswith("-"):
        reverse = True
        sort_by = sort_by[1:]
    
    if sort_by not in ["id", "status", "customer_id", "total"]:
        sort_by = "id"

    results = sorted(results, key=lambda x: x[sort_by], reverse=reverse)

    if cursor:
        last_id = decode_cursor(cursor)
        if last_id is None:
            return jsonify({"error": "Invalid cursor"}), 400
        
        idx = 0
        for i, o in enumerate(results):
            if o["id"] == last_id:
                idx = i + 1
                break
        results = results[idx:]

    paginated = results[:limit]
    
    next_cursor = None
    if len(results) > limit:
        next_cursor = encode_cursor(paginated[-1]["id"])

    if fields:
        field_list = set(fields.split(","))
        filtered_paginated = []
        for o in paginated:
            filtered_o = {k: v for k, v in o.items() if k in field_list}
            filtered_paginated.append(filtered_o)
        paginated = filtered_paginated

    return jsonify({
        "data": paginated,
        "next_cursor": next_cursor
    })

if __name__ == "__main__":
    app.run(debug=True)
