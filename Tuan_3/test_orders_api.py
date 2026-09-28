import requests
import time
import subprocess
import os
import signal

def run_tests():
    base_url = "http://127.0.0.1:5000/orders"

    print("Test 1: Sort by total descending and limit 2")
    r = requests.get(f"{base_url}?sort=-total&limit=2")
    data = r.json()
    print(data)
    
    assert len(data["data"]) == 2
    assert data["data"][0]["total"] == 450.0

    cursor = data["next_cursor"]
    print("\nTest 2: Cursor pagination (next page)")
    r = requests.get(f"{base_url}?sort=-total&limit=2&cursor={cursor}")
    data2 = r.json()
    print(data2)
    
    assert data2["data"][0]["total"] == 250.0

    print("\nTest 3: Filter by status=paid & fields=id,total")
    r = requests.get(f"{base_url}?status=paid&fields=id,total")
    data3 = r.json()
    print(data3)
    
    assert "status" not in data3["data"][0]
    assert "id" in data3["data"][0]

    print("\nTest 4: Invalid cursor")
    r = requests.get(f"{base_url}?cursor=invalid_base64_!@#")
    print(r.status_code, r.json())
    assert r.status_code == 400

if __name__ == "__main__":
    p = subprocess.Popen(["python3", "btvn_tuan_3_orders_api.py"])
    time.sleep(2)
    try:
        run_tests()
        print("\nAll tests passed!")
    finally:
        os.kill(p.pid, signal.SIGTERM)
