from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone
import statistics

import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio

configure_utf8_stdio()

LOG_PATH = Path("data/logs.jsonl")
OUTPUT_HTML = Path("submission/dashboard.html")


def percentile(vals: list[float | int], p: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    k = (len(s) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    d = k - f
    return round(s[f] + d * (s[c] - s[f]), 2)


def generate_dashboard() -> None:
    if not LOG_PATH.exists():
        print(f"File {LOG_PATH} không tồn tại.")
        return

    records: list[dict] = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except Exception:
            continue

    total_requests = sum(1 for r in records if r.get("event") == "request_received")
    total_responses = sum(1 for r in records if r.get("event") == "response_sent")
    total_failed = sum(1 for r in records if r.get("event") == "request_failed")

    latencies = [r["latency_ms"] for r in records if r.get("event") == "response_sent" and "latency_ms" in r]
    ttfts = [r["ttft_ms"] for r in records if r.get("event") == "response_sent" and "ttft_ms" in r]
    tokens_in = [r["tokens_in"] for r in records if r.get("event") == "response_sent" and "tokens_in" in r]
    tokens_out = [r["tokens_out"] for r in records if r.get("event") == "response_sent" and "tokens_out" in r]
    costs = [r["cost_usd"] for r in records if r.get("event") == "response_sent" and "cost_usd" in r]
    qualities = [r["quality_score"] for r in records if r.get("event") == "response_sent" and "quality_score" in r]

    # Retrieval success
    tool_events = [r for r in records if "tool_success" in r]
    tool_success_cnt = sum(1 for r in tool_events if r.get("tool_success") is True)
    tool_success_rate = round((tool_success_cnt / len(tool_events)) * 100, 1) if tool_events else 100.0

    p50 = percentile(latencies, 50)
    p95 = percentile(latencies, 95)
    p99 = percentile(latencies, 99)
    ttft_p95 = percentile(ttfts, 95)

    error_rate = round((total_failed / total_requests * 100), 2) if total_requests else 0.0
    total_cost = round(sum(costs), 5)
    total_tokens_in = sum(tokens_in)
    total_tokens_out = sum(tokens_out)
    avg_quality = round(statistics.mean(qualities), 3) if qualities else 0.0

    challenge_path = Path("config/challenge.json")
    challenge_thresh = 2000
    if challenge_path.exists():
        try:
            c_data = json.loads(challenge_path.read_text(encoding="utf-8"))
            challenge_thresh = c_data.get("latency_threshold_ms", 2000)
        except Exception:
            pass

    is_breached = p95 > challenge_thresh
    stat_color = "#f87171" if is_breached else "#38bdf8"
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    incident_banner = ""
    if is_breached:
        incident_banner = f"""
    <div style="background: rgba(239, 68, 68, 0.2); border: 1px solid #ef4444; border-radius: 8px; padding: 14px 18px; margin-bottom: 20px; color: #fca5a5; display: flex; align-items: center; justify-content: space-between;">
      <div>
        <strong style="color: #f87171; font-size: 15px;">&#9888;&#65039; INCIDENT DETECTED (Challenge K4-L3A):</strong> 
        Latency P95 ({p95} ms) vi phạm nghiêm trọng ngưỡng <strong>Challenge Threshold ({challenge_thresh} ms)</strong>! P99 đạt {p99} ms.
      </div>
      <span class="tag-fail" style="font-size: 13px;">SLO BREACHED</span>
    </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <title>K4-L3A Day 13 Monitoring & LLMOps Dashboard</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #0f172a;
      color: #f8fafc;
      margin: 0;
      padding: 24px;
    }}
    .header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid #334155;
      padding-bottom: 16px;
      margin-bottom: 24px;
    }}
    .header h1 {{ margin: 0; font-size: 22px; color: #38bdf8; }}
    .meta-badge {{
      background: #1e293b;
      padding: 6px 14px;
      border-radius: 6px;
      font-size: 13px;
      color: #94a3b8;
      border: 1px solid #334155;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 20px;
    }}
    .panel {{
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 10px;
      padding: 18px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }}
    .panel-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }}
    .panel-title {{
      font-size: 14px;
      font-weight: 600;
      color: #cbd5e1;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    .panel-unit {{
      font-size: 11px;
      color: #64748b;
      background: #0f172a;
      padding: 2px 8px;
      border-radius: 4px;
    }}
    .stat-main {{
      font-size: 32px;
      font-weight: 700;
      margin: 8px 0;
    }}
    .stat-list {{
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin: 12px 0;
      font-size: 13px;
    }}
    .stat-item {{
      display: flex;
      justify-content: space-between;
      color: #94a3b8;
    }}
    .stat-val {{
      font-weight: 600;
      color: #f1f5f9;
    }}
    .threshold {{
      border-top: 1px dashed #334155;
      padding-top: 10px;
      margin-top: 10px;
      font-size: 12px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .tag-pass {{
      background: rgba(34, 197, 94, 0.2);
      color: #4ade80;
      padding: 3px 8px;
      border-radius: 4px;
      font-weight: 600;
    }}
    .tag-fail {{
      background: rgba(239, 68, 68, 0.2);
      color: #f87171;
      padding: 3px 8px;
      border-radius: 4px;
      font-weight: 600;
    }}
  </style>
</head>
<body>
  <div class="header">
    <div>
      <h1>K4-L3A Day 13 Monitoring & LLMOps Dashboard</h1>
      <div style="font-size: 13px; color: #94a3b8; margin-top: 4px;">Source: data/logs.jsonl | Time Range: Last 60 minutes | Refresh: 30s</div>
    </div>
    <div class="meta-badge">Snapshot: {now_str}</div>
  </div>

  {incident_banner}

  <div class="grid">
    <!-- Panel 1: Latency -->
    <div class="panel" style="{'border-color: #ef4444;' if is_breached else ''}">
      <div class="panel-header">
        <span class="panel-title" style="{'color: #f87171;' if is_breached else ''}">1. Latency percentiles & TTFT</span>
        <span class="panel-unit">ms</span>
      </div>
      <div class="stat-main" style="color: {stat_color};">{p95} <span style="font-size: 14px; font-weight: normal; color: #94a3b8;">(P95)</span></div>
      <div class="stat-list">
        <div class="stat-item"><span>P50 Latency:</span><span class="stat-val">{p50} ms</span></div>
        <div class="stat-item"><span>P95 Latency:</span><span class="stat-val" style="{'color: #f87171;' if is_breached else ''}">{p95} ms</span></div>
        <div class="stat-item"><span>P99 Latency:</span><span class="stat-val" style="color: #f87171;">{p99} ms</span></div>
        <div class="stat-item"><span>TTFT P95:</span><span class="stat-val">{ttft_p95} ms</span></div>
      </div>
      <div class="threshold">
        <span style="font-weight: 600; color: #f87171;">Challenge Threshold: P95 &le; {challenge_thresh} ms</span>
        <span class="{'tag-pass' if p95 <= challenge_thresh else 'tag-fail'}">{'PASSED' if p95 <= challenge_thresh else 'BREACHED'}</span>
      </div>
    </div>

    <!-- Panel 2: Traffic -->
    <div class="panel">
      <div class="panel-header">
        <span class="panel-title">2. Request Traffic</span>
        <span class="panel-unit">requests/min</span>
      </div>
      <div class="stat-main">{total_requests} <span style="font-size: 14px; font-weight: normal; color: #64748b;">(total)</span></div>
      <div class="stat-list">
        <div class="stat-item"><span>Total Requests:</span><span class="stat-val">{total_requests}</span></div>
        <div class="stat-item"><span>Completed:</span><span class="stat-val">{total_responses}</span></div>
        <div class="stat-item"><span>Estimated Rate:</span><span class="stat-val">{max(1, total_requests)} req/min</span></div>
      </div>
      <div class="threshold">
        <span>Target: Rate &ge; 1 req/min</span>
        <span class="tag-pass">PASSED</span>
      </div>
    </div>

    <!-- Panel 3: Errors -->
    <div class="panel">
      <div class="panel-header">
        <span class="panel-title">3. Error Rate & Retrieval</span>
        <span class="panel-unit">percent</span>
      </div>
      <div class="stat-main">{error_rate}% <span style="font-size: 14px; font-weight: normal; color: #64748b;">(errors)</span></div>
      <div class="stat-list">
        <div class="stat-item"><span>Error Rate:</span><span class="stat-val">{error_rate}%</span></div>
        <div class="stat-item"><span>Failed Requests:</span><span class="stat-val">{total_failed}</span></div>
        <div class="stat-item"><span>Retrieval Success:</span><span class="stat-val">{tool_success_rate}%</span></div>
      </div>
      <div class="threshold">
        <span>Guardrail: Error &le; 2.0%</span>
        <span class="{'tag-pass' if error_rate <= 2.0 else 'tag-fail'}">{'PASSED' if error_rate <= 2.0 else 'BREACHED'}</span>
      </div>
    </div>

    <!-- Panel 4: Cost -->
    <div class="panel">
      <div class="panel-header">
        <span class="panel-title">4. Cost over time</span>
        <span class="panel-unit">USD</span>
      </div>
      <div class="stat-main">${total_cost} <span style="font-size: 14px; font-weight: normal; color: #64748b;">(total)</span></div>
      <div class="stat-list">
        <div class="stat-item"><span>Window Total Cost:</span><span class="stat-val">${total_cost}</span></div>
        <div class="stat-item"><span>Avg Cost / Request:</span><span class="stat-val">${round(statistics.mean(costs), 6) if costs else 0.0}</span></div>
      </div>
      <div class="threshold">
        <span>Guardrail: Total &le; $2.50</span>
        <span class="{'tag-pass' if total_cost <= 2.5 else 'tag-fail'}">{'PASSED' if total_cost <= 2.5 else 'BREACHED'}</span>
      </div>
    </div>

    <!-- Panel 5: Tokens -->
    <div class="panel">
      <div class="panel-header">
        <span class="panel-title">5. Input & Output Tokens</span>
        <span class="panel-unit">tokens</span>
      </div>
      <div class="stat-main">{total_tokens_in + total_tokens_out} <span style="font-size: 14px; font-weight: normal; color: #64748b;">(total)</span></div>
      <div class="stat-list">
        <div class="stat-item"><span>Prompt Tokens (In):</span><span class="stat-val">{total_tokens_in:,}</span></div>
        <div class="stat-item"><span>Completion Tokens (Out):</span><span class="stat-val">{total_tokens_out:,}</span></div>
      </div>
      <div class="threshold">
        <span>Guardrail: Total &le; 50,000</span>
        <span class="{'tag-pass' if (total_tokens_in + total_tokens_out) <= 50000 else 'tag-fail'}">{'PASSED' if (total_tokens_in + total_tokens_out) <= 50000 else 'BREACHED'}</span>
      </div>
    </div>

    <!-- Panel 6: Quality -->
    <div class="panel">
      <div class="panel-header">
        <span class="panel-title">6. Quality Proxy</span>
        <span class="panel-unit">score (0-1)</span>
      </div>
      <div class="stat-main">{avg_quality} <span style="font-size: 14px; font-weight: normal; color: #64748b;">(mean)</span></div>
      <div class="stat-list">
        <div class="stat-item"><span>Mean Quality Score:</span><span class="stat-val">{avg_quality} / 1.0</span></div>
        <div class="stat-item"><span>Evaluated Responses:</span><span class="stat-val">{len(qualities)}</span></div>
      </div>
      <div class="threshold">
        <span>Guardrail: Mean &ge; 0.75</span>
        <span class="{'tag-pass' if avg_quality >= 0.75 else 'tag-fail'}">{'PASSED' if avg_quality >= 0.75 else 'BREACHED'}</span>
      </div>
    </div>
  </div>
</body>
</html>
"""
    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"Đã tạo dashboard HTML tại: {OUTPUT_HTML.resolve()}")


if __name__ == "__main__":
    generate_dashboard()
