# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Trần Phạm Thái Vũ
- **MSSV:** 2A202602695
- **Lớp:** K4-L3A
- **Repository URL:** https://github.com/VinUni-AI20k/K4-L3-DAY13-TranPhamThaiVu-2A202602695-Monitoring-LLMOps
- **Commit SHA cuối:** 74d936fc421330bb4d9e05b0589aedaa616a2a91
- **Challenge ID:** day13-k4-l3a-monitoring-llmops-v1
- **Tên project Langfuse cá nhân:** `day13-k4-l3a-2A202602695`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.png` |
| Log validator | `evidence/02-log-validator.png` |
| Dashboard validator | `evidence/03-dashboard-validator.png` |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10-prompt-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100 | 100/100 | Đạt điểm tuyệt đối, hoàn thiện schema, propagation, context enrichment và PII scrubbing. |
| `validate_dashboard.py` | HỢP LỆ: 6/6 panel | HỢP LỆ: 6/6 panel | Đáp ứng 100% contract schema của dashboard YAML. |
| `pytest` | 22 passed in 3.02s | 22 passed in 2.70s | 100% unit tests passed ổn định, không có regression. |
| Số traces hợp lệ | 0 (chưa phân cấp) | 27+ traces | Đạt và vượt xa yêu cầu &ge; 10 traces trên project Langfuse cá nhân. |
| Số PII leak | 0 | 0 | Đã kiểm thử với mẫu chứa Email, Phone VN, CCCD, Thẻ tín dụng; 100% được che thành `[REDACTED_*]`. |
| Latency P95 / TTFT P95 | 358.0 ms / 50.0 ms | 355.0 ms / 51.0 ms | Bình thường đạt ~355ms; khi có sự cố challenge P95 tăng vọt lên 2653.7 ms phản ánh rõ nét triệu chứng. |
| Retrieval success rate | 100.0% | 100.0% | Đo lường chính xác tỷ lệ truy xuất công cụ trong điều kiện chuẩn. |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:**
  Tại [app/middleware.py](file:///d:/Lab/K4-L3A-Day13-TranPhamThaiVu-2A202602695-Monitoring-LLMOps/app/middleware.py), gọi `clear_contextvars()` ngay đầu hàm dispatch để cô lập context giữa các request. Trích xuất `x-request-id` từ header nếu client truyền lên; nếu không có, tự động sinh mới với định dạng chuẩn `req-<8-hex>` (`req-` + `uuid.uuid4().hex[:8]`). Sau đó gọi `bind_contextvars(correlation_id=correlation_id)` và gán vào `request.state.correlation_id`. Cuối cùng, gán trả lại cho client qua response headers `x-request-id` và `x-response-time-ms`.
- **Các metadata được ghi vào structured log:**
  Các trường bắt buộc và ngữ cảnh mở rộng gồm: `ts` (ISO 8601 UTC), `level` (info/error/warning), `service` (`api`), `event` (`request_received`, `response_sent`, `request_failed`), `correlation_id`, `user_id_hash` (băm SHA-256 ẩn danh danh tính), `session_id`, `feature`, `model`, `env` (`dev`), `latency_ms`, `ttft_ms`, `tokens_in`, `tokens_out`, `cost_usd`, `quality_score`, `tool_name`, `tool_success`.
- **Cách bảo đảm PII được scrub trước khi ghi:**
  Trong [app/logging_config.py](file:///d:/Lab/K4-L3A-Day13-TranPhamThaiVu-2A202602695-Monitoring-LLMOps/app/logging_config.py), đăng ký processor `scrub_event` vào pipeline của `structlog` **trước** `JsonlFileProcessor` (bước ghi file `data/logs.jsonl`) và `structlog.processors.JSONRenderer()` (bước render console). Hàm `_scrub_value` duyệt đệ quy qua toàn bộ các trường (string, dict, list) và áp dụng regex từ [app/pii.py](file:///d:/Lab/K4-L3A-Day13-TranPhamThaiVu-2A202602695-Monitoring-LLMOps/app/pii.py) để thay thế email, số điện thoại VN, CCCD, thẻ thanh toán, passport bằng token `[REDACTED_<TYPE>]` trước khi dữ liệu kịp serialize.
- **Cách kiểm chứng kết quả:**
  Gửi request kiểm thử mang dữ liệu nhạy cảm (`email: test@student.edu.vn, phone: 0987654321, cccd: 012345678901, card: 1234-5678-9012-3456`), sau đó chạy `python scripts/validate_logs.py` đạt 100/100, xác nhận `Potential PII leaks detected: 0` và kiểm tra file log hiển thị token `[REDACTED_*]`.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:**
  Mọi traces được đẩy trực tiếp lên project Langfuse Cloud cá nhân mang tên `day13-k4-l3a-2A202602695` (hiển thị rõ ràng ở góc trên thanh breadcrumb trong các ảnh evidence `06-trace-list.png`, `07-trace-waterfall.png`, `09-prompt-versions.png`), được xác thực bằng cặp API keys riêng trong `.env`.
- **Cấu trúc root/retrieval/generation observations:**
  Sử dụng decorator `@observe(name="lab-agent-run", as_type="agent")` tạo root observation. Bên trong, dùng `langfuse_client.start_as_current_observation` để tách thành 2 child observations:
  1. `retrieval` (as_type: `retriever`): đo thời gian và ngữ cảnh truy xuất tài liệu vector store (`query_preview`, `doc_count`).
  2. `llm-generate` (as_type: `generation`): ghi nhận đối tượng prompt, model, thống kê `usage_details` (`input`, `output`, `total`), và `cost_details`.
- **Cách nối trace với log:**
  Metadata của trace được gắn trường `correlation_id` lấy từ `request.state.correlation_id` thông qua `propagate_attributes`. Khi cần đối chiếu, chỉ cần copy `correlation_id` từ dòng log trong `data/logs.jsonl` tìm kiếm trên thanh search của Langfuse sẽ ra chính xác trace tương ứng (ánh xạ 1-1).
- **Prompt name:** `day13-chat`
- **Version/label baseline:** Version 1 (`#1`), gắn label `baseline` và `production` ban đầu.
- **Version/label candidate:** Version 2 (`#2`), bổ sung câu chỉ dẫn `"Answer concisely in 1-2 sentences."`, gắn label `candidate`.
- **Trace ID của mỗi version:**
  - Trace dùng prompt Version 1 (`baseline`): `b838e17d34826383ff916f509aab4228`
  - Trace dùng prompt Version 2 (`candidate`): `0076de303bec921ead815f7932226189`
