# Lab 2 — Lint OpenAPI bằng Spectral

## Chạy

```bash
npx @stoplight/spectral-cli lint openapi.yaml --ruleset .spectral.yml
# No results with a severity of 'error' found!   (0 problems)
```

## Ba lỗi đã sửa trong `openapi.yaml`

| # | Lỗi | Sửa | Rule bắt lỗi |
|---|---|---|---|
| 1 | `GET /books` thiếu `operationId` | Thêm `operationId: listBooks` | `operation-operationId` (có sẵn trong spectral:oas) |
| 2 | Response `204` của `DELETE /books/{id}` có `content` | Xoá `content` | `no-body-on-204` |
| 3 | `Book.year` có `type: string` | Đổi thành `type: integer` (min 1450, max 2100) | `book-year-integer` |

Ngoài ra bổ sung `info.contact`, global `tags`, `tags` và `description` cho mọi operation để hết các warning của `spectral:oas`.

## Custom rule: `response-200-schema-not-empty`

Mọi response `200` có `content` thì phải có `schema`, và `schema` không được rỗng.

Rule này bắt các trường hợp:

- Có `content` nhưng thiếu `schema` → client không biết sẽ nhận gì.
- `schema: {}` → chấp nhận mọi dữ liệu, nên test jsonschema luôn pass và không bảo vệ được gì.

Đã kiểm tra bằng cách cố ý gây lỗi trên bản sao của spec: `schema: {}` và thiếu `schema` đều bị báo `error`.

## Câu hỏi: spec pass Spectral nhưng Flask trả sai field — test nào bắt?

Spectral chỉ đọc file spec, không chạy code, nên không bắt được. Cần test chạy API thật rồi đối chiếu response với schema trong spec: `pytest` + `jsonschema`, ví dụ `test_response_extra_field_blocked` trong `tests/test_lab01.py` (`additionalProperties: false` chặn field lạ như `password_hash`, `type: integer` chặn số bị đổi thành chuỗi).
