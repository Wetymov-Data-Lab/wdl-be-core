from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from wdl_shared.schemas.engine.enums.database import ReferentialAction, RelationshipCardinality
from wdl_shared.schemas.engine.models.canvas import CanvasPosition

from common.exceptions.exceptions import EntityNotFoundError
from context.domain.entities.base import Entity
from context.domain.entities.column import Column
from context.domain.entities.table import Table


@dataclass(frozen=True, slots=True, kw_only=True)
class ColumnPair:
    """Source column referencing a target column."""

    source_column_id: UUID
    target_column_id: UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class RelationshipAttributes:
    """Mutable attributes of a relationship."""

    name: str | None
    columns: tuple[ColumnPair, ...]
    source_cardinality: RelationshipCardinality
    target_cardinality: RelationshipCardinality
    on_delete: ReferentialAction
    on_update: ReferentialAction
    waypoints: tuple[CanvasPosition, ...]


@dataclass(eq=False, kw_only=True)
class Relationship(Entity[UUID]):
    database_id: UUID
    name: str | None
    source_table_id: UUID
    target_table_id: UUID
    columns: tuple[ColumnPair, ...]
    source_cardinality: RelationshipCardinality
    target_cardinality: RelationshipCardinality
    on_delete: ReferentialAction
    on_update: ReferentialAction
    waypoints: tuple[CanvasPosition, ...]
    author_id: UUID
    created_at: datetime
    updated_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        database_id: UUID,
        source_table_id: UUID,
        target_table_id: UUID,
        attributes: RelationshipAttributes,
        author_id: UUID,
        created_at: datetime,
        relationship_id: UUID | None = None,
    ) -> "Relationship":
        return cls(
            id=relationship_id or uuid4(),
            database_id=database_id,
            name=attributes.name,
            source_table_id=source_table_id,
            target_table_id=target_table_id,
            columns=attributes.columns,
            source_cardinality=attributes.source_cardinality,
            target_cardinality=attributes.target_cardinality,
            on_delete=attributes.on_delete,
            on_update=attributes.on_update,
            waypoints=attributes.waypoints,
            author_id=author_id,
            created_at=created_at,
        )

    def ensure_endpoint_tables(self, source: Table, target: Table) -> None:
        if source.database_id != self.database_id or target.database_id != self.database_id:
            raise EntityNotFoundError("Relationship tables must belong to the requested database")

    def ensure_column_pair(self, source: Column, target: Column) -> None:
        if source.table_id != self.source_table_id or target.table_id != self.target_table_id:
            raise EntityNotFoundError("Relationship columns must belong to their endpoint tables")

    def update(self, *, attributes: RelationshipAttributes, updated_at: datetime) -> None:
        self.name = attributes.name
        self.columns = attributes.columns
        self.source_cardinality = attributes.source_cardinality
        self.target_cardinality = attributes.target_cardinality
        self.on_delete = attributes.on_delete
        self.on_update = attributes.on_update
        self.waypoints = attributes.waypoints
        self.updated_at = updated_at
