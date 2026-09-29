# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.


## Alert 1

- Tên: high_latency_p95
- Severity: warning
- Duration: 5m
- Kênh thông báo: Slack (#alerts-llmops)
- SLI/SLO liên quan: `fast_successful_requests` (SLI: `event == "response_sent" and latency_ms <= 3000`, Target 99.5%)
- Điều kiện và thời gian duy trì: `latency_p95 > 3000ms` kéo dài liên tục trên 5 phút.
- Ảnh hưởng tới người dùng: Người dùng cảm thấy hệ thống chậm trễ rõ rệt (phản hồi > 3s), có nguy cơ client timeout hoặc reload gây nghẽn thêm.
- Ba bước kiểm tra đầu tiên:
  1. Mở Dashboard kiểm tra panel Latency (P50, P95, P99) và TTFT để xác định phạm vi ảnh hưởng.
  2. Lọc `data/logs.jsonl` với điều kiện `latency_ms > 3000` và trích xuất một `correlation_id` tiêu biểu.
  3. Mở Langfuse tìm trace có `correlation_id` đó, xem waterfall để xác định span chậm (Retrieval hay Generation).
- Mitigation tạm thời:
  1. Nếu span retrieval chậm: kích hoạt fallback tài liệu cục bộ hoặc tăng timeout vector store.
  2. Nếu span generation chậm: tạm thời giảm max output tokens hoặc điều chỉnh prompt ngắn hơn.
  3. Tăng số lượng worker/replica API nếu độ trễ phát sinh do nghẽn hàng đợi request.
- Owner: llmops-oncall

## Alert 2

- Tên: high_error_rate
- Severity: critical
- Duration: 3m
- Kênh thông báo: Slack (#alerts-critical-oncall)
- SLI/SLO liên quan: Primary SLO `fast_successful_requests` và Guardrail `error_rate_pct_max: 2%`
- Điều kiện và thời gian duy trì: `error_rate_pct > 2.0%` kéo dài liên tục trên 3 phút.
- Ảnh hưởng tới người dùng: Người dùng gặp thông báo lỗi hệ thống (HTTP 500), không nhận được câu trả lời, làm tiêu hao nhanh error budget (0.5%).
- Ba bước kiểm tra đầu tiên:
  1. Mở Dashboard kiểm tra panel Errors để xem loại lỗi chủ yếu (`error_type`).
  2. Lọc file `data/logs.jsonl` với `event == "request_failed"` để lấy `correlation_id` và chi tiết exception.
  3. Tra cứu trace ID trên Langfuse để xem span ném ngoại lệ và stack trace tương ứng.
- Mitigation tạm thời:
  1. Bật cơ chế trả lời an toàn fallback nếu một service phụ thuộc bên ngoài bị sập.
  2. Cách ly tính năng (feature isolation) đang gây lỗi hàng loạt để bảo vệ hệ thống chung.
  3. Thực hiện rollback prompt hoặc mã nguồn về phiên bản ổn định trước đó.
- Owner: llmops-oncall

## Alert 3

- Tên: low_retrieval_success_rate
- Severity: warning
- Duration: 5m
- Kênh thông báo: Slack (#alerts-search-platform)
- SLI/SLO liên quan: Guardrail `retrieval_success_rate_pct_min: 90%`
- Điều kiện và thời gian duy trì: `tool_success_rate_pct < 90.0%` kéo dài liên tục trên 5 phút.
- Ảnh hưởng tới người dùng: Câu trả lời của chatbot bị mất ngữ cảnh chuyên môn, trả về nội dung chung chung hoặc thông báo lỗi truy vấn tài liệu.
- Ba bước kiểm tra đầu tiên:
  1. Mở Dashboard kiểm tra panel Errors & Retrieval Success để xem xu hướng giảm của tỷ lệ retrieval.
  2. Lọc file `data/logs.jsonl` tìm các log có `tool_name == "retrieval"` và `tool_success == false`.
  3. Mở Langfuse trace để kiểm tra query đầu vào nào khiến retrieval thất bại.
- Mitigation tạm thời:
  1. Chuyển sang tìm kiếm keyword fallback trong khi khắc phục vector store.
  2. Khởi động lại service vector index hoặc mở rộng connection pool.
  3. Kiểm tra xem có incident practice đang được kích hoạt hay không và tắt bằng lệnh disable.
- Owner: search-platform
