# Tuần 6 - Authentication và Authorization

Bùi Đình Cảnh - 24021392

## Nội dung

| Bài | File | Cổng HTTPS |
| --- | --- | --- |
| Lab 1 - Basic Auth | lab1_basic.py | 5001 |
| Lab 2 - API Key | lab2_api_key.py | 5002 |
| Lab 3 - JWT, refresh token | lab3_jwt.py | 5003 |
| Lab 4 - RBAC, scope, ownership | lab4_rbac.py | 5004 |
| Bài tập cuối slide | social_api.py | 5005 |

Bài cuối: [OpenAPI](openapi.yaml), [Security Audit](SecurityAudit.md), [bài làm](Bai_tap_cuoi_slide.md).

## Cài đặt và chạy

```bash
cd Tuan_6
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
export JWT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
flask --app lab1_basic init-demo
python lab1_basic.py
```

Thay lab1_basic bằng tên module tương ứng để chạy bài khác. Khởi tạo dữ liệu một lần cho mỗi bài.

Tài khoản demo: an@vnu.edu.vn (editor), binh@vnu.edu.vn (viewer), admin@vnu.edu.vn (admin), manager@vnu.edu.vn (manager).

Mật khẩu tự nhập khi init-demo, ít nhất 12 ký tự và tối đa 72 byte UTF-8.

## Kiểm tra

```bash
python -m unittest -v test_labs.py
python -m openapi_spec_validator openapi.yaml
```
