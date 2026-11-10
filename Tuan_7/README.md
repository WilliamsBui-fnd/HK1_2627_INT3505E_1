# Tuần 7 - Backend Service

Lab 1 và bài tập cuối slide của `SOA - B7 - Backend_Service.pdf`. Service dùng Flask application factory, Blueprints, SQLAlchemy 2.x, Marshmallow và Flask-Migrate. SQLite dùng mặc định khi chạy local; Docker Compose dùng PostgreSQL.

## Chạy local

```bash
cd Tuan_7
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
flask --app wsgi:app db upgrade
flask --app wsgi:app run --port 5000
```

Chạy test: `python -m pytest -q`. Mỗi test tạo database SQLite riêng và dựng schema bằng migration.

## Chạy Docker

```bash
cd Tuan_7
docker compose up --build -d
docker compose ps
curl http://localhost:5000/ready
```

Compose tự chờ PostgreSQL khỏe, chạy migration rồi khởi động Gunicorn. `docker compose down` dừng service; thêm `-v` chỉ khi muốn xóa dữ liệu Postgres.

## API

| Method | Path | Mô tả |
| --- | --- | --- |
| GET | `/api/v1/products?page=1&size=20` | Danh sách sản phẩm chưa archive, có `items`, `page`, `size`, `total` |
| GET | `/api/v1/products/{id}` | Lấy sản phẩm chưa archive |
| POST | `/api/v1/products` | Tạo sản phẩm, trả 201 và Location |
| POST | `/api/v1/products/{id}/reserve` | Trừ tồn kho theo `{"qty": 1}` |
| PATCH | `/api/v1/products/{id}` | Cập nhật `name`, `description`, `price_cents`, `qty_in_stock` |
| DELETE | `/api/v1/products/{id}` | Soft delete |
| GET | `/api/v1/orders` | Danh sách đơn hàng và các OrderItem |
| GET | `/api/v1/orders/{id}` | Chi tiết đơn hàng |
| POST | `/api/v1/orders` | Tạo đơn nhiều sản phẩm, trừ kho trong cùng transaction |
| GET | `/healthz` | Liveness, không truy vấn database |
| GET | `/ready` | Readiness, `SELECT 1` đến database |

Ví dụ:

```bash
curl -i -X POST http://localhost:5000/api/v1/products \
  -H 'Content-Type: application/json' \
  -d '{"sku":"BOOK-001","name":"SOA","price_cents":120000,"qty_in_stock":10}'

curl -i -X POST http://localhost:5000/api/v1/orders \
  -H 'Content-Type: application/json' \
  -d '{"items":[{"product_id":1,"qty":2}]}'
```

`OrderItem` lưu giá lúc đặt (`unit_price_cents`), nên tổng đơn cũ giữ nguyên khi giá sản phẩm đổi. Lỗi trả JSON gồm `error` và `detail`, với 404 cho resource không có, 409 cho SKU trùng/hết kho, 422 cho dữ liệu không hợp lệ. Endpoint danh sách đơn dùng `selectinload` cho items và `joinedload` cho product; test kiểm tra số SELECT không tăng theo số đơn.

## Migration

Migration đầu tiên ở `migrations/versions/`. Sau khi sửa model:

```bash
flask --app wsgi:app db migrate -m "describe change"
flask --app wsgi:app db upgrade
```

Luôn đọc lại revision do Alembic sinh trước khi áp dụng.
