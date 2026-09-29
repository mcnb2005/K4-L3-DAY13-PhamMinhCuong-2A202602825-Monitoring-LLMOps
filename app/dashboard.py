from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
from statistics import mean
from typing import Any

import yaml

from . import logging_config


CONFIG_PATH = Path("config/dashboard.yaml")


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _percentile(values: list[float], percentile: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(0, math.ceil((percentile / 100) * len(ordered)) - 1)
    return float(ordered[rank])


def _number(record: dict[str, Any], field: str) -> float:
    value = record.get(field, 0)
    return float(value) if isinstance(value, (int, float)) else 0.0


def _load_config(config_path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, yaml.YAMLError):
        return {"time_range_minutes": 60, "refresh_seconds": 30, "panels": []}
    dashboard = payload.get("dashboard", {}) if isinstance(payload, dict) else {}
    return dashboard if isinstance(dashboard, dict) else {}


def _load_records(log_path: Path, window_minutes: int) -> list[dict[str, Any]]:
    if not log_path.exists():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    records: list[dict[str, Any]] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue
        timestamp = _parse_timestamp(record.get("ts"))
        if timestamp is None or timestamp >= cutoff:
            records.append(record)
    return records


def build_dashboard_snapshot(
    log_path: Path | None = None, config_path: Path = CONFIG_PATH
) -> dict[str, Any]:
    config = _load_config(config_path)
    window_minutes = int(config.get("time_range_minutes", 60))
    records = _load_records(log_path or logging_config.LOG_PATH, window_minutes)

    requests = [item for item in records if item.get("event") == "request_received"]
    responses = [item for item in records if item.get("event") == "response_sent"]
    failures = [item for item in records if item.get("event") == "request_failed"]

    latencies = [_number(item, "latency_ms") for item in responses]
    ttfts = [_number(item, "ttft_ms") for item in responses]
    qualities = [_number(item, "quality_score") for item in responses]
    tool_results = [
        item for item in records if isinstance(item.get("tool_success"), bool)
    ]

    timestamps = [
        parsed
        for parsed in (_parse_timestamp(item.get("ts")) for item in requests)
        if parsed is not None
    ]
    active_minutes = 1
    if len(timestamps) > 1:
        active_minutes = max(
            1, math.ceil((max(timestamps) - min(timestamps)).total_seconds() / 60)
        )

    request_count = len(requests)
    error_rate = (len(failures) / request_count * 100) if request_count else 0.0
    retrieval_success = (
        sum(1 for item in tool_results if item["tool_success"])
        / len(tool_results)
        * 100
        if tool_results
        else 0.0
    )

    return {
        "title": config.get("title", "Monitoring & LLMOps Dashboard"),
        "window_minutes": window_minutes,
        "refresh_seconds": int(config.get("refresh_seconds", 30)),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "record_count": len(records),
        "panels": {
            "latency": {
                "p50_ms": round(_percentile(latencies, 50), 2),
                "p95_ms": round(_percentile(latencies, 95), 2),
                "p99_ms": round(_percentile(latencies, 99), 2),
                "ttft_p95_ms": round(_percentile(ttfts, 95), 2),
                "threshold_ms": 2000,
            },
            "traffic": {
                "requests": request_count,
                "requests_per_minute": round(request_count / active_minutes, 2),
                "active_minutes": active_minutes,
            },
            "errors": {
                "failed_requests": len(failures),
                "error_rate_pct": round(error_rate, 2),
                "retrieval_success_pct": round(retrieval_success, 2),
                "error_types": _count_values(failures, "error_type"),
            },
            "cost": {
                "total_usd": round(sum(_number(item, "cost_usd") for item in responses), 6),
                "average_usd": round(
                    mean(_number(item, "cost_usd") for item in responses), 6
                )
                if responses
                else 0.0,
            },
            "tokens": {
                "input_total": int(sum(_number(item, "tokens_in") for item in responses)),
                "output_total": int(sum(_number(item, "tokens_out") for item in responses)),
            },
            "quality": {
                "average": round(mean(qualities), 3) if qualities else 0.0,
                "samples": len(qualities),
            },
        },
    }


def _count_values(records: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        value = str(record.get(field) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return counts


def _status(value: float, threshold: float, operator: str = "lte") -> str:
    healthy = value <= threshold if operator == "lte" else value >= threshold
    return "healthy" if healthy else "breach"


def render_dashboard(snapshot: dict[str, Any]) -> str:
    panels = snapshot["panels"]
    latency = panels["latency"]
    traffic = panels["traffic"]
    errors = panels["errors"]
    cost = panels["cost"]
    tokens = panels["tokens"]
    quality = panels["quality"]
    refresh = int(snapshot["refresh_seconds"])

    cards = [
        (
            "Latency percentiles & TTFT",
            f"{latency['p95_ms']:.0f} ms",
            f"P50 {latency['p50_ms']:.0f} · P95 {latency['p95_ms']:.0f} · "
            f"P99 {latency['p99_ms']:.0f} · TTFT P95 {latency['ttft_p95_ms']:.0f} ms",
            _status(latency["p95_ms"], latency["threshold_ms"]),
            f"SLO ≤ {latency['threshold_ms']} ms",
        ),
        (
            "Request traffic",
            f"{traffic['requests_per_minute']:.2f} rpm",
            f"{traffic['requests']} requests across {traffic['active_minutes']} active minute(s)",
            "healthy" if traffic["requests"] else "neutral",
            "Threshold ≥ 1 rpm",
        ),
        (
            "Errors & retrieval",
            f"{errors['error_rate_pct']:.2f}%",
            f"{errors['failed_requests']} failures · retrieval success "
            f"{errors['retrieval_success_pct']:.2f}%",
            _status(errors["error_rate_pct"], 2),
            "Error SLO ≤ 2% · Retrieval ≥ 90%",
        ),
        (
            "Cost over time",
            f"${cost['total_usd']:.6f}",
            f"Average ${cost['average_usd']:.6f} per successful response",
            _status(cost["total_usd"], 2.5),
            "Daily guardrail ≤ $2.50",
        ),
        (
            "Input & output tokens",
            f"{tokens['input_total'] + tokens['output_total']:,}",
            f"Input {tokens['input_total']:,} · Output {tokens['output_total']:,}",
            _status(tokens["input_total"] + tokens["output_total"], 50_000),
            "Window guardrail ≤ 50,000 tokens",
        ),
        (
            "Quality proxy",
            f"{quality['average']:.3f}",
            f"Mean heuristic score across {quality['samples']} response(s)",
            _status(quality["average"], 0.75, "gte") if quality["samples"] else "neutral",
            "Quality SLO ≥ 0.75",
        ),
    ]

    card_html = "".join(
        f"""
        <article class="card {css_class}">
          <div class="card-head"><h2>{escape(title)}</h2><span class="dot"></span></div>
          <div class="value">{escape(value)}</div>
          <p>{escape(detail)}</p>
          <div class="threshold">{escape(threshold)}</div>
        </article>
        """
        for title, value, detail, css_class, threshold in cards
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="{refresh}">
  <title>{escape(str(snapshot['title']))}</title>
  <style>
    :root {{ color-scheme: dark; --bg:#07111f; --card:#101e31; --line:#223653;
      --text:#f1f5fb; --muted:#91a5c2; --cyan:#54d7e6; --green:#5ae0a0;
      --red:#ff6b79; --amber:#f8c55c; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; min-height:100vh; font-family:Inter,Segoe UI,sans-serif;
      background:radial-gradient(circle at 15% 0%,#123353 0,transparent 32%),var(--bg);
      color:var(--text); }}
    main {{ width:min(1180px,calc(100% - 40px)); margin:0 auto; padding:44px 0 56px; }}
    header {{ display:flex; justify-content:space-between; gap:24px; align-items:flex-end;
      margin-bottom:28px; }}
    .eyebrow {{ color:var(--cyan); letter-spacing:.14em; text-transform:uppercase;
      font-size:12px; font-weight:700; }}
    h1 {{ margin:7px 0 0; font-size:clamp(28px,4vw,46px); letter-spacing:-.04em; }}
    .meta {{ color:var(--muted); text-align:right; line-height:1.6; font-size:13px; }}
    .grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:16px; }}
    .card {{ min-height:215px; padding:22px; border:1px solid var(--line); border-radius:18px;
      background:linear-gradient(145deg,rgba(19,37,60,.96),rgba(10,23,39,.96));
      box-shadow:0 16px 40px rgba(0,0,0,.2); }}
    .card-head {{ display:flex; align-items:center; justify-content:space-between; gap:12px; }}
    h2 {{ font-size:14px; margin:0; color:#c8d5e8; font-weight:650; }}
    .dot {{ width:9px; height:9px; border-radius:50%; background:var(--amber);
      box-shadow:0 0 14px currentColor; }}
    .healthy .dot {{ background:var(--green); }} .breach .dot {{ background:var(--red); }}
    .value {{ font-size:40px; font-weight:750; letter-spacing:-.04em; margin:28px 0 12px; }}
    p {{ color:var(--muted); font-size:13px; line-height:1.55; min-height:40px; margin:0; }}
    .threshold {{ border-top:1px solid var(--line); margin-top:16px; padding-top:13px;
      color:#aebed4; font-size:12px; }}
    footer {{ display:flex; justify-content:space-between; margin-top:22px; color:var(--muted);
      font-size:12px; }}
    @media (max-width:900px) {{ .grid {{ grid-template-columns:repeat(2,1fr); }} }}
    @media (max-width:620px) {{ main {{ width:min(100% - 24px,1180px); padding-top:26px; }}
      header {{ align-items:flex-start; flex-direction:column; }} .meta {{ text-align:left; }}
      .grid {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
  <main>
    <header>
      <div><div class="eyebrow">Operational overview</div><h1>{escape(str(snapshot['title']))}</h1></div>
      <div class="meta">Last {snapshot['window_minutes']} minutes<br>{snapshot['record_count']} log records</div>
    </header>
    <section class="grid">{card_html}</section>
    <footer><span>Source: data/logs.jsonl</span><span>Auto-refresh: {refresh}s · {escape(str(snapshot['generated_at']))}</span></footer>
  </main>
</body>
</html>"""
