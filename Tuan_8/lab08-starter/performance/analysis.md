# Lab 4 — Phân tích kết quả

| Kịch bản | Users | Spawn rate | Duration | p95 (ms) | Failure rate | RPS |
|---|---:|---:|---:|---:|---:|---:|
| A | 10 | 2 | 30s | 70 | 0.00% | 4.72 |
| B | 50 | 5 | 60s | 43 | 0.07% | 23.32 |
| C | 200 | 50 | 30s | 680 | 0.08% | 89.87 |

Môi trường: Flask development server + SQLite, chạy trên máy cá nhân.

`search_by_year` lỗi 1% là lỗi giả lập phía client: Locust gọi `response.failure("Simulated 500")`, server vẫn trả 200, không phải HTTP 500 thật.

1. Kịch bản C có p95 cao nhất (680 ms, so với 70 ms ở A và 43 ms ở B). 200 user vào trong 4 giây, Flask dev server và SQLite xử lý gần như tuần tự nên request xếp hàng: median 34 ms nhưng p99 890 ms, max 1434 ms. RPS chỉ tăng từ 23.32 (B) lên 89.87 (C) dù user gấp 4 lần: bắt đầu bão hoà. A có p95 70 ms cao hơn B vì chỉ có 112 request và các request đầu (khởi động) kéo p95 lên.

2. Chỉ `GET /books?year=` có failure (A 0%, B 0.55%, C 0.55%). Đây là lỗi giả lập 1% do Locust gọi `response.failure("Simulated 500")`, server vẫn trả 200, nên tỉ lệ không tăng theo số user mà chỉ dao động theo số mẫu. Các endpoint khác 0% lỗi; 404 của `GET /books/{id}` (id ngẫu nhiên) được tính là thành công vì là hành vi mong đợi.

3. Với SLO p95 < 300 ms, A và B đạt, C không đạt (680 ms). Đề xuất baseline cho CI gate: chạy kịch bản B, fail nếu p95 tổng > 100 ms hoặc failure rate thật (không tính lỗi giả lập) > 1%. Kết quả này không đại diện cho production vì dùng dev server, SQLite và máy cá nhân.

4. Bonus — connection pool giới hạn 5: khi 200 user truy cập đồng thời, chỉ 5 request giữ được kết nối DB, số còn lại phải chờ; quá `pool_timeout` thì bị lỗi `TimeoutError` → HTTP 500. Kiểm chứng: cấu hình `SQLALCHEMY_ENGINE_OPTIONS={"pool_size": 5, "max_overflow": 0, "pool_timeout": 1}` cho DB dùng pool (vd. PostgreSQL), chạy lại kịch bản C và so sánh với khi không giới hạn: p95/p99 tăng vọt, RPS bị chặn trần dù tăng user, và Error report xuất hiện lỗi 500.
