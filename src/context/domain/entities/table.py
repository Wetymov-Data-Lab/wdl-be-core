from dataclasses import dataclass, fields
from datetime import datetime
from uuid import UUID, uuid4

from wdl_shared.schemas.engine.models.canvas import CanvasPosition

from context.domain.entities.base import Entity


@dataclass(frozen=True, slots=True, kw_only=True)
class TableAttributes:
    """Mutable attributes of a database table and its canvas card."""

    name: str
    schema_name: str | None
    description: str | None
    notice: str | None
    color: str | None
    position: CanvasPosition
    width: float | None
    is_collapsed: bool
    sort_order: int


@dataclass(eq=False, kw_only=True)
class Table(Entity[UUID]):
    database_id: UUID
    name: str
    schema_name: str | None
    description: str | None
    notice: str | None
    color: str | None
    position: CanvasPosition
    width: float | None
    is_collapsed: bool
    sort_order: int
    author_id: UUID
    created_at: datetime
    updated_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        database_id: UUID,
        attributes: TableAttributes,
        author_id: UUID,
        created_at: datetime,
        table_id: UUID | None = None,
    ) -> "Table":
        return cls(
            id=table_id or uuid4(),
            database_id=database_id,
            name=attributes.name,
            schema_name=attributes.schema_name,
            description=attributes.description,
            notice=attributes.notice,
            color=attributes.color,
            position=attributes.position,
            width=attributes.width,
            is_collapsed=attributes.is_collapsed,
            sort_order=attributes.sort_order,
            author_id=author_id,
            created_at=created_at,
        )

    def update(self, *, attributes: TableAttributes, updated_at: datetime) -> None:
        for field in fields(attributes):
            setattr(self, field.name, getattr(attributes, field.name))
        self.updated_at = updated_at
