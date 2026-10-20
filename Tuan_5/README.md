# Tuần 5 - Data Modeling & Resource Design

Sinh viên: Bùi Đình Cảnh

Mã sinh viên: 24021392

## Nội dung đã hoàn thành

- `models.py`: Book, Author, Category, Review, User và BookAuthor.
- `routes/`: CRUD và relationship routes cho toàn bộ entity trong Lab 1.
- `schemas/`: JSON Schema Draft 2020-12 cho request validation và 3 resource bài tập.
- `pagination.py`: offset, composite cursor, genre/category filter và multi-key sort của Lab 2.
- `test_app.py`: 31 bài kiểm thử tự động.
- `postman/Bookstore_Week5.postman_collection.json`: Postman collection cho Lab 1 và Lab 2.

## Lab 1 - Models, relationships và CRUD

Các nhóm endpoint:

- `/api/v1/books`: CRUD sách, tác giả của sách và review theo sách.
- `/api/v1/authors`: CRUD tác giả và danh sách sách theo tác giả.
- `/api/v1/categories`: CRUD thể loại và `bookCount`.
- `/api/v1/users`: CRUD người dùng và review theo người dùng.
- `/api/v1/reviews`: tra cứu, cập nhật và xóa review.

Book dùng quan hệ N:1 với Category, N:M với Author qua BookAuthor có field `role`. Review dùng quan hệ N:1 với Book và User.

## Lab 2 - Pagination, filter và sort

`GET /api/v1/books` hỗ trợ:

- `strategy=offset|cursor`
- `offset`, `limit` với giới hạn từ 1 đến 100
- `genre=tech` hoặc `category=1`
- `sort=-price,title`
- composite cursor chứa toàn bộ sort values và `id` tie-break

## Cài đặt và chạy

```bash
cd Tuan_5
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 app.py
```

API chạy tại `http://127.0.0.1:5000`.

## Ví dụ

```bash
curl 'http://127.0.0.1:5000/api/v1/books?strategy=offset&offset=0&limit=5&genre=tech&sort=-price,title'
curl 'http://127.0.0.1:5000/api/v1/books?strategy=cursor&limit=5&genre=tech&sort=-price,title'
curl 'http://127.0.0.1:5000/api/v1/books?strategy=cursor&limit=5&category=1&sort=-price,title'
```

Giá trị `nextCursor` ở response đầu tiên được truyền nguyên vẹn vào query tiếp theo bằng tham số `cursor`.

## Chạy test

```bash
cd Tuan_5
python3 -m unittest -v test_app.py
```
