# Lab 4 — Phân tích kết quả

| Kịch bản | Users | Spawn rate | Duration | p95 (ms) | Failure rate | RPS |
|---|---:|---:|---:|---:|---:|---:|
| A | 10 | 2 | 30s | 12 | 0.00% | 4.68 |
| B | 50 | 5 | 60s | 16 | 0.07% | 23.50 |
| C | 200 | 50 | 30s | 97 | 0.14% | 97.46 |

Môi trường: Flask development server + SQLite, chạy trên máy cá nhân.

`search_by_year` lỗi 1% là lỗi giả lập phía client: Locust gọi `response.failure("Simulated 500")`, server vẫn trả 200, không phải HTTP 500 thật.

1. Kịch bản C có p95 cao nhất (97 ms, so với 12 ms và 16 ms). 200 user vào trong 4 giây, Flask dev server và SQLite xử lý gần như tuần tự nên request phải xếp hàng. Median vẫn chỉ 9 ms nhưng p95 tăng mạnh, p99 lên 190 ms: phần đuôi chậm do chờ, không phải do từng request chậm hơn. RPS tăng gần tuyến tính theo số user (4.7 → 23.5 → 97.5).

2. Chỉ `GET /books?year=` có failure (0% → 0.49% → 1.02%). Đây là lỗi giả lập 1% nên tỉ lệ thực chất không tăng theo số user, chỉ là A có quá ít request (21) để ra được 1 lần lỗi. Các endpoint khác 0% lỗi; 404 của `GET /books/{id}` (id ngẫu nhiên) được tính là thành công vì là hành vi mong đợi.

3. Với SLO p95 < 300 ms, cả 3 kịch bản đều đạt. Đề xuất baseline cho CI gate: chạy kịch bản B, fail nếu p95 tổng > 50 ms (khoảng 3 lần mức đo được) hoặc failure rate thật (không tính lỗi giả lập) > 1%. Kết quả này không đại diện cho production vì dùng dev server, SQLite và máy cá nhân.

4. Bonus — connection pool giới hạn 5: khi 200 user truy cập đồng thời, chỉ 5 request giữ được kết nối DB, số còn lại phải chờ; quá `pool_timeout` thì bị lỗi `TimeoutError` → HTTP 500. Kiểm chứng: cấu hình `SQLALCHEMY_ENGINE_OPTIONS={"pool_size": 5, "max_overflow": 0, "pool_timeout": 1}` cho DB dùng pool (vd. PostgreSQL), chạy lại kịch bản C và so sánh với khi không giới hạn: p95/p99 tăng vọt, RPS bị chặn trần dù tăng user, và Error report xuất hiện lỗi 500.
