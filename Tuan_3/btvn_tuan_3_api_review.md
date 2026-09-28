# Báo cáo: Review GitHub REST API theo 9 tiêu chí

**API được chọn:** GitHub REST API v3

1. **Tài nguyên là danh từ (Đạt)**
   - Các URL đều sử dụng danh từ số nhiều: `/users`, `/repos`, `/issues`. Không có động từ trong URL.

2. **Naming nhất quán (Đạt)**
   - Sử dụng lowercase, phân tách bằng kebab-case hoặc snake_case nhất quán (ví dụ: `per_page`, `sort`, `direction`).

3. **Status code đúng nghĩa (Đạt)**
   - Trả về đúng `200 OK`, `201 Created` khi tạo mới issue, `404 Not Found` khi repo không tồn tại, `403 Forbidden` khi bị rate limit.

4. **Idempotency rõ ràng (Không đạt / Cần cải thiện)**
   - Mặc dù tài liệu rất tốt, một số POST requests tạo resource không hỗ trợ `Idempotency-Key` header rõ ràng như Stripe, dẫn đến rủi ro tạo duplicate nếu retry.

5. **Error response có cấu trúc (Không đạt / Cần cải thiện)**
   - GitHub có cấu trúc lỗi riêng `{"message": "Not Found", "documentation_url": "..."}` nhưng không tuân thủ chuẩn RFC 7807 (`application/problem+json`).

6. **Pagination rõ ràng (Đạt)**
   - Cung cấp Link header rất rõ ràng cho việc chuyển trang (`rel="next"`, `rel="last"`). Hỗ trợ `page` và `per_page`.

7. **Filter/Sort đa dạng (Đạt)**
   - Cho phép sort theo các field nhất định (`?sort=created&direction=asc`), filter theo state (`?state=open`).

8. **Authentication & security (Đạt)**
   - Bắt buộc dùng `Authorization: Bearer <token>`. Rate limit được mô tả rõ và trả về qua các header `X-RateLimit-Limit`.

9. **Versioning + deprecation (Đạt)**
   - Version được quản lý qua Header `Accept: application/vnd.github.v3+json` hoặc cố định từ 2022 qua header `X-GitHub-Api-Version`.

**Đề xuất cải thiện:**
1. Cập nhật error response format theo chuẩn RFC 7807 để các client dễ dàng parse lỗi tự động.
2. Bổ sung `Idempotency-Key` cho các endpoint tạo tài nguyên quan trọng để an toàn hơn khi client retry do network timeout.
