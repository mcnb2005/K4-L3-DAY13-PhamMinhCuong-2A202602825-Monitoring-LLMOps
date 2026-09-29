# Evidence cá nhân

Đặt ảnh hoặc output text dùng để chấm vào thư mục này. Danh sách đầy đủ xem tại [docs/SUBMISSION.md](../../docs/SUBMISSION.md).

Tên file gợi ý:

```text
01-pytest.png
02-log-validator.png
03-dashboard-validator.png
04-structured-log.png
05-pii-redaction.png
06-trace-list.png
07-trace-waterfall.png
08-trace-metadata.png
09-prompt-versions.png
10-prompt-rollback.png
11-dashboard-overview.png
12-incident-metric.png
13-incident-log.png
14-incident-trace.png
```

Có thể dùng `.txt` cho output của tests/validators. Có thể tách dashboard thành nhiều ảnh nếu một ảnh không đọc rõ.

Ảnh `04`, `05`, `13` lấy từ terminal hoặc `data/logs.jsonl`. Ảnh `06`–`10`, `14` lấy từ project Langfuse cá nhân `day13-k4-l3a-<MSSV>` và nên nhìn thấy tên project. Không mở/chụp trang API Keys.

Từ `submission/REPORT.md`, dẫn ảnh bằng đường dẫn tương đối:

```markdown
![Trace waterfall](evidence/07-trace-waterfall.png)
```

Không commit secret, API key, PII thô hoặc evidence của học viên/lớp khác.

## Trạng thái evidence hiện tại

Đã tạo và kiểm chứng local:

- `00-baseline.txt`
- `01-pytest.txt`
- `02-log-validator.txt`
- `03-dashboard-validator.txt`
- `04-structured-log.txt`
- `05-pii-redaction.txt`
- `06-trace-list.txt`
- `06-trace-list.png`
- `07-trace-waterfall.txt`
- `07-trace-waterfall.png`
- `08-trace-metadata.txt`
- `08-trace-metadata.png`
- `09-prompt-versions.txt`
- `09-prompt-versions.png`
- `10-prompt-rollback.txt`
- `10a-prompt-promoted-v2.png`
- `10b-prompt-rollback-v1.png`
- `11-dashboard-overview.png`
- `12-practice-incident-metric.png`
- `13-practice-incident-log.txt`
- `12-incident-metric.png`
- `12-incident-metric.txt`
- `13-incident-log.txt`
- `14-incident-trace.txt`

Hai file `12-practice-*` và `13-practice-*` chỉ chứng minh workflow với scenario
`rag_slow`, không thay thế challenge chính thức. Evidence text `06`–`10` đã được
xác minh bằng Langfuse Observations API v2. Ảnh UI đã có cho `06`–`09`, bước
promote v2 (`10a`) và rollback về v1 (`10b`).
Incident chính thức `12`–`14` đã được xác minh bằng dashboard, structured log và
Langfuse Observations API v2. Ảnh dashboard đã có; còn cần bổ sung ảnh trace UI
và commit SHA cuối.
