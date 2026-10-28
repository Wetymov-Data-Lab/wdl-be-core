from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from wdl_shared.schemas.engine.enums.database import IndexType, SortOrder

from common.exceptions.exceptions import EntityNotFoundError
from context.domain.entities.base import Entity
from context.domain.entities.column import Column


@dataclass(frozen=True, slots=True, kw_only=True)
class IndexColumn:
    """Ordered membership of a column in an index."""

    column_id: UUID
    sort_order: SortOrder
    position: int


@dataclass(frozen=True, slots=True, kw_only=True)
class IndexAttributes:
    """Mutable attributes of a diagram index."""

    name: str | None
    type: IndexType
    columns: tuple[IndexColumn, ...]
    method: str | None
    where: str | None


@dataclass(eq=False, kw_only=True)
class DiagramIndex(Entity[UUID]):
    table_id: UUID
    name: str | None
    type: IndexType
    columns: tuple[IndexColumn, ...]
    method: str | None
    where: str | None
    author_id: UUID
    created_at: datetime
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        self.columns = ordered(self.columns)

    @classmethod
    def create(
        cls,
        *,
        table_id: UUID,
        attributes: IndexAttributes,
        author_id: UUID,
        created_at: datetime,
        index_id: UUID | None = None,
    ) -> "DiagramIndex":
        return cls(
            id=index_id or uuid4(),
            table_id=table_id,
            name=attributes.name,
            type=attributes.type,
            columns=attributes.columns,
            method=attributes.method,
            where=attributes.where,
            author_id=author_id,
            created_at=created_at,
        )

    def ensure_column_in_table(self, column: Column) -> None:
        if column.table_id != self.table_id:
            raise EntityNotFoundError(
                f"Column {column.id} does not belong to table {self.table_id}"
            )

    def update(self, *, attributes: IndexAttributes, updated_at: datetime) -> None:
        self.name = attributes.name
        self.type = attributes.type
        self.columns = ordered(attributes.columns)
        self.method = attributes.method
        self.where = attributes.where
        self.updated_at = updated_at


def ordered(columns: tuple[IndexColumn, ...]) -> tuple[IndexColumn, ...]:
    return tuple(sorted(columns, key=lambda column: column.position))
