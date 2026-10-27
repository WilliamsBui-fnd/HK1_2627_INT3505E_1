# Tuần 6 - Authentication và Authorization

Sinh viên: Bùi Đình Cảnh

Mã sinh viên: 24021392

Slide nguồn: SOA - B6_Auth.pdf, 30 trang.

Slide không đánh số lab riêng. Bài làm chia bốn nhóm code thực hành trong slide thành bốn lab như sau:

| Bài | Trang slide | File chạy | Cổng HTTPS |
| --- | --- | --- | --- |
| Lab 1 - HTTP Basic Auth | 6-8 | lab1_basic.py | 5001 |
| Lab 2 - API Key | 9-12 | lab2_api_key.py | 5002 |
| Lab 3 - JWT, refresh token | 13-18 | lab3_jwt.py | 5003 |
| Lab 4 - RBAC, scope, ownership | 23-26 | lab4_rbac.py | 5004 |
| Bài tập cuối slide | 30 | social_api.py, openapi.yaml, SecurityAudit.md | 5005 |

Phần OAuth 2.0/OIDC trang 19-22 là lý thuyết, được trả lời trong Bai_tap_cuoi_slide.md.

## Cài đặt

Yêu cầu Python 3.10 trở lên. Chạy từ thư mục Tuan_6:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
export JWT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
```

Giữ biến JWT_SECRET_KEY trong terminal chạy server và lệnh Flask. Nếu đổi khóa, token đã phát hành trước đó không còn hợp lệ. Không đưa giá trị khóa vào Git. Lab 1 và Lab 2 không cần biến này.

Khởi tạo dữ liệu cho từng ứng dụng, mỗi lệnh sẽ hỏi mật khẩu và xác nhận:

```bash
flask --app lab1_basic init-demo
flask --app lab2_api_key init-demo
flask --app lab3_jwt init-demo
flask --app lab4_rbac init-demo
flask --app social_api init-demo
```

Mật khẩu có ít nhất 12 ký tự, tối đa 72 byte UTF-8. Mật khẩu được hash bằng bcrypt cost 12 và salt riêng. Mỗi lab có database riêng trong instance/. Lệnh init-demo từ chối ghi đè database đã có người dùng.

| Email | Role | Order ID | Bài public | Bài private |
| --- | --- | --- | --- | --- |
| an@vnu.edu.vn | editor | 1 | 1 | 2 |
| binh@vnu.edu.vn | viewer | 2 | 3 | 4 |
| admin@vnu.edu.vn | admin | 3 | 5 | 6 |
| manager@vnu.edu.vn | manager | 4 | 7 | 8 |

## Lab 1 - HTTP Basic Auth

```bash
python lab1_basic.py
```

Trong terminal khác:

```bash
curl -ki https://127.0.0.1:5001/api/orders
curl -ki -u an@vnu.edu.vn https://127.0.0.1:5001/api/orders
```

curl hỏi mật khẩu khi dùng -u chỉ có email. Thiếu hoặc sai credential trả 401 kèm WWW-Authenticate: Basic. Credential đúng trả 200, principal và các order thuộc người dùng hiện tại. Base64 chỉ là encoding; HTTPS bảo vệ credential khi truyền. Các server dùng chứng chỉ tự ký để chạy local; -k chỉ dùng cho demo này.

## Lab 2 - API Key

```bash
python lab2_api_key.py
```

Tạo key bằng tài khoản của chủ key:

```bash
curl -ki -u an@vnu.edu.vn \
  -H 'Content-Type: application/json' \
  -d '{"scopes":["orders:read"],"expires_in":3600,"ip_allowlist":["127.0.0.1/32"]}' \
  https://127.0.0.1:5002/api/keys
```

Response 201 chứa api_key một lần. Đặt key vừa nhận vào biến API_KEY ở terminal test, rồi chạy:

```bash
curl -ki -H "X-Api-Key: $API_KEY" https://127.0.0.1:5002/api/orders
curl -ki -H "X-Api-Key: $API_KEY" https://127.0.0.1:5002/api/orders/2
curl -ki -X POST -H "X-Api-Key: $API_KEY" \
  -H 'Content-Type: application/json' -d '{"item":"SOA","quantity":1}' \
  https://127.0.0.1:5002/api/orders
