# Security Audit - Bài tập cuối slide buổi 6

Sinh viên: Bùi Đình Cảnh

Mã sinh viên: 24021392

Phạm vi: bốn lab Authentication/Authorization và social_api.py. Đây là môi trường thực hành local, dữ liệu demo trong SQLite. Các kiểm tra dưới đây dựa trên code và test_labs.py.

## 1. Credential bị đọc trên đường truyền

Basic Auth chỉ mã hóa biểu diễn bằng Base64; ai có header có thể lấy lại email và mật khẩu. API key và JWT Bearer bị lộ cũng có thể bị dùng lại trong thời hạn còn hiệu lực.

Đã xử lý: các file lab và social_api chạy HTTPS local với chứng chỉ tự ký; credential không được truyền trong URL. Response đặt Cache-Control: no-store. Basic Auth trả challenge WWW-Authenticate khi thiếu hoặc sai credential.

Giới hạn: curl -k chỉ phục vụ demo chứng chỉ tự ký. Khi triển khai cần TLS với chứng chỉ hợp lệ, cấu hình HTTPS ở reverse proxy và không dùng Flask development server cho production.

## 2. Database lộ mật khẩu

Lưu plaintext hoặc dùng SHA-256 trực tiếp cho mật khẩu sẽ làm việc dò mật khẩu dễ hơn khi database bị lấy cắp.

Đã xử lý: database.py dùng bcrypt cost 12 và salt riêng cho từng người dùng. Code kiểm tra giới hạn 72 byte UTF-8 để tránh cắt mật khẩu. Response chỉ lấy các trường công khai, không xuất password_hash.

Giới hạn: hệ thống mới có thể chuyển sang Argon2id theo phần trang 27-28. Cần đo chi phí hash trên hạ tầng triển khai; cost 4 trong test chỉ phục vụ kiểm thử, cấu hình chạy mặc định là 12.

## 3. Brute force, credential stuffing và dò tài khoản

Thông báo khác nhau cho email không tồn tại và mật khẩu sai giúp dò danh sách tài khoản. Không giới hạn login tạo điều kiện thử mật khẩu hàng loạt.

Đã xử lý: common.py giới hạn 10 lần xác thực trong 60 giây theo cả IP lẫn email chuẩn hóa; bộ đếm lưu SQLite và cập nhật trong transaction. Quá giới hạn trả 429 cùng Retry-After. Mật khẩu sai, email không tồn tại và tài khoản bị khóa có cùng lỗi đăng nhập. Tài khoản không tồn tại vẫn chạy bcrypt với dummy hash.

Giới hạn: dummy hash giảm khác biệt thời gian, không chứng minh thời gian phản hồi tuyệt đối bằng nhau. Rate limit theo tài khoản có thể bị lợi dụng gây gián đoạn login; hệ thống lớn cần đánh giá chính sách, dùng kho đếm tập trung, giám sát và cân nhắc MFA.

## 4. Secret hoặc dữ liệu phiên bị commit lên Git

JWT signing key bị lộ cho phép tạo token giả; database có hash mật khẩu, hash API key và metadata phiên cũng là dữ liệu cần bảo vệ.

Đã xử lý: signing key lấy từ JWT_SECRET_KEY, từ chối khóa ngắn hơn 32 byte; README sinh khóa bằng CSPRNG. .gitignore loại .env, instance/ và các file SQLite. Không có credential demo cố định để chạy server; init-demo hỏi mật khẩu qua prompt.

Giới hạn: môi trường triển khai cần secret manager và quy trình thu hồi/đổi khóa. Độ dài khóa không tự bảo đảm entropy; phải dùng cách sinh ngẫu nhiên đã hướng dẫn. File đã từng được track cần được xử lý riêng nếu phát hiện lộ.

## 5. JWT giả mạo, sai thuật toán hoặc dùng nhầm dịch vụ

Chấp nhận alg=none, tin thuật toán do client chọn, bỏ exp hoặc không kiểm issuer/audience có thể cho phép token giả hoặc token từ dịch vụ khác truy cập API.

Đã xử lý: tokens.py cố định HS256, kiểm chữ ký bằng Flask-JWT-Extended/PyJWT, kiểm exp, iat, nbf, iss, aud và bắt buộc các claim định danh/phiên. Audience khác nhau cho Lab 3, Lab 4 và social_api. Access token sống 15 phút. Payload không chứa email, mật khẩu hoặc key.

Giới hạn: đây là JWT được ký, payload đọc được và không được xem là nơi giữ secret. Khóa ký bị lộ cần ngừng tin cậy khóa đó; bài lab chưa triển khai nhiều signing key với kid.

## 6. Refresh token bị replay hoặc hai request refresh chạy đồng thời

Nếu refresh token dùng lại vô hạn, kẻ lấy được token có thể kéo dài quyền truy cập. Nếu cập nhật jti thiếu điều kiện nguyên tử, hai request có thể cùng xoay token thành công.

Đã xử lý: sessions lưu refresh_jti hiện tại; refresh dùng UPDATE có điều kiện jti, expires_at và revoked_at. Mỗi token chỉ xoay thành công một lần. Dùng lại token cũ thu hồi toàn bộ phiên, bao gồm access token và refresh mới. Phiên tối đa 30 ngày từ login. Quyền được nạp lại từ database khi refresh.

Giới hạn: client cần tránh gửi refresh đồng thời và không tự động retry token cũ sau khi đã nhận cặp mới. Cơ chế phát hiện replay chủ động thu hồi cả phiên nên có thể yêu cầu đăng nhập lại khi client gửi trùng.

