# Báo cáo Bài tập SOA - INT3505E_1
**Họ và tên:** Bùi Đình Cảnh  
**Mã SV:** 24021392  

---

##  Tuần 1: Giới thiệu API và Web Services
*Bài tập: Xây dựng RESTful CRUD cơ bản cho resource `books` bằng Flask.*

**Lệnh khởi chạy Server:**
```bash
# Di chuyển vào thư mục và chạy
cd Tuan_1
python3 bai6_books_crud.py
```

**Lệnh Test (Chạy ở Terminal khác):**
```bash
# 1. Lấy danh sách sách
curl -i http://127.0.0.1:5000/books

# Lệnh Test: Kết quả mong đợi
HTTP/1.1 200 OK
[
  {"author": "Robert C. Martin", "id": 1, "title": "Clean Code", "year": 2008},
  {"author": "Martin Kleppmann", "id": 2, "title": "Designing Data-Intensive Applications", "year": 2017}
]
```

---

##  Tuần 2: Kiến trúc REST và HTTP Fundamentals
*Bài tập: Refactor API `orders` dùng SQLite, xử lý Lỗi (Error Handler) và ETag.*

**Lệnh khởi chạy Server:**
```bash
cd Tuan_2
python3 btvn_tuan_2_app.py
```

**Lệnh Test:**
```bash
# 1. Lấy Order 1 kèm ETag
curl -i http://127.0.0.1:5000/orders/1

# Lệnh Test: Kết quả mong đợi
HTTP/1.1 200 OK
ETag: "d41d8cd98f00b204e9800998ecf8427e"
{"id": 1, "item": "Laptop", "quantity": 1}

# 2. Test Error Handler chuẩn RFC 7807
curl -i http://127.0.0.1:5000/orders/999

# Lệnh Test: Kết quả mong đợi
HTTP/1.1 404 NOT FOUND
Content-Type: application/problem+json
{
  "detail": "Order ID 999 not found in the database.",
  "instance": "/orders/999",
  "status": 404,
  "title": "Order Not Found",
  "type": "https://api.example.com/probs/order-not-found"
}
```
