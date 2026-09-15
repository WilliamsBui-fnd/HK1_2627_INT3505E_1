from flask import Flask, jsonify

app = Flask(__name__)

ORDERS = {
    "ord_01": {"id": "ord_01", "status": "pending", "item": "Laptop"},
    "ord_02": {"id": "ord_02", "status": "shipped", "item": "Phone"},
    "ord_03": {"id": "ord_03", "status": "delivered", "item": "Book"}
}

@app.route("/orders/<order_id>", methods=["DELETE"])
def delete_order(order_id):
    order = ORDERS.get(order_id)
    
    if order is None:
        return jsonify({"error": "not found"}), 404
        
    if order["status"] in ("shipped", "delivered"):
        return jsonify({"error": "cannot delete shipped or delivered order"}), 409
        
    ORDERS.pop(order_id, None)
    return "", 204

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
