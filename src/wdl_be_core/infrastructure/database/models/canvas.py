from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column
from wdl_shared.schemas.engine.models.canvas import CanvasViewport

from wdl_be_core.infrastructure.database.base import Base
from wdl_be_core.infrastructure.database.models.mixins import AuditMixin, CanvasPositionMixin


class CanvasStates(Base):
    """Default or per-user viewport preferences."""

    __tablename__ = "canvas_states"
    __table_args__ = (
        UniqueConstraint("database_id", "user_id", name="uq_canvas_states_database_user"),
        CheckConstraint("zoom > 0 AND zoom <= 8", name="ck_canvas_states_zoom"),
        CheckConstraint(
            "grid_size >= 1 AND grid_size <= 200",
            name="ck_canvas_states_grid_size",
        ),
    )

    id:                       Mapped[UUID]        = mapped_column(Uuid, primary_key=True)
    database_id:              Mapped[UUID]        = mapped_column(
        Uuid,
        ForeignKey("databases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id:                  Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    viewport_x:               Mapped[float]       = mapped_column(Float, nullable=False, default=0)
    viewport_y:               Mapped[float]       = mapped_column(Float, nullable=False, default=0)
    zoom:                     Mapped[float]       = mapped_column(Float, nullable=False, default=1)
    grid_size:                Mapped[int]         = mapped_column(
        Integer,
        nullable=False,
        default=20,
    )
    snap_to_grid:             Mapped[bool]        = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    show_relationship_labels: Mapped[bool]        = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    @property
    def viewport(self) -> CanvasViewport:
        return CanvasViewport(x=self.viewport_x, y=self.viewport_y, zoom=self.zoom)

    @viewport.setter
    def viewport(self, value: CanvasViewport) -> None:
        self.viewport_x = value.x
        self.viewport_y = value.y
        self.zoom       = value.zoom


class DiagramGroups(AuditMixin, CanvasPositionMixin, Base):
    """Visual group of database tables."""

    __tablename__ = "diagram_groups"
    __table_args__ = (
        UniqueConstraint("database_id", "name", name="uq_diagram_groups_database_name"),
        CheckConstraint("width > 0", name="ck_diagram_groups_width"),
        CheckConstraint("height > 0", name="ck_diagram_groups_height"),
        CheckConstraint(
            "color IS NULL OR color ~ '^#[0-9A-Fa-f]{6}$'",
            name="ck_diagram_groups_color",
        ),
    )

    id:           Mapped[UUID]       = mapped_column(Uuid, primary_key=True)
    database_id:  Mapped[UUID]       = mapped_column(
        Uuid,
        ForeignKey("databases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name:         Mapped[str]        = mapped_column(String(255), nullable=False)
    width:        Mapped[float]      = mapped_column(Float, nullable=False)
    height:       Mapped[float]      = mapped_column(Float, nullable=False)
    color:        Mapped[str | None] = mapped_column(String(7), nullable=True)
    is_collapsed: Mapped[bool]       = mapped_column(Boolean, nullable=False, default=False)


class DiagramGroupTables(Base):
    """Table membership of a visual group."""

    __tablename__ = "diagram_group_tables"
    __table_args__ = (
        UniqueConstraint("table_id", name="uq_diagram_group_tables_table_id"),
    )

    id:       Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    group_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("diagram_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    table_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("tables.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


class DiagramNotes(AuditMixin, CanvasPositionMixin, Base):
    """Free-form note placed on a database canvas."""

    __tablename__ = "diagram_notes"
    __table_args__ = (
        CheckConstraint("width > 0", name="ck_diagram_notes_width"),
        CheckConstraint("height > 0", name="ck_diagram_notes_height"),
        CheckConstraint(
            "color IS NULL OR color ~ '^#[0-9A-Fa-f]{6}$'",
            name="ck_diagram_notes_color",
        ),
    )

    id:          Mapped[UUID]       = mapped_column(Uuid, primary_key=True)
    database_id: Mapped[UUID]       = mapped_column(
        Uuid,
        ForeignKey("databases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    text:        Mapped[str]        = mapped_column(Text, nullable=False)
    width:       Mapped[float]      = mapped_column(Float, nullable=False, default=240)
    height:      Mapped[float]      = mapped_column(Float, nullable=False, default=160)
    color:       Mapped[str | None] = mapped_column(String(7), nullable=True)
