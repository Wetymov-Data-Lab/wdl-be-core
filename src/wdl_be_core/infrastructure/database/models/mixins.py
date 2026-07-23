from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import DateTime, Float, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from wdl_shared.schemas.engine.models.canvas import CanvasPosition


def utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp."""

    return datetime.now(UTC)


class AuditMixin:
    """Common audit fields for user-created entities."""

    created_at: Mapped[datetime]        = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=utc_now,
    )
    author_id:  Mapped[UUID]            = mapped_column(Uuid, nullable=False)


class CanvasPositionMixin:
    """Persist a shared canvas position as scalar database columns."""

    position_x: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    position_y: Mapped[float] = mapped_column(Float, nullable=False, default=0)

    @property
    def position(self) -> CanvasPosition:
        return CanvasPosition(x=self.position_x, y=self.position_y)

    @position.setter
    def position(self, value: CanvasPosition) -> None:
        self.position_x = value.x
        self.position_y = value.y