- **Cách promote và rollback `production`:**
  1. *Promote:* Trên giao diện Langfuse Prompts, gán nhãn `production` vào Version 2. Ứng dụng tự động tải v2 cho các request môi trường production.
  2. *Rollback:* Khi cần hoàn tác về bản cũ ổn định, chỉ cần gán lại nhãn `production` vào Version 1. Ứng dụng tự động chuyển về v1 mà không cần sửa code hay khởi động lại server.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:**
  Dashboard được dựng theo chuẩn contract [config/dashboard.yaml](file:///d:/Lab/K4-L3A-Day13-TranPhamThaiVu-2A202602695-Monitoring-LLMOps/config/dashboard.yaml) lấy nguồn chuẩn từ `data/logs.jsonl`:
  1. *Latency percentiles & TTFT (ms):* Thống kê P50, P95, P99 và TTFT P95.
  2. *Request traffic (requests/min):* Tổng request nhận và tốc độ xử lý trên phút.
  3. *Error rate & Retrieval success (%):* Tỷ lệ request lỗi và tỷ lệ truy xuất thành công.
  4. *Cost over time (USD):* Chi phí tích lũy toàn cửa sổ và chi phí trung bình/request.
  5. *Input and output tokens (tokens):* Thống kê prompt tokens và completion tokens.
  6. *Quality proxy (score 0-1):* Điểm chất lượng trung bình theo heuristic độ dài và ngữ cảnh.
- **SLO và lý do chọn:**
  Primary SLO: `fast_successful_requests` với Target **99.5%** trong chu kỳ 28 ngày (SLI: `event == "response_sent" and latency_ms <= 3000`). Lý do chọn: Trong điều kiện baseline bình thường, P95 của hệ thống đạt ~355ms; ngưỡng 3000ms là ranh giới tối đa trước khi người dùng cảm thấy độ trễ rõ rệt, gián đoạn trải nghiệm tương tác với trợ lý AI.
- **Cách tính error budget:**
  $$\text{Error Budget} = 100\% - 99.5\% = 0.5\%$$
  Nghĩa là trong mỗi 1,000 request nhận vào (`request_received`), hệ thống chỉ cho phép tối đa 5 request bị lỗi (HTTP 500) hoặc có độ trễ vượt quá 3000ms. Nếu tỷ lệ vi phạm vượt quá 0.5% trong cửa sổ 28 ngày, error budget cạn kiệt, toàn bộ các đợt phát hành prompt/tính năng mới sẽ bị phong tỏa để ưu tiên ổn định hạ tầng.
- **Ba alert và runbook tương ứng:**
  1. `high_latency_p95`: Severity warning, cảnh báo khi P95 > 3000ms kéo dài 5 phút (Runbook: [docs/alerts.md#alert-1](file:///d:/Lab/K4-L3A-Day13-TranPhamThaiVu-2A202602695-Monitoring-LLMOps/docs/alerts.md#alert-1)).
  2. `high_error_rate`: Severity critical, cảnh báo khi tỷ lệ lỗi > 2.0% kéo dài 3 phút (Runbook: [docs/alerts.md#alert-2](file:///d:/Lab/K4-L3A-Day13-TranPhamThaiVu-2A202602695-Monitoring-LLMOps/docs/alerts.md#alert-2)).
  3. `low_retrieval_success_rate`: Severity warning, cảnh báo khi tỷ lệ truy xuất thành công < 90% kéo dài 5 phút (Runbook: [docs/alerts.md#alert-3](file:///d:/Lab/K4-L3A-Day13-TranPhamThaiVu-2A202602695-Monitoring-LLMOps/docs/alerts.md#alert-3)).

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1`
- **Khoảng thời gian điều tra:** `16:19:40 - 16:20:00 (Asia/Ho_Chi_Minh)` tương ứng `09:19:40 - 09:20:00 UTC` ngày 29/09/2026.
- **Triệu chứng từ metrics:**
  Trên Dashboard runtime, Panel 1 Latency ghi nhận P95 tăng vọt từ ~355ms lên **2653.7 ms** (và P99 đạt **3226.02 ms**), vi phạm nghiêm trọng ngưỡng sự cố quy định của Challenge (2,000 ms), kích hoạt trạng thái cảnh báo đỏ `BREACHED` trên dashboard.
- **Log line và correlation ID liên quan:**
  Lọc file `data/logs.jsonl` trong khoảng thời gian trên phát hiện request bất thường:
  - `correlation_id`: `req-12f2e487`
  - `feature`: `monitoring`
  - `latency_ms`: `2652` (> 2000 ms)
  - `ts`: `2026-09-29T09:19:47.399498Z`
  - *Dòng log mẫu:*
    ```json
    {"service": "api", "latency_ms": 2652, "ttft_ms": 50, "tokens_in": 34, "tokens_out": 126, "cost_usd": 0.001992, "quality_score": 0.9, "tool_name": "retrieval", "tool_success": true, "payload": {"answer_preview": "Starter answer. You should improve this output logic and add better quality chec..."}, "event": "response_sent", "user_id_hash": "aae0b94055a9", "correlation_id": "req-12f2e487", "model": "claude-sonnet-4-5", "feature": "monitoring", "env": "dev", "session_id": "k4-l3a-challenge-s02", "level": "info", "ts": "2026-09-29T09:19:47.399498Z"}
    ```
- **Trace ID và span gây ảnh hưởng:**
  - *Trace ID trên Langfuse:* `fcdb7d7412ae74c659afb784b534f584`
  - *Phân tích Span Waterfall:*
    - Root span `lab-agent-run`: tổng thời gian xử lý **2.654 s**.
    - Child span `retrieval`: tiêu tốn **`2.501 s`** (chiếm tới **94.2%** tổng thời lượng request).
    - Child span `llm-generate`: chỉ tiêu tốn **`0.152 s`** (hoàn toàn bình thường).
- **Root cause:**
  Nghẽn cổ chai phát sinh trực tiếp tại tầng truy xuất tri thức / Vector store (`mock_rag.retrieve`), giả lập sự cố vector database bị chậm trễ kéo dài (2.5s) cho các câu hỏi thuộc chủ đề `monitoring`. Mô hình LLM không có lỗi và vẫn phản hồi trong 150ms.
- **Fix action:**
  Đã tắt sự cố bằng lệnh `python scripts/inject_incident.py --disable`. Trong thực tế: tối ưu hóa index vector (chuyển sang HNSW), kích hoạt Redis caching cho các câu hỏi thường gặp, tăng connection pool kết nối tới vector DB.
- **Preventive measure:**
  1. Cấu hình timeout tối đa 1.5s cho bước retrieval; nếu vượt quá thời gian, kích hoạt fallback sang tài liệu cục bộ hoặc keyword search để tránh làm nghẽn toàn bộ luồng request.
  2. Thiết lập alert rule `high_latency_p95` đẩy thông báo về kênh Slack On-call để đội ngũ kỹ thuật can thiệp ngay khi độ trễ retrieval bắt đầu tăng.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:**
  Quyết định xây dựng hàm đệ quy `_scrub_value` để duyệt và làm sạch PII trên toàn bộ cấu trúc event dictionary (bao gồm cả nested dict và list) thay vì chỉ che cứng trường `payload`. Lý do: Điều này đảm bảo an toàn PII tuyệt đối cho mọi metadata mở rộng trong tương lai hoặc các thông tin exception detail, ngăn chặn triệt để nguy cơ rò rỉ dữ liệu nhạy cảm ra file log và hệ thống phân tích.
- **Một lỗi/blocker đã gặp:**
  Gặp lỗi `Failed building wheel for pydantic-core` khi cài đặt môi trường ban đầu bằng Python 3.14 (do Python 3.14 là phiên bản quá mới, chưa có precompiled wheels trên Windows và thiếu trình biên dịch Rust/C++).
- **Cách tìm nguyên nhân và xử lý:**
  Sử dụng `py --list` để kiểm tra các phiên bản Python có sẵn trên máy, phát hiện máy đã cài sẵn Python 3.11.9. Đã tái tạo virtual environment bằng `py -3.11 -m venv .venv` và cài đặt lại thành công 100% thư viện bằng binary wheels chính thức.
- **Cách hiểu luồng Metrics → Logs → Traces:**
  1. **Metrics:** Là "chiếc còi báo động" (symptom detection) giúp nhận biết **hệ thống có vấn đề gì và xảy ra ở thời điểm nào** (ví dụ: Panel Latency báo P95 tăng vọt vi phạm ngưỡng lúc 16:19).
  2. **Logs:** Là "danh sách bằng chứng" (request localization) giúp lọc ra **chính xác request nào bị ảnh hưởng** thông qua mã định danh duy nhất `correlation_id`.
  3. **Traces:** Là "kính hiển vi chẩn đoán" (root cause analysis), giúp bóc tách từng span bên trong request đó để biết **bước cụ thể nào (retrieval hay LLM generation) là nguyên nhân gây nghẽn hoặc lỗi**.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:**
  - *Prompt version & Rollback:* Coi prompt như mã nguồn (Prompt as Code), cho phép kiểm thử an toàn giữa các phiên bản (`baseline`, `candidate`) và có thể rollback tức thì chỉ bằng một thao tác đổi nhãn trên Langfuse mà không cần redeploy code.
  - *Token & Cost:* Giám sát chặt chẽ chi phí và lượng token theo thời gian thực giúp phát hiện sớm các hiện tượng prompt injection, loop câu hỏi hoặc chi phí bùng phát bất thường.
  - *SLO:* Là cam kết chất lượng dịch vụ định lượng với người dùng, làm cơ sở quyết định khi nào được triển khai tính năng mới và khi nào cần dừng lại để dồn nguồn lực sửa lỗi hệ thống.
- **Điều quan trọng nhất đã học:**
  Kỹ năng xây dựng hệ thống quan sát toàn diện (Observability) cho các ứng dụng AI/LLM, kết hợp nhuần nhuyễn giữa Structured Logging, Correlation ID và Distributed Tracing để điều tra sự cố một cách khoa học, có bằng chứng xác thực.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:**
  Bài lab đang sử dụng FakeLLM và MockRAG. Khi đưa lên môi trường Production thực tế quy mô lớn, sẽ cần mở rộng thêm distributed tracing qua mạng cho các microservices và xây dựng pipeline tự động hóa CI/CD cho kiểm thử hồi quy prompt.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [x] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
