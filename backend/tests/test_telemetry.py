from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.services.telemetry import (
    TelemetryEventCreate,
    TelemetryEventType,
    TelemetryStage,
    TelemetryStatus,
    telemetry_service,
)

client = TestClient(app)


def setup_function() -> None:
    telemetry_service.clear()


def test_ingest_and_export_events() -> None:
    payload = {
        "client_id": "client_test",
        "command_id": "cmd_1",
        "event_type": TelemetryEventType.COMMAND.value,
        "stage": TelemetryStage.TRANSCRIPT.value,
        "status": TelemetryStatus.SUCCESS.value,
        "transcript_digest": "abc123",
        "transcript_length": 42,
    }

    response = client.post("/api/v1/telemetry/events", json=payload)
    assert response.status_code == 202
    body = response.json()
    assert body["command_id"] == "cmd_1"
    assert "stored_at" in body

    export_response = client.get("/api/v1/telemetry/export/client_test")
    assert export_response.status_code == 200
    exported = export_response.json()
    assert len(exported) == 1
    assert exported[0]["transcript_digest"] == "abc123"
    assert "transcript" not in exported[0]


def test_metrics_and_purge() -> None:
    now = datetime.now(timezone.utc)
    events = [
        TelemetryEventCreate(
            client_id="client_test",
            command_id="cmd_1",
            event_type=TelemetryEventType.COMMAND,
            stage=TelemetryStage.PARSE_LOCAL,
            status=TelemetryStatus.SUCCESS,
            latency_ms=12.5,
            timestamp=now - timedelta(minutes=1),
        ),
        TelemetryEventCreate(
            client_id="client_test",
            command_id="cmd_1",
            event_type=TelemetryEventType.COMMAND,
            stage=TelemetryStage.EXECUTION,
            status=TelemetryStatus.SUCCESS,
            latency_ms=78.0,
            timestamp=now,
        ),
        TelemetryEventCreate(
            client_id="client_test",
            command_id="cmd_2",
            event_type=TelemetryEventType.COMMAND,
            stage=TelemetryStage.EXECUTION,
            status=TelemetryStatus.ERROR,
            latency_ms=120.0,
            timestamp=now,
        ),
    ]

    for event in events:
        telemetry_service.record_event(event)

    metrics_response = client.get("/api/v1/telemetry/metrics")
    assert metrics_response.status_code == 200
    metrics = metrics_response.json()

    assert metrics["total_events"] == 3
    assert metrics["total_commands"] == 3
    assert metrics["success_rate"] == 0.5
    assert round(metrics["average_latency_ms"][TelemetryStage.PARSE_LOCAL.value], 1) == 12.5
    assert round(metrics["average_latency_ms"][TelemetryStage.EXECUTION.value], 1) == 99.0

    purge_response = client.delete("/api/v1/telemetry/purge/client_test")
    assert purge_response.status_code == 200
    purge_data = purge_response.json()
    assert purge_data["deleted"] == 3

    # Ensure data removed
    export_after = client.get("/api/v1/telemetry/export/client_test")
    assert export_after.status_code == 200
    assert export_after.json() == []
