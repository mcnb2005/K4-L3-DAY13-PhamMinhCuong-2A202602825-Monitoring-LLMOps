# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: High end-to-end latency
- Severity: high
- Duration: 5 phút
- Kênh thông báo: Slack `#llm-ops-alerts`
- SLI/SLO liên quan: P95 latency của các request hoàn thành thành công.
- Điều kiện và thời gian duy trì: `latency_p95_ms > 2000` liên tục 5 phút.
- Ảnh hưởng tới người dùng: câu trả lời xuất hiện chậm, timeout ở client và giảm throughput.
- Ba bước kiểm tra đầu tiên:
  1. Xác định thời điểm P95/P99 bắt đầu tăng trên dashboard.
  2. Lọc các `response_sent` chậm trong `data/logs.jsonl` và lấy `correlation_id`.
  3. Mở trace cùng ID, so sánh thời gian của retrieval với generation.
- Mitigation tạm thời: giảm concurrency hoặc chuyển sang retrieval fallback/cache; rollback prompt nếu generation tăng sau khi đổi version.
- Owner: `llm-platform`

## Alert 2

- Tên: Elevated request error rate
- Severity: critical
- Duration: 5 phút
- Kênh thông báo: Slack `#llm-ops-alerts`
- SLI/SLO liên quan: tỷ lệ request thất bại trên tổng request nhận được.
- Điều kiện và thời gian duy trì: `error_rate_pct > 2` liên tục 5 phút.
- Ảnh hưởng tới người dùng: API trả lỗi thay vì câu trả lời.
- Ba bước kiểm tra đầu tiên:
  1. Xem breakdown `error_type` và retrieval success trên dashboard.
  2. Lấy `correlation_id` từ một `request_failed` đại diện.
  3. Mở trace tương ứng và kiểm tra observation cuối cùng trước lỗi.
- Mitigation tạm thời: tắt đường retrieval lỗi, dùng fallback an toàn và retry có backoff trong giới hạn.
- Owner: `api-oncall`

## Alert 3

- Tên: Degraded answer quality
- Severity: medium
- Duration: 10 phút
- Kênh thông báo: Slack `#llm-ops-alerts`
- SLI/SLO liên quan: quality proxy trung bình và retrieval success rate.
- Điều kiện và thời gian duy trì: `quality_score_avg < 0.75` hoặc `retrieval_success_rate_pct < 90` liên tục 10 phút.
- Ảnh hưởng tới người dùng: câu trả lời thiếu ngữ cảnh, kém liên quan hoặc không dựa trên tài liệu.
- Ba bước kiểm tra đầu tiên:
  1. So sánh quality/retrieval với baseline cùng loại feature.
  2. Lấy `correlation_id` của các request quality thấp và kiểm tra log metadata.
  3. So sánh trace, prompt version và số document retrieval với version ổn định gần nhất.
- Mitigation tạm thời: rollback label `production` về prompt baseline và dùng câu trả lời fallback khi retrieval không có kết quả.
- Owner: `llm-quality`
