# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Phạm Minh Cương
- **MSSV:** 2A202602825
- **Lớp:** K4-L3A
- **Repository URL:** `https://github.com/mcnb2005/K4-L3-DAY13-PhamMinhCuong-2A202602825-Monitoring-LLMOps`
- **Commit SHA cuối:** CẦN HỌC VIÊN ĐIỀN SAU KHI COMMIT/PUSH
- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1`
- **Tên project Langfuse cá nhân:** `day13-k4-l3a-2A202602825`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Baseline trước khi sửa | `evidence/00-baseline.txt` |
| Pytest cuối | `evidence/01-pytest.txt` |
| Log validator | `evidence/02-log-validator.txt` |
| Dashboard validator | `evidence/03-dashboard-validator.txt` |
| Structured log | `evidence/04-structured-log.txt` |
| PII redaction | `evidence/05-pii-redaction.txt` |
| Trace list | `evidence/06-trace-list.png` (chi tiết API: `evidence/06-trace-list.txt`) |
| Trace waterfall | `evidence/07-trace-waterfall.png` (chi tiết API: `evidence/07-trace-waterfall.txt`) |
| Trace metadata | `evidence/08-trace-metadata.png` (chi tiết API: `evidence/08-trace-metadata.txt`) |
| Prompt versions | `evidence/09-prompt-versions.png` (chi tiết API: `evidence/09-prompt-versions.txt`) |
| Prompt promote/rollback | Promote v2: `evidence/10a-prompt-promoted-v2.png`; rollback v1: `evidence/10b-prompt-rollback-v1.png` (chi tiết API: `evidence/10-prompt-rollback.txt`) |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric chính thức | `evidence/12-incident-metric.png` (chi tiết: `evidence/12-incident-metric.txt`) |
| Incident log chính thức | `evidence/13-incident-log.txt` |
| Incident trace chính thức | `evidence/14-incident-trace.txt` — cần bổ sung ảnh Langfuse UI |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100 | 100/100 | Không còn thiếu correlation/enrichment |
| `validate_dashboard.py` | 6/6 | 6/6 | Contract đã hợp lệ từ starter; đã bổ sung runtime UI |
| `pytest` | 22 passed | 27 passed | Bổ sung test middleware, PII, trace child và dashboard |
| Số traces hợp lệ | 0 | 14 | 10 workload traces + 4 managed-prompt traces, xác minh qua Observations API v2 |
| Số PII leak | 0 | 0 | Validator độc lập không phát hiện raw PII |
| Latency P95 / TTFT P95 | 154 ms / 51 ms | Challenge: 3503 ms / 51 ms | `rag_slow` làm retrieval tăng rõ rệt và vi phạm SLO 2000 ms |
| Retrieval success rate | 100% | 100% | Practice latency không làm retrieval thất bại |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** middleware xóa context cũ ở đầu request, nhận `x-request-id` hợp lệ hoặc sinh `req-<8-hex>`, bind bằng `structlog.contextvars`, lưu vào `request.state`, rồi trả lại qua `x-request-id` cùng `x-response-time-ms`.
- **Các metadata được ghi vào structured log:** `user_id_hash`, `session_id`, `feature`, `model`, `env`, token, cost, TTFT, latency, quality và trạng thái retrieval.
- **Cách bảo đảm PII được scrub trước khi ghi:** processor `scrub_event` duyệt đệ quy toàn bộ event và chạy trước cả file processor lẫn JSON renderer. Rule bao gồm email, điện thoại Việt Nam, CCCD, thẻ thanh toán và passport.
- **Cách kiểm chứng kết quả:** sau toàn bộ workload và challenge, validator phân tích 109 records với 51 correlation ID, đạt 100/100 và không phát hiện PII. Xem `evidence/02-log-validator.txt` và `evidence/05-pii-redaction.txt`.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** workload đã tạo 10 root traces và 30 observations; Observations API v2 xác nhận mỗi trace có agent/retriever/generation. Ảnh UI xác nhận project cá nhân `day13-k4-l3a-2A202602825`, cấu trúc trace, metadata và prompt versions.
- **Cấu trúc root/retrieval/generation observations:** root `lab-agent-run` chứa child `retrieval` loại retriever và `llm-generation` loại generation. Generation cập nhật model, prompt link, TTFT, input/output/total tokens và input/output/total cost.
- **Cách nối trace với log:** cùng `correlation_id` được đưa vào root metadata và metadata của cả hai child observations.
- **Prompt name:** `day13-chat`
- **Version/label baseline:** v1 với `baseline`; trạng thái cuối có thêm `production` sau rollback.
- **Version/label candidate:** v2 với `candidate` và `latest`.
- **Trace ID của mỗi version:** baseline v1 `5bd2a5563446337f231676cd06e8bc5d`; candidate v2 `930461828e8b7b49a569c976311ca873`.
- **Cách promote và rollback `production`:** đã chuyển `production` sang v2 và xác minh bằng trace `01a21ec25b7589993dee989a1557a28f`; sau đó rollback về v1 và xác minh bằng trace `81b3792ba5af4c3caa13e06114b198eb`. Trạng thái cuối: `production → v1`.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** endpoint `/dashboard` đọc `data/logs.jsonl`, tự refresh 30 giây và hiển thị latency/TTFT, traffic, error/retrieval, cost, tokens và quality trong cửa sổ 60 phút. `/dashboard/data` cung cấp aggregate JSON không chứa PII.
- **SLO và lý do chọn:** 99.5% request trong cửa sổ 28 ngày phải hoàn thành trong 2000 ms. Baseline fake LLM thấp hơn 1 giây nên 2 giây có headroom nhưng vẫn bắt được retrieval chậm.
- **Cách tính error budget:** 100% − 99.5% = 0.5%; tương đương tối đa 5 bad events trên 1000 request hoặc 3 giờ 21 phút 36 giây trong 28 ngày nếu quy đổi theo thời gian.
- **Ba alert và runbook tương ứng:** P95 latency cao, error rate cao, và quality/retrieval suy giảm; mỗi alert có duration, severity, Slack channel, owner và ba bước Metrics → Logs → Traces trong `docs/alerts.md`.

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1`; incident chính thức `rag_slow`.
- **Khoảng thời gian điều tra:** 2026-09-29 17:26:08–17:26:23 Asia/Bangkok.
- **Triệu chứng từ metrics:** trong 5 request chính thức, latency P95 là 3503 ms, vượt SLO 2000 ms; TTFT P95 chỉ 51 ms, error rate 0% và retrieval success 100%.
- **Log line và correlation ID liên quan:** response `req-9767637f` có latency 3503 ms, TTFT 50 ms, retrieval thành công; xem `evidence/13-incident-log.txt`.
- **Trace ID và span gây ảnh hưởng:** trace `a131d5b1a71d649bd54c76ff8e145fb1` có root `lab-agent-run` 3.505 s; child `retrieval` 2.502 s trong khi `llm-generation` chỉ 0.152 s; xem `evidence/14-incident-trace.txt`.
- **Root cause:** incident `rag_slow` thêm khoảng 2.5 giây vào bước retrieval; generation và TTFT không tăng tương ứng.
- **Fix action:** đã tắt incident bằng `python scripts/inject_incident.py --disable`; trong production dùng timeout, cache hoặc fallback retrieval.
- **Preventive measure:** cảnh báo P95 5 phút, theo dõi riêng retrieval success/duration và giữ correlation ID xuyên log/trace.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** scrub toàn bộ event theo cấu trúc đệ quy thay vì chỉ scrub `payload`, để error detail hoặc metadata mới không vô tình đi vòng qua lớp bảo vệ PII.
- **Một lỗi/blocker đã gặp:** máy không có Python hệ thống; Langfuse ban đầu trả 401 vì base URL sai region; API trace cũ trả 410 với organization mới.
- **Cách tìm nguyên nhân và xử lý:** dùng Python 3.12 runtime của Codex để tạo `.venv`, sửa `LANGFUSE_BASE_URL` theo đúng region, rồi dùng Observations API v2 thay cho legacy Trace API. Kết quả cuối xác minh được 14 traces thật.
- **Cách hiểu luồng Metrics → Logs → Traces:** metric khoanh vùng triệu chứng/thời gian, log chọn request bằng `correlation_id`, trace cùng ID chỉ ra child observation gây chậm/lỗi, rồi mới kết luận root cause.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** version/label giúp truy vết và rollback thay đổi; token/cost phát hiện regression tài chính; SLO biến kỳ vọng người dùng thành ngưỡng đo và error budget.
- **Điều quan trọng nhất đã học:** observability chỉ hữu ích khi ba lớp tín hiệu dùng cùng định danh và không đánh đổi bảo mật PII.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** cần bổ sung ảnh Langfuse UI cho incident trace chính thức và điền commit SHA cuối sau lần push cuối.

## 9. Checklist trước khi nộp

- [ ] Kết quả và evidence thuộc commit SHA cuối — kiểm tra lại sau khi commit/push.
- [x] Tất cả evidence local hiện có mở được bằng đường dẫn tương đối.
- [x] Incident chính thức nối đúng metric → log → trace bằng `req-9767637f` và trace `a131d5b1a71d649bd54c76ff8e145fb1`.
- [x] Trace/prompt đã được xác minh qua API và ảnh UI, bao gồm promote v2 và rollback về v1; evidence không để lộ key.
- [x] Repository local chạy lại được theo README bằng `.venv`.
- [ ] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
