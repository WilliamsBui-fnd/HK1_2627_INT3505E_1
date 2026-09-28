# BÁO CÁO BÀI TẬP VỀ NHÀ BUỔI 1
**Môn học:** Kiến trúc hướng dịch vụ (SOA)  
**Mã lớp:** INT3505E_1  
**Họ và tên:** Bùi Đình Cảnh  
**Mã sinh viên:** 24021392  
**Link GitHub Repository:** [https://github.com/WilliamsBui-fnd/HK1_2627_INT3505E_1](https://github.com/WilliamsBui-fnd/HK1_2627_INT3505E_1)

---

## PHẦN 1: NGHIÊN CỨU VÀ PHÂN TÍCH 3 PUBLIC API THỰC TẾ

### 1. GitHub REST API
- **Domain / Mục đích:** Quản lý kho chứa mã nguồn, tài khoản người dùng, pull requests và theo dõi sự cố (issues).
- **Loại API (API Type):** REST API (Sử dụng định dạng wire-format JSON qua giao thức HTTP/1.1 & HTTP/2).
- **Base URL:** `https://api.github.com`
- **Phương thức xác thực (Auth Method):** 
  - Cho phép truy cập Unauthenticated (bị giới hạn Rate Limit ở mức 60 requests/giờ).
  - Sử dụng Personal Access Token (PAT) hoặc OAuth 2.0 gửi qua Header `Authorization: Bearer <token>` (Rate Limit nâng lên 5,000 requests/giờ).
- **Quản lý phiên bản (Versioning):** Khai báo phiên bản qua HTTP Header `X-GitHub-Api-Version: 2022-11-28` hoặc qua Media Type `Accept: application/vnd.github+json`.
- **Định danh tài nguyên (Resource Identifier):** Sử dụng kết hợp **Số nguyên (Integer ID)** (ví dụ repo ID `1296269`) và **Tên duy nhất (Username/Repo Name)** trên URL path (ví dụ: `/users/octocat` hoặc `/repos/octocat/hello-world`).

---

### 2. OpenWeatherMap Current Weather API
- **Domain / Mục đích:** Cung cấp dữ liệu thời tiết thời gian thực toàn cầu (nhiệt độ, độ ẩm, áp suất, tốc độ gió).
- **Loại API (API Type):** REST API (Định dạng phản hồi chính là JSON, hỗ trợ thêm XML).
- **Base URL:** `https://api.openweathermap.org/data/2.5/`
- **Phương thức xác thực (Auth Method):** API Key (Truyền dưới dạng Query Parameter `?appid={YOUR_API_KEY}`).
- **Quản lý phiên bản (Versioning):** Đánh số phiên bản trực tiếp trên đường dẫn URL path (`/data/2.5/weather`).
- **Định danh tài nguyên (Resource Identifier):** Sử dụng **Số nguyên City ID** (ví dụ `1566083` là mã của TP. Hồ Chí Minh) hoặc **Tọa độ địa lý (Latitude/Longitude)**.

---

### 3. Spotify Web API
- **Domain / Mục đích:** Truy vấn danh mục âm nhạc, danh sách phát (Playlists), thông tin nghệ sĩ, album và điều khiển phát nhạc.
- **Loại API (API Type):** REST API (Định dạng JSON over HTTP).
- **Base URL:** `https://api.spotify.com/v1/`
- **Phương thức xác thực (Auth Method):** OAuth 2.0 (Bắt buộc Access Token gửi qua Header `Authorization: Bearer <access_token>`).
- **Quản lý phiên bản (Versioning):** Đánh số phiên bản trực tiếp trên đường dẫn URL path (`/v1`).
- **Định danh tài nguyên (Resource Identifier):** Sử dụng chuỗi **Base62 Alphanumeric ID** gồm 22 ký tự duy nhất (Ví dụ Track ID: `4uLU6hMCjMI75M1A2tKUQC`).

---

## PHẦN 2: ĐỌC SÁCH VÀ 5 CÂU SO SÁNH / BỔ SUNG KHÁI NIỆM API

So sánh 5 đặc điểm cốt lõi trong Slide 05 với kiến thức từ 2 cuốn sách tham khảo chính: *API Design Patterns* (JJ Geewax) và *Web API Design Rulebook* (Mark Higginbotham):

### 1. Về "Hợp đồng rõ ràng" (Contract-First)
- **Slide 05:** Nhấn mạnh việc mô tả Spec (OpenAPI, Protobuf) trước khi viết code để Client có thể đọc spec mà không cần đọc code.
- **Geewax & Higginbotham bổ sung:** Hợp đồng API không chỉ là cú pháp (Syntax) mà là cam kết về **Semantics (Ý nghĩa nghiệp vụ)** và **Tương thích ngược (Backward Compatibility)**. Tác giả Geewax nhấn mạnh rằng khi hợp đồng đã công bố, bất kỳ thay đổi phá vỡ (breaking change) nào cũng là vi phạm cam kết. Higginbotham bổ sung thêm việc hợp đồng phải quy định rõ ràng cả các mã lỗi (Error Schemas) chuẩn chứ không chỉ định dạng thành công.

### 2. Về "Ẩn cài đặt" (Abstraction)
- **Slide 05:** Client không biết và không nên biết Server dùng CSDL hay ngôn ngữ gì (ví dụ đổi Postgres -> MongoDB không ảnh hưởng Client).
- **Geewax bổ sung:** Phải tách biệt rõ ràng giữa **Resource (Tài nguyên khái niệm)** và **Database Entity (Thực thể CSDL)**. Tác giả chỉ ra sai lầm phổ biến là bê nguyên cấu trúc bảng trong CSDL ra làm API Resource. API Abstraction chuẩn phải thiết kế tài nguyên theo nhu cầu nghiệp vụ của Client chứ không mô phỏng CSDL bên dưới.

### 3. Về "Độc lập ngôn ngữ & nền tảng" (Language-Agnostic)
- **Slide 05:** Dùng định dạng dữ liệu trung gian (JSON, XML, Protobuf) để bất kỳ ngôn ngữ nào (Python, Java, Go, Mobile) cũng gọi được.
- **Higginbotham bổ sung:** Cần tuân thủ nghiêm ngặt các **chuẩn định dạng dữ liệu quốc tế (RFC Standards)**. Ví dụ: Kiểu dữ liệu thời gian phải dùng chuẩn ISO-8601 (`YYYY-MM-DDTHH:mm:ssZ`), tiền tệ dùng mã ISO-4217 (`USD`, `VND`), không được dùng các định dạng thời gian/tiền tệ tùy biến của riêng một ngôn ngữ lập trình nào.

### 4. Về "Tính tái sử dụng" (Reusability)
- **Slide 05:** Một codebase phục vụ nhiều loại Client (Web, Mobile, 3rd-party) mà không cần sửa code Server.
- **Geewax bổ sung:** Tính tái sử dụng chỉ đạt hiệu quả cao khi đi kèm tính **Nhất quán (Consistency across APIs)**. Tác giả đưa ra nguyên tắc: Tất cả các API trong cùng hệ thống phải dùng chung quy tắc đặt tên (ví dụ: luôn dùng `snake_case` hoặc `camelCase`, dùng chung tên trường thời tạo `created_at` thay vì chỗ ghi `create_date`, chỗ ghi `time_created`).

### 5. Về "Versioning & Quan sát được" (Versioned & Observable)
- **Slide 05:** API phải có phiên bản (`/v1`, `/v2`) và có logs, metrics, traces để vận hành.
- **Higginbotham bổ sung:** Bổ sung chiến lược **Deprecation & Sunsetting Policy (Chính sách ngừng hỗ trợ)**. Khi ra mắt phiên bản mới (`/v2`), Server phải gửi kèm các HTTP Header chuẩn như `Deprecation` hoặc `Sunset` để cảnh báo trước thời hạn ngắt kết nối cho Client, tránh ngắt đột ngột gây sập hệ thống của đối tác.

---

## PHẦN 3: BÁO CÁO KẾT QUẢ CODE MỞ RỘNG BÀI 6 (RESTFUL CRUD)

Code mở rộng đã được triển khai hoàn chỉnh trong file `bai6_books_crud.py` và `app.py`, bao gồm 3 tính năng nâng cấp theo yêu cầu:

### 1. Đoạn code xử lý Tìm kiếm, Sắp xếp và Validate (Python Flask)

```python
# 1. TÌM KIẾM (?q=...) VÀ SẮP XẾP (?sort=title)
@app.route("/books", methods=["GET"])
def list_books():
    q = request.args.get("q", "").strip().lower()
    sort_by = request.args.get("sort", "").strip().lower()
    limit = int(request.args.get("limit", 100))

    result = BOOKS
    # (a) Lọc theo từ khóa tìm kiếm q trong title hoặc author
    if q:
        result = [b for b in result if q in b["title"].lower() or q in b["author"].lower()]

    # (b) Sắp xếp danh sách theo tiêu chí sort=title hoặc sort=year
    if sort_by == "title":
        result = sorted(result, key=lambda b: b["title"].lower())
    elif sort_by == "year":
        result = sorted(result, key=lambda b: b["year"])

    return jsonify(result[:limit]), 200


# 2. VALIDATE NĂM XUẤT BẢN (year >= 1900) KHI TẠO MỚI SÁCH
@app.route("/books", methods=["POST"])
def create_book():
    global _next
    body = request.get_json(silent=True) or {}
    title = body.get("title")
    author = body.get("author")
    year = body.get("year")

    if not title or not author:
        return jsonify({"error": "title and author are required"}), 400

    # (c) Bắt buộc trường year là số nguyên >= 1900
    if year is None or not isinstance(year, int) or year < 1900:
        return jsonify({"error": "year must be an integer >= 1900"}), 400

    book = {"id": _next, "title": title, "author": author, "year": year}
    _next += 1
    BOOKS.append(book)

    return jsonify(book), 201, {"Location": f"/books/{book['id']}"}
```

---

### 2. Kết quả chạy thực nghiệm (Minh chứng lệnh cURL)

- **Test 1: Lấy danh sách, Tìm kiếm & Sắp xếp theo tiêu đề**
  ```bash
  $ curl "http://127.0.0.1:5000/books?q=clean&sort=title"
  HTTP/1.1 200 OK
  Content-Type: application/json

  [
    {
      "author": "Robert C. Martin",
      "id": 1,
      "title": "Clean Code",
      "year": 2008
    }
  ]
  ```

- **Test 2: Thêm mới sách hợp lệ (Năm 1999 >= 1900) -> Status 201 Created**
  ```bash
  $ curl -i -X POST http://127.0.0.1:5000/books \
    -H "Content-Type: application/json" \
    -d '{"title":"Refactoring","author":"Martin Fowler","year":1999}'

  HTTP/1.1 201 Created
  Content-Type: application/json
  Location: /books/3

  {
    "author": "Martin Fowler",
    "id": 3,
    "title": "Refactoring",
    "year": 1999
  }
  ```

- **Test 3: Thử thêm mới sách với năm xuất bản không hợp lệ (Năm 1850 < 1900) -> Status 400 Bad Request**
  ```bash
  $ curl -i -X POST http://127.0.0.1:5000/books \
    -H "Content-Type: application/json" \
    -d '{"title":"Ancient Book","author":"Unknown","year":1850}'

  HTTP/1.1 400 Bad Request
  Content-Type: application/json

  {
    "error": "year must be an integer >= 1900"
  }
  ```
