from collections.abc import AsyncIterator, Callable, Mapping
from contextlib import asynccontextmanager
from typing import Any, TypeVar
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .masking import mask_sensitive_data
from .models import AuditLog, OutboxMessage, utc_now
from .types import AuditEntry, Operation, OutboxEvent, OutboxSource

T = TypeVar("T")
AuditMasker = Callable[[Mapping[str, Any]], dict[str, Any]]
AuditSource = AuditEntry | Callable[[], AuditEntry | None] | None


class TransactionManager:
    """Runs business writes, audit logging and outbox writes in one transaction."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        service_name: str,
        audit_topic: str | None = "audit-log",
        audit_masker: AuditMasker = mask_sensitive_data,
    ) -> None:
        self._session_factory = session_factory
        if not service_name.strip():
            raise ValueError("service_name must not be empty")
        self._service_name = service_name
        self._audit_topic = audit_topic
        self._audit_masker = audit_masker

    async def run(
        self,
        operation: Operation[T],
        *,
        audit: AuditEntry | None = None,
        outbox: OutboxSource[T] = None,
    ) -> T:
        async with self._session_factory() as session:
            async with session.begin():
                result = await operation(session)
                audit_model = self._build_audit(audit) if audit is not None else None
                if audit_model is not None:
                    session.add(audit_model)
                events = self._resolve_events(outbox, result)
                if audit_model is not None and self._audit_topic is not None:
                    events.append(self._audit_event(audit_model))
                session.add_all(self._build_outbox(event) for event in events)
                await session.flush()
                return result

    @asynccontextmanager
    async def transaction(self, *, audit: AuditSource = None) -> AsyncIterator[AsyncSession]:
        """Yield the manager-owned session and commit audit with business writes."""
        async with self._session_factory() as session:
            async with session.begin():
                yield session
                entry = audit() if callable(audit) else audit
                audit_model = self._build_audit(entry) if entry is not None else None
                if audit_model is not None:
                    session.add(audit_model)
                    if self._audit_topic is not None:
                        session.add(self._build_outbox(self._audit_event(audit_model)))
                await session.flush()

    async def emit(self, *events: OutboxEvent, audit: AuditEntry | None = None) -> None:
        async def no_operation(_: AsyncSession) -> None:
            return None

        await self.run(no_operation, audit=audit, outbox=events)

    def _build_audit(self, entry: AuditEntry) -> AuditLog:
        return AuditLog(
            id=uuid4(),
            service_name=self._service_name,
            action=entry.action,
            resource_type=entry.resource_type,
            resource_id=str(entry.resource_id) if entry.resource_id is not None else None,
            actor_id=str(entry.actor_id) if entry.actor_id is not None else None,
            input=self._mask(entry.input),
            changes=self._mask(entry.changes),
            context=self._mask(entry.context) or {},
            trace_id=entry.trace_id,
            created_at=utc_now(),
        )

    def _mask(self, value: Mapping[str, Any] | None) -> dict[str, Any] | None:
        return self._audit_masker(value) if value is not None else None

    @staticmethod
    def _resolve_events(source: OutboxSource[T], result: T) -> list[OutboxEvent]:
        resolved = source(result) if callable(source) else source
        if resolved is None:
            return []
        if isinstance(resolved, OutboxEvent):
            return [resolved]
        return list(resolved)

    @staticmethod
    def _build_outbox(event: OutboxEvent) -> OutboxMessage:
        return OutboxMessage(
            topic=event.topic,
            event_type=event.event_type,
            aggregate_type=event.aggregate_type,
            aggregate_id=str(event.aggregate_id) if event.aggregate_id is not None else None,
            payload=dict(event.payload),
            headers=dict(event.headers),
        )

    def _audit_event(self, audit: AuditLog) -> OutboxEvent:
        return OutboxEvent(
            topic=self._audit_topic or "audit-log",
            event_type="audit_log.created",
            aggregate_type=audit.resource_type,
            aggregate_id=audit.resource_id,
            payload={
                "id": str(audit.id),
                "schema_version": 1,
                "service_name": audit.service_name,
                "action": audit.action,
                "resource_type": audit.resource_type,
                "resource_id": audit.resource_id,
                "actor_id": audit.actor_id,
                "input": audit.input,
                "changes": audit.changes,
                "context": audit.context,
                "trace_id": audit.trace_id,
                "created_at": audit.created_at.isoformat(),
            },
        )