## 7. Logout không thu hồi refresh hoặc thu hồi bị mất sau restart

Chỉ xóa token ở client không ngăn người khác tiếp tục dùng token đã lấy được. Blocklist chỉ lưu trong RAM sẽ mất khi server khởi động lại.

Đã xử lý: Lab 3 và Lab 4 có POST /api/auth/logout, ghi revoked_at vào SQLite. Mỗi request kiểm tra phiên, thời hạn và trạng thái tài khoản. Test tạo lại ứng dụng vẫn xác nhận access và refresh bị từ chối sau logout.

Giới hạn: social_api giữ đúng ba endpoint đề bài nên chưa có endpoint logout riêng. Cần bổ sung logout hoặc chức năng quản lý phiên trước khi mở rộng thành ứng dụng thực tế; hiện phiên social hết hiệu lực theo TTL, khi bị thu hồi trong kho phiên hoặc phát hiện refresh replay.

## 8. BOLA - đọc hoặc xóa tài nguyên của người khác

User A sửa ID trong URL để đọc order hoặc bài private của B nếu chỉ kiểm token và scope mà không kiểm quyền đối tượng.

Đã xử lý: Lab 1 và Lab 2 liệt kê order theo owner; Lab 2 kiểm owner khi truy cập order bằng ID. authorization.py kiểm owner cho GET/DELETE order của Lab 4, cho admin vượt ownership theo policy. social_api.py chỉ cho owner hoặc admin đọc bài private; mọi request vẫn cần posts:read.

Giới hạn: 403 cho bài private khác chủ cho thấy tài nguyên tồn tại; đây là lựa chọn đã mô tả trong spec. Nếu chính sách yêu cầu ẩn sự tồn tại thì đổi thống nhất implementation, spec và test sang 404.

## 9. BFLA - gọi chức năng admin bằng tài khoản thường

Endpoint quản trị chỉ kiểm đã login sẽ cho user thường gọi chức năng có quyền cao. Chỉ dựa vào role trong token cũ cũng trì hoãn hiệu lực khi hạ quyền.

Đã xử lý: Lab 4 có require_roles với OR, require_scopes với AND, rồi kiểm ownership. GET /api/admin/users yêu cầu admin và users:read. DELETE order yêu cầu admin hoặc manager, đủ orders:read và orders:write. Role lấy lại từ database mỗi request; scope hiệu lực là giao giữa token và database.

Giới hạn: thay đổi quyền cần cập nhật role và scope đúng policy. Cấu hình role/scope hiện phục vụ phạm vi demo, chưa có API quản lý quyền hay tenant.

## 10. Mass assignment và lộ thuộc tính nhạy cảm

Client gửi roles, is_admin hoặc owner_id trong body để tự nâng quyền nếu backend cập nhật trực tiếp mọi trường. Trả nguyên row users có thể lộ password_hash.

Đã xử lý: json_body chỉ nhận whitelist trường. Login chỉ nhận email/password; tạo order chỉ nhận item/quantity. Owner lấy từ principal. public_user chỉ xuất id, email, roles và scopes; API key metadata bỏ hash.

Giới hạn: khi thêm endpoint PATCH hoặc trường mới phải rà lại whitelist và serializer. Không được dùng dict của row users làm response trực tiếp.

## 11. API key bị lộ, có quyền quá rộng hoặc không thu hồi được

Key tồn tại lâu, được gửi qua query string hoặc được cấp quyền vượt chủ sở hữu làm tăng tác hại khi bị lấy cắp.

Đã xử lý: lab2_api_key.py sinh 32 byte ngẫu nhiên, lưu SHA-256 của toàn bộ key, chỉ hiện plaintext khi tạo/rotate. Có scope, hết hạn, revoked_at, IP allowlist và kiểm quyền chủ key. Rotate vô hiệu key cũ trong cùng transaction. Query string không được dùng để xác thực. Không tin X-Forwarded-For do client tự gửi.

Giới hạn: SHA-256 ở đây dành cho key có entropy cao, không dùng cho mật khẩu. IP allowlist cần được cấu hình lại cẩn thận khi chạy sau proxy; chưa có cơ chế tự động phát hiện key lộ.

## 12. Token lộ qua trình duyệt, log và vận hành

JWT trong localStorage có thể bị JavaScript đọc khi có XSS. Password/token trong URL hoặc log có thể bị truy cập ngoài phạm vi dự kiến. Dependency và sự kiện auth cũng cần được theo dõi.

Đã xử lý: API nhận token qua header, không qua URL/cookie, không tự ghi log password/token và không tạo giao diện lưu localStorage. README nhập password bằng prompt/getpass. Mọi response có no-store và nosniff. Có test cho credential, quyền, token và schema OpenAPI.

Giới hạn: ví dụ curl dùng token trong terminal chỉ dành cho local. Chưa triển khai giao diện, BFF, audit log tập trung hay cảnh báo bất thường. Trước production cần quản lý phiên ở client, chống XSS; nếu dùng cookie cần HttpOnly/Secure, SameSite phù hợp và chống CSRF. Cần khóa phiên bản dependency sau khi đánh giá, quét lỗ hổng và bổ sung log sự kiện đã che secret.

## Kiểm chứng

```bash
python -m unittest -v test_labs.py
python -m openapi_spec_validator openapi.yaml
```

Bộ kiểm thử có 49 test; phạm vi là hành vi API và contract trong môi trường local, không thay thế kiểm thử xâm nhập hoặc đánh giá hệ thống triển khai.
