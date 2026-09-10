from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, Index, Integer, String, Text, Uuid, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(UTC)


class TransactionManagerBase(DeclarativeBase):
    """Separate metadata keeps common infrastructure independent from the app package."""


class OutboxMessage(TransactionManagerBase):
    __tablename__ = "outbox"
    __table_args__ = (
        Index("ix_outbox_pending", "published_at", "occurred_at"),
        Index("ix_outbox_topic_occurred_at", "topic", "occurred_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    topic: Mapped[str] = mapped_column(String(255))
    event_type: Mapped[str] = mapped_column(String(255))
    aggregate_type: Mapped[str | None] = mapped_column(String(255))
    aggregate_id: Mapped[str | None] = mapped_column(String(255))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    headers: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    last_error: Mapped[str | None] = mapped_column(Text)


class AuditLog(TransactionManagerBase):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_resource", "resource_type", "resource_id"),
        Index("ix_audit_log_service_created_at", "service_name", "created_at"),
        Index("ix_audit_log_actor_created_at", "actor_id", "created_at"),
        Index("ix_audit_log_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    service_name: Mapped[str] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(255))
    resource_type: Mapped[str] = mapped_column(String(255))
    resource_id: Mapped[str | None] = mapped_column(String(255))
    actor_id: Mapped[str | None] = mapped_column(String(255))
    input: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    changes: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    trace_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
