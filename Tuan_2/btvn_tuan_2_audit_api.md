# Báo Cáo Audit RESTful API: GitHub Public API

- **Họ và tên:** Bùi Đình Cảnh
- **Mã sinh viên:** 24021392
- **Môn học:** Kiến trúc Hướng Dịch vụ (SOA)
- **Tên bài tập:** BTVN Buổi 2 - Audit một Public API thực tế

---

## 1. Giới thiệu API được chọn

Trong bài tập này, em chọn phân tích **GitHub REST API** (`https://api.github.com`).
Đây là hệ thống REST API công khai phổ biến cung cấp quyền truy cập dữ liệu người dùng, repositories, issues và commit.

---

## 2. Phân tích 5 Endpoint tiêu biểu

### Endpoint 1: Lấy câu triết lý ngẫu nhiên (`GET /zen`)
- **HTTP Method:** `GET`
- **URL:** `https://api.github.com/zen`
- **Status Code:** `200 OK`
- **Response Headers quan trọng:**
  - `Content-Type: text/plain; charset=utf-8`
  - `Cache-Control: no-cache`
- **Đánh giá RESTful:**
  - Endpoint dùng đúng method `GET` để lấy dữ liệu. Trả về trạng thái `200 OK` khi thành công.

---

### Endpoint 2: Lấy thông tin tài khoản người dùng (`GET /users/{username}`)
- **HTTP Method:** `GET`
- **URL Ví dụ:** `https://api.github.com/users/octocat`
- **Status Codes:**
  - `200 OK`: Khi tìm thấy người dùng (trả về JSON thông tin chi tiết).
  - `404 Not Found`: Khi không tìm thấy `username`.
- **Response Headers quan trọng:**
  - `Content-Type: application/json; charset=utf-8`
  - `ETag: W/"..."` (Dùng để kiểm tra bộ nhớ đệm conditional request).
  - `x-ratelimit-limit: 60` (Giới hạn số request/giờ cho client chưa xác thực).
- **Đánh giá RESTful:**
  - Thiết kế URI định danh tài nguyên chuẩn `/users/{username}`.
  - Sử dụng header `ETag` chuẩn RESTful để tối ưu hóa bộ nhớ đệm (caching).

---

### Endpoint 3: Lấy danh sách Repositories công khai (`GET /users/{username}/repos`)
- **HTTP Method:** `GET`
- **URL Ví dụ:** `https://api.github.com/users/octocat/repos?page=1&per_page=5`
- **Status Code:** `200 OK`
- **Response Headers quan trọng:**
  - `Content-Type: application/json; charset=utf-8`
  - `Link: <...page=2>; rel="next", <...page=1>; rel="first"` (Chuẩn HATEOAS cho phân trang).
- **Đánh giá RESTful:**
  - Sử dụng Query Parameters (`page`, `per_page`) để hỗ trợ phân trang dữ liệu.
  - Áp dụng chuẩn **HATEOAS (Level 3 trong Mô hình Richardson)** thông qua header `Link` hướng dẫn người dùng chuyển trang tiếp theo.

---

### Endpoint 4: Lấy thông tin một Repository cụ thể (`GET /repos/{owner}/{repo}`)
- **HTTP Method:** `GET`
- **URL Ví dụ:** `https://api.github.com/repos/octocat/Hello-World`
- **Status Codes:**
  - `200 OK`: Thành công.
  - `404 Not Found`: Repository không tồn tại hoặc ở chế độ riêng tư (Private).
- **Response Headers quan trọng:**
  - `Cache-Control: public, max-age=60, s-maxage=60`
  - `ETag: "..."`
- **Đánh giá RESTful:**
  - Định danh tài nguyên phân cấp rõ ràng (`/repos/{owner}/{repo}`).
  - Hỗ trợ HTTP Caching rõ ràng.

---

### Endpoint 5: Tạo mới một Repository (`POST /user/repos`)
- **HTTP Method:** `POST`
- **URL:** `https://api.github.com/user/repos`
- **Request Body (JSON):**
  ```json
  {
    "name": "my-new-repo",
    "private": false
  }
  ```
- **Status Codes:**
  - `201 Created`: Tạo repository thành công.
  - `401 Unauthorized`: Chưa truyền Token xác thực (`Authorization: Bearer ...`).
  - `422 Unprocessable Entity`: Tên repository bị trùng hoặc không hợp lệ.
- **Response Headers quan trọng:**
  - `Location: https://api.github.com/repos/octocat/my-new-repo`
- **Đánh giá RESTful:**
  - Dùng đúng HTTP Method `POST` cho thao tác tạo mới tài nguyên.
  - Trả về đúng Status Code `201 Created` kèm header `Location` chỉ tới tài nguyên vừa tạo.
  - Phân biệt rõ ràng lỗi xác thực (`401`) và lỗi validate dữ liệu đầu vào (`422`).

---

## 3. Đánh giá tổng quan tính RESTful của GitHub API

1. **Chuẩn thiết kế URI:** Các tài nguyên được đặt tên theo danh từ số nhiều (như `/users`, `/repos`), cấu trúc phân cấp trực quan và nhất quán.
2. **Sử dụng HTTP Verbs & Status Codes:** Phân biệt rõ ràng các phương thức `GET`, `POST`, `PUT`, `DELETE` và các mã phản hồi chuẩn (`200`, `201`, `304`, `401`, `404`, `422`).
3. **Quản lý Cache & Conditional Requests:** Sử dụng hiệu quả các header `ETag`, `If-None-Match` và `Cache-Control`.
4. **Cấp độ trưởng thành (Richardson Maturity Model):** GitHub REST API đạt **Mức 3 (Hypermedia Controls / HATEOAS)** nhờ cung cấp các liên kết chuyển hướng linh hoạt trong header `Link`.
