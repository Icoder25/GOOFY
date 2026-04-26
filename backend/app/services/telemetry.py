from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional
from uuid import uuid4

import structlog
from pydantic import BaseModel, Field, field_validator

from app.firebase import firestore_client

logger = structlog.get_logger()

RETENTION_DAYS = 30
_COLLECTION_NAME = "telemetry_events"


class TelemetryEventType(str, Enum):
    COMMAND = "command"
    ERROR = "error"


class TelemetryStage(str, Enum):
    TRANSCRIPT = "transcript"
    PARSE_LOCAL = "parse_local"
    PARSE_BACKEND = "parse_backend"
    EXECUTION = "execution"
    RUNTIME = "runtime"


class TelemetryStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    ERROR = "error"


class TelemetryEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    client_id: str
    command_id: str
    event_type: TelemetryEventType
    stage: TelemetryStage
    status: TelemetryStatus
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    intent: Optional[str] = None
    strategy: Optional[str] = None
    confidence: Optional[float] = None
    latency_ms: Optional[float] = None
    transcript_digest: Optional[str] = None
    transcript_length: Optional[int] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TelemetryEventCreate(BaseModel):
    client_id: str
    command_id: str
    event_type: TelemetryEventType
    stage: TelemetryStage
    status: TelemetryStatus
    intent: Optional[str] = None
    strategy: Optional[str] = None
    confidence: Optional[float] = None
    latency_ms: Optional[float] = None
    transcript_digest: Optional[str] = None
    transcript_length: Optional[int] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[datetime] = None

    @field_validator("latency_ms")
    @classmethod
    def validate_latency(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and value < 0:
            raise ValueError("latency_ms must be greater than or equal to zero")
        return value

    @field_validator("confidence")
    @classmethod
    def clamp_confidence(cls, value: Optional[float]) -> Optional[float]:
        if value is None:
            return None
        return max(0.0, min(1.0, value))

    @field_validator("transcript_length")
    @classmethod
    def validate_transcript_length(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value < 0:
            raise ValueError("transcript_length must be greater than or equal to zero")
        return value


class TelemetryMetrics(BaseModel):
    total_events: int
    total_commands: int
    success_rate: float
    average_latency_ms: Dict[str, float]
    window_start: datetime
    window_end: datetime
    retention_days: int = RETENTION_DAYS
    source: str


class TelemetryService:
    """Telemetry persistence with Firestore + in-memory fallback."""

    def __init__(self, retention_days: int = RETENTION_DAYS) -> None:
        self._retention_days = retention_days
        self._memory_events: Dict[str, List[TelemetryEvent]] = defaultdict(list)
        self._firestore = firestore_client

    def record_event(self, payload: TelemetryEventCreate) -> TelemetryEvent:
        event = TelemetryEvent(
            client_id=payload.client_id,
            command_id=payload.command_id,
            event_type=payload.event_type,
            stage=payload.stage,
            status=payload.status,
            intent=payload.intent,
            strategy=payload.strategy,
            confidence=payload.confidence,
            latency_ms=payload.latency_ms,
            transcript_digest=payload.transcript_digest,
            transcript_length=payload.transcript_length,
            error_message=payload.error_message,
            metadata=payload.metadata,
            created_at=payload.timestamp or datetime.now(timezone.utc),
        )

        if self._firestore:
            self._persist_to_firestore(event)
        else:
            self._memory_events[event.client_id].append(event)
            self._apply_retention(event.client_id)

        logger.debug("telemetry_event_recorded", telemetry=event.model_dump())
        return event

    def export_events(self, client_id: str) -> List[TelemetryEvent]:
        if self._firestore:
            return list(self._fetch_firestore_events(client_id))
        events = self._memory_events.get(client_id, [])
        return list(sorted(events, key=lambda item: item.created_at))

    def purge_events(self, client_id: str) -> int:
        if self._firestore:
            return self._purge_firestore_events(client_id)
        removed = len(self._memory_events.get(client_id, []))
        self._memory_events.pop(client_id, None)
        logger.info("telemetry_events_purged", client_id=client_id, count=removed)
        return removed

    def metrics(self) -> TelemetryMetrics:
        window_end = datetime.now(timezone.utc)
        window_start = window_end - timedelta(days=self._retention_days)
        events = list(self._iter_events(window_start))

        total_events = len(events)
        command_events = [event for event in events if event.event_type == TelemetryEventType.COMMAND]
        execution_events = [event for event in command_events if event.stage == TelemetryStage.EXECUTION]
        successes = [event for event in execution_events if event.status == TelemetryStatus.SUCCESS]

        success_rate = 0.0
        if execution_events:
            success_rate = round(len(successes) / len(execution_events), 4)

        latency_by_stage: Dict[str, List[float]] = defaultdict(list)
        for event in command_events:
            if event.latency_ms is not None:
                latency_by_stage[event.stage.value].append(event.latency_ms)

        averaged_latency: Dict[str, float] = {}
        for stage, values in latency_by_stage.items():
            averaged_latency[stage] = round(sum(values) / len(values), 2)

        source = "firestore" if self._firestore else "memory"

        return TelemetryMetrics(
            total_events=total_events,
            total_commands=len(command_events),
            success_rate=success_rate,
            average_latency_ms=averaged_latency,
            window_start=window_start,
            window_end=window_end,
            source=source,
        )

    def clear(self) -> None:
        """Remove all in-memory events (primarily for tests)."""
        self._memory_events.clear()

    # Internal helpers -------------------------------------------------

    def _apply_retention(self, client_id: str) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=self._retention_days)
        events = self._memory_events.get(client_id)
        if not events:
            return
        filtered = [event for event in events if event.created_at >= cutoff]
        self._memory_events[client_id] = filtered

    def _iter_events(self, cutoff: datetime) -> Iterable[TelemetryEvent]:
        if self._firestore:
            yield from self._iter_firestore_events(cutoff)
            return
        for events in self._memory_events.values():
            for event in events:
                if event.created_at >= cutoff:
                    yield event

    def _persist_to_firestore(self, event: TelemetryEvent) -> None:
        firestore = self._firestore
        if firestore is None:
            return

        try:
            collection = firestore.collection(_COLLECTION_NAME)
            collection.document(event.id).set(event.model_dump())
        except Exception as exc:  # pragma: no cover - exercised when Firestore configured
            logger.error("telemetry_firestore_write_failed", error=str(exc))

    def _fetch_firestore_events(self, client_id: str) -> Iterable[TelemetryEvent]:
        firestore = self._firestore
        if firestore is None:
            return []

        try:
            collection = firestore.collection(_COLLECTION_NAME)
            query = collection.where("client_id", "==", client_id)
            for doc in query.stream():
                data = doc.to_dict()
                if not data:
                    continue
                yield TelemetryEvent(**data)
        except Exception as exc:  # pragma: no cover
            logger.error("telemetry_firestore_read_failed", error=str(exc))
            return []

    def _iter_firestore_events(self, cutoff: datetime) -> Iterable[TelemetryEvent]:
        firestore = self._firestore
        if firestore is None:
            return []

        try:
            collection = firestore.collection(_COLLECTION_NAME)
            query = collection.where("created_at", ">=", cutoff)
            for doc in query.stream():
                data = doc.to_dict()
                if not data:
                    continue
                yield TelemetryEvent(**data)
        except Exception as exc:  # pragma: no cover
            logger.error("telemetry_firestore_iter_failed", error=str(exc))
            return []

    def _purge_firestore_events(self, client_id: str) -> int:
        firestore = self._firestore
        if firestore is None:
            return 0

        try:
            collection = firestore.collection(_COLLECTION_NAME)
            query = collection.where("client_id", "==", client_id)
            count = 0
            for doc in query.stream():
                doc.reference.delete()
                count += 1
            logger.info("telemetry_firestore_purged", client_id=client_id, count=count)
            return count
        except Exception as exc:  # pragma: no cover
            logger.error("telemetry_firestore_purge_failed", error=str(exc))
            return 0


telemetry_service = TelemetryService()