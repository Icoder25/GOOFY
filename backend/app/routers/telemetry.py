from fastapi import APIRouter

from app.services.telemetry import TelemetryEventCreate, telemetry_service

router = APIRouter()


@router.post("/telemetry/events", status_code=202)
async def ingest_event(payload: TelemetryEventCreate):
    """Ingest a telemetry event from the extension."""
    event = telemetry_service.record_event(payload)
    return {
        "id": event.id,
        "command_id": event.command_id,
        "stored_at": event.created_at,
    }


@router.get("/telemetry/export/{client_id}")
async def export_events(client_id: str):
    """Export telemetry events for a client (data subject access)."""
    events = telemetry_service.export_events(client_id)
    return [event.model_dump() for event in events]


@router.delete("/telemetry/purge/{client_id}")
async def purge_events(client_id: str):
    """Delete telemetry data for a client (right to be forgotten)."""
    deleted = telemetry_service.purge_events(client_id)
    return {"client_id": client_id, "deleted": deleted}


@router.get("/telemetry/metrics")
async def telemetry_metrics():
    """Return aggregate metrics for dashboards."""
    metrics = telemetry_service.metrics()
    return metrics.model_dump()
