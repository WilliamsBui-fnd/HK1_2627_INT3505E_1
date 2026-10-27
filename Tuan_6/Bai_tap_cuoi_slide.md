# Bài tập cuối slide buổi 6

Sinh viên: Bùi Đình Cảnh

Mã sinh viên: 24021392

## Yêu cầu và bài nộp

Slide trang 30 yêu cầu OpenAPI cho POST /auth/login, POST /auth/refresh và GET /posts/{id}; mỗi endpoint cần làm rõ scope, lỗi và HTTP status. Bài nộp kèm SecurityAudit.md liệt kê ít nhất 5 điểm có thể lộ.

Các file tương ứng:

- openapi.yaml: đặc tả OpenAPI 3.1 cho đủ ba endpoint.
- social_api.py: API mẫu chạy được theo đặc tả.
- SecurityAudit.md: 12 nhóm rủi ro, biện pháp đã làm và giới hạn còn lại.
- test_labs.py: kiểm tra OpenAPI hợp lệ, schema response và các quyết định phân quyền.

## Thiết kế xác thực và phân quyền

API dùng login nội bộ bằng email/password, cấp JWT Bearer. Đây không phải flow OAuth 2.0 Password grant. Client không được yêu cầu role hoặc tự cấp scope trong body login. Quyền được lấy từ database.

AuthN xác định người gọi từ credential hoặc token hợp lệ. AuthZ kiểm tra scope hiện tại và chính sách đối với bài viết. Token hợp lệ không tự cho phép đọc mọi bài.

| Endpoint | Credential | Scope cần có | Thành công | Lỗi |
| --- | --- | --- | --- | --- |
| POST /auth/login | email và password trong JSON | Không cần scope trước login | 200, cặp access/refresh | 400 JSON/trường sai; 401 sai credential hoặc tài khoản bị khóa; 413 body quá lớn; 415 sai Content-Type; 429 vượt giới hạn xác thực |
| POST /auth/refresh | Refresh token qua Authorization Bearer | Không yêu cầu scope hành động | 200, cặp token mới | 401 thiếu/sai/hết hạn/sai loại token, phiên bị thu hồi, refresh replay hoặc tài khoản bị khóa |
| GET /posts/{id} | Access token qua Authorization Bearer | posts:read trong token và database | 200, bài viết được phép đọc | 400 ID sai; 401 token không hợp lệ; 403 thiếu scope hoặc không có quyền đọc bài private; 404 không có bài viết |

Do dùng HTTP Bearer thay vì OAuth 2.0, trường security trong OpenAPI có danh sách scope rỗng. Scope hành động được ghi rõ trong description và x-required-scopes. Điều này tránh mô tả sai local login thành OAuth flow.

## Chính sách bài viết

Bài public: mọi tài khoản đã xác thực có posts:read được đọc.

Bài private: chỉ tác giả hoặc admin được đọc và vẫn cần posts:read. User thường đọc bài private của người khác nhận 403. ID không tồn tại nhận 404. Không trả password_hash hoặc thông tin đăng nhập của tác giả trong response.

## Vòng đời token

Access token sống 900 giây. Token có sub là ID dạng chuỗi, roles, scopes, sid, jti, iat, nbf, exp, iss và aud. Server cố định HS256; issuer là soa-week6; audience của bài cuối là social_api. Secret được cấp từ biến môi trường và sinh ngẫu nhiên.

Refresh token thuộc phiên tối đa 30 ngày tính từ login. Mỗi lần refresh, server nạp quyền hiện tại, xoay refresh_jti bằng UPDATE có điều kiện rồi cấp cặp token mới. Thời hạn phiên không tăng. Nếu dùng lại refresh cũ, toàn bộ phiên bị thu hồi. Access token không dùng thay refresh token và ngược lại.

Social API này giới hạn đúng ba endpoint trong đề. Logout và kiểm chứng thu hồi sau restart nằm ở Lab 3 và Lab 4; trước khi mở rộng social API thành sản phẩm cần thêm chức năng kết thúc phiên.

## OAuth 2.0, PKCE và OIDC trong slide

OAuth 2.0 là framework ủy quyền, JWT là định dạng token. OAuth có thể dùng opaque token hoặc JWT; JWT cũng có thể được cấp bởi login nội bộ như bài này.

Bốn vai trò OAuth là Resource Owner, Client, Authorization Server và Resource Server. Khi client cần quyền của người dùng, lựa chọn trong slide là Authorization Code với PKCE:

1. Client sinh code_verifier ngẫu nhiên, code_challenge bằng BASE64URL(SHA256(code_verifier)) và state.
2. Client chuyển trình duyệt tới Authorization Server với client_id, redirect_uri, scope, state và code_challenge S256.
3. Người dùng xác thực và đồng ý quyền tại Authorization Server; client không nhận mật khẩu.
4. Authorization Server chuyển trình duyệt về redirect_uri đã đăng ký, mang code và state; client kiểm tra state.
5. Client gửi code, code_verifier và redirect_uri tới token endpoint qua HTTPS. Confidential client xác thực thêm; public client không giữ client_secret.
6. Authorization Server kiểm PKCE và trả access token, có thể kèm refresh token. Client dùng access token gọi Resource Server theo scope.

M2M không có người dùng có thể dùng Client Credentials. Tránh Implicit và không dùng Resource Owner Password grant theo nội dung slide. Refresh không gửi lại code_verifier của PKCE.

OIDC bổ sung lớp danh tính cho OAuth, gồm ID Token và có thể dùng UserInfo. Khi cần đăng nhập qua nhà cung cấp danh tính bên ngoài thì dùng OIDC; không dùng ID Token thay access token để gọi API tài nguyên.
