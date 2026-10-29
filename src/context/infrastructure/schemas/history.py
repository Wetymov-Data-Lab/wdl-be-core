from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from context.infrastructure.schemas.mixins import utc_now
from infrastructure.database.base import Base


class DiagramHistoryEntries(Base):
    """One undoable diagram change of a user: row states before and after it."""

    __tablename__ = "diagram_history"
    __table_args__ = (
        Index("ix_diagram_history_database_actor", "database_id", "actor_id", "created_at"),
    )

    id:          Mapped[UUID]                 = mapped_column(Uuid, primary_key=True)
    database_id: Mapped[UUID]                 = mapped_column(
        Uuid,
        ForeignKey("databases.id", ondelete="CASCADE"),
        nullable=False,
    )
    actor_id:    Mapped[UUID]                 = mapped_column(Uuid, nullable=False)
    action:      Mapped[str]                  = mapped_column(String(64), nullable=False)
    changes:     Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    is_undone:   Mapped[bool]                 = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    created_at:  Mapped[datetime]             = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