```

Kết quả lần lượt: 200, 403 vì khác chủ sở hữu, 403 vì key chỉ có orders:read. Tạo key có orders:write để thử POST thành công. owner_id luôn lấy từ key, không nhận từ body.

Quản lý key số 1:

```bash
curl -ki -u an@vnu.edu.vn https://127.0.0.1:5002/api/keys
curl -ki -u an@vnu.edu.vn https://127.0.0.1:5002/api/keys/1
curl -ki -X POST -u an@vnu.edu.vn https://127.0.0.1:5002/api/keys/1/rotate
curl -ki -X DELETE -u an@vnu.edu.vn https://127.0.0.1:5002/api/keys/1
```

Rotate trả key mới và vô hiệu key cũ. DELETE trả 204. Key hết hạn, sai hoặc bị thu hồi trả 401; thiếu scope hoặc sai IP trả 403. Server hash toàn bộ key bằng SHA-256, chỉ lưu hash và metadata. Scope cấp cho key phải nằm trong quyền hiện tại của chủ key. Không nhận secret qua query string và không tin X-Forwarded-For do client tự gửi.

## Lab 3 - JWT và refresh token

```bash
python lab3_jwt.py
```

Ở terminal test có Python, nhập mật khẩu qua getpass rồi gửi JSON qua stdin:

```bash
TOKENS="$(python3 -c 'import getpass,json; print(json.dumps({"email":"an@vnu.edu.vn","password":getpass.getpass("Mật khẩu: ")}))' | curl -ksS -H 'Content-Type: application/json' --data-binary @- https://127.0.0.1:5003/api/auth/login)"
ACCESS_TOKEN="$(printf '%s' "$TOKENS" | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')"
REFRESH_TOKEN="$(printf '%s' "$TOKENS" | python3 -c 'import json,sys; print(json.load(sys.stdin)["refresh_token"])')"
curl -ki -H "Authorization: Bearer $ACCESS_TOKEN" https://127.0.0.1:5003/api/me
curl -ki -H "Authorization: Bearer $ACCESS_TOKEN" https://127.0.0.1:5003/api/orders
TOKENS="$(curl -ksS -X POST -H "Authorization: Bearer $REFRESH_TOKEN" https://127.0.0.1:5003/api/auth/refresh)"
ACCESS_TOKEN="$(printf '%s' "$TOKENS" | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')"
REFRESH_TOKEN="$(printf '%s' "$TOKENS" | python3 -c 'import json,sys; print(json.load(sys.stdin)["refresh_token"])')"
curl -ki -X POST -H "Authorization: Bearer $ACCESS_TOKEN" https://127.0.0.1:5003/api/auth/logout
```

Login và refresh trả access_token, refresh_token, token_type, expires_in, scope. Access sống 15 phút; phiên refresh tối đa 30 ngày từ login. Mỗi lần refresh phải thay cả hai biến token bằng cặp mới. Dùng lại refresh cũ trả 401 và thu hồi cả phiên. Logout thu hồi tất cả access/refresh của phiên đó, kể cả sau khi restart server. Mỗi phiên login độc lập.

JWT chỉ chấp nhận HS256, kiểm exp, iat, nbf, jti, sub, iss, aud và sid; không chứa mật khẩu hoặc email. API chỉ nhận Bearer trong header. Scope bị rút trong database có hiệu lực ngay. Refresh nạp lại quyền hiện tại.

## Lab 4 - RBAC, scope và ownership

```bash
python lab4_rbac.py
```

Login giống Lab 3 nhưng thay cổng thành 5004. Dùng access token do Lab 4 cấp:

```bash
curl -ki -H "Authorization: Bearer $ACCESS_TOKEN" https://127.0.0.1:5004/api/orders/1
curl -ki -X POST -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' -d '{"item":"SOA","quantity":2}' \
  https://127.0.0.1:5004/api/orders
curl -ki -X DELETE -H "Authorization: Bearer $ACCESS_TOKEN" https://127.0.0.1:5004/api/orders/1
curl -ki -H "Authorization: Bearer $ACCESS_TOKEN" https://127.0.0.1:5004/api/admin/users
```

| Endpoint | Role | Scope | Quyền đối tượng |
| --- | --- | --- | --- |
| GET /api/orders | Người dùng đã xác thực | orders:read | Chỉ liệt kê order của mình |
| GET /api/orders/{id} | Người dùng đã xác thực | orders:read | Owner hoặc admin |
| POST /api/orders | admin hoặc manager hoặc editor | orders:write | Tạo order cho chính mình |
| DELETE /api/orders/{id} | admin hoặc manager | orders:read và orders:write | Owner hoặc admin |
| GET /api/admin/users | admin | users:read | Danh sách không chứa password_hash |

require_roles dùng OR; require_scopes dùng AND. Kiểm tra theo thứ tự AuthN, role/scope rồi ownership. Admin được vượt ownership theo policy, vẫn phải có scope. Manager không được xóa order của người khác. Viewer không được tạo order hay gọi chức năng admin.

## Bài tập cuối slide

```bash
python social_api.py
```

Ba endpoint đúng đường dẫn đề bài:

- POST /auth/login: public, không cần scope trước login.
- POST /auth/refresh: refresh token hợp lệ, không cần scope hành động.
- GET /posts/{id}: access token và posts:read; bài private chỉ owner/admin.

Login và refresh tương tự Lab 3, thay URL lần lượt bằng https://127.0.0.1:5005/auth/login và https://127.0.0.1:5005/auth/refresh.

```bash
curl -ki -H "Authorization: Bearer $ACCESS_TOKEN" https://127.0.0.1:5005/posts/1
curl -ki -H "Authorization: Bearer $ACCESS_TOKEN" https://127.0.0.1:5005/posts/2
```

Token của Lab 3 hoặc Lab 4 không dùng được cho social_api vì audience khác nhau. openapi.yaml mô tả request/response, loại token, scope, ownership và mã lỗi của từng endpoint. SecurityAudit.md liệt kê 12 rủi ro cùng biện pháp và giới hạn. social_api giữ đúng ba endpoint đề bài; endpoint logout được thực hành ở Lab 3 và Lab 4.

## Kiểm tra

```bash
python -m unittest -v test_labs.py
python -m openapi_spec_validator openapi.yaml
```

Bộ test gồm 49 bài kiểm thử, có kiểm tra tính hợp lệ của OpenAPI và đối chiếu schema response với API chạy thật trong Flask test client. Test bao phủ 401/403/404, scope, role, BOLA, mass assignment, giới hạn login, API key rotation/revocation, JWT giả mạo, expiry, issuer/audience, refresh đồng thời, replay và logout sau restart. Password test và khóa ký ngẫu nhiên chỉ tồn tại trong fixture; không dùng khi chạy các ứng dụng.

Code không có comment. Tài liệu nộp dạng Markdown và YAML, không cần PDF.
