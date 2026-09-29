from __future__ import annotations

import asyncio
import json
import re
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import httpx

from app import agent as agent_module
from app import logging_config
from app.dashboard import build_dashboard_snapshot
from app.main import app
from app.pii import scrub_text


def _post_chat(headers: dict[str, str] | None = None) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/chat",
                headers=headers,
                json={
                    "user_id": "student@example.com",
                    "session_id": "session-01",
                    "feature": "qa",
                    "message": "Call 090 123 4567 about monitoring",
                },
            )

    return asyncio.run(send())


def test_request_id_headers_context_and_pii_scrubbing(monkeypatch, tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    response = _post_chat({"x-request-id": "client-request-01"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "client-request-01"
    assert float(response.headers["x-response-time-ms"]) > 0
    records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    api_records = [record for record in records if record.get("service") == "api"]
    assert api_records
    assert all(record["correlation_id"] == "client-request-01" for record in api_records)
    assert all(record["feature"] == "qa" for record in api_records)
    assert all(record["env"] == "dev" for record in api_records)
    assert all("student@example.com" not in json.dumps(record) for record in records)
    assert all("090 123 4567" not in json.dumps(record) for record in records)


def test_invalid_request_id_is_replaced(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(logging_config, "LOG_PATH", tmp_path / "logs.jsonl")

    response = _post_chat({"x-request-id": "unsafe id with spaces"})

    assert re.fullmatch(r"req-[0-9a-f]{8}", response.headers["x-request-id"])


def test_additional_passport_pattern_is_scrubbed() -> None:
    assert scrub_text("Passport B1234567") == "Passport [REDACTED_PASSPORT]"


def test_dashboard_aggregates_six_panels(tmp_path: Path) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    records = [
        {
            "ts": timestamp,
            "event": "request_received",
            "correlation_id": "req-00000001",
        },
        {
            "ts": timestamp,
            "event": "response_sent",
            "correlation_id": "req-00000001",
            "latency_ms": 350,
            "ttft_ms": 50,
            "cost_usd": 0.001,
            "tokens_in": 20,
            "tokens_out": 80,
            "quality_score": 0.9,
            "tool_success": True,
        },
    ]
    log_path = tmp_path / "logs.jsonl"
    log_path.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8"
    )

    snapshot = build_dashboard_snapshot(log_path=log_path)

    assert set(snapshot["panels"]) == {
        "latency",
        "traffic",
        "errors",
        "cost",
        "tokens",
        "quality",
    }
    assert snapshot["panels"]["latency"]["p95_ms"] == 350
    assert snapshot["panels"]["errors"]["retrieval_success_pct"] == 100


class _Observation:
    def __init__(self, arguments: dict) -> None:
        self.arguments = arguments
        self.updates: list[dict] = []

    def update(self, **kwargs):
        self.updates.append(kwargs)
        return self


class _TraceClient:
    def __init__(self) -> None:
        self.observations: list[_Observation] = []
        self.span_updates: list[dict] = []

    @contextmanager
    def start_as_current_observation(self, **kwargs):
        observation = _Observation(kwargs)
        self.observations.append(observation)
        yield observation

    def update_current_span(self, **kwargs) -> None:
        self.span_updates.append(kwargs)


def test_agent_creates_retrieval_and_generation_children(monkeypatch) -> None:
    client = _TraceClient()
    monkeypatch.setattr(agent_module, "get_langfuse_client", lambda: client)
    monkeypatch.setattr(agent_module, "tracing_enabled", lambda: False)

    @contextmanager
    def attributes(**kwargs):
        yield

    monkeypatch.setattr(agent_module, "propagate_attributes", attributes)
    agent = agent_module.LabAgent()

    agent_module.LabAgent.run.__wrapped__(
        agent,
        user_id="student-01",
        feature="qa",
        session_id="session-01",
        message="Explain monitoring",
        correlation_id="req-12345678",
    )

    assert [item.arguments["as_type"] for item in client.observations] == [
        "retriever",
        "generation",
    ]
    generation_update = client.observations[1].updates[-1]
    assert generation_update["usage_details"]["input"] > 0
    assert generation_update["usage_details"]["output"] > 0
    assert generation_update["cost_details"]["total"] > 0
    assert generation_update["metadata"]["correlation_id"] == "req-12345678"
