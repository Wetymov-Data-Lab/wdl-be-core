import builtins
from collections import defaultdict
from collections.abc import Sequence
from uuid import UUID, uuid4

from sqlalchemy import ColumnElement, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from wdl_shared.schemas.engine.enums.database import ReferentialAction, RelationshipCardinality
from wdl_shared.schemas.engine.models.canvas import CanvasPosition

from context.domain.entities.relationship import ColumnPair, Relationship
from context.infrastructure.repositories.relationship_contract import (
    RelationshipRepository as AbstractRelationshipRepository,
)
from context.infrastructure.schemas.database import RelationshipColumns, Relationships


class RelationshipRepository(AbstractRelationshipRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, entity_id: UUID) -> Relationship | None:
        model = await self._session.get(Relationships, entity_id)
        if model is None:
            return None
        return (await self._to_domain([model], Relationships.id == model.id))[0]

    async def list(self, database_id: UUID) -> builtins.list[Relationship]:
        models = (
            await self._session.scalars(
                select(Relationships)
                .where(Relationships.database_id == database_id)
                .order_by(Relationships.created_at)
            )
        ).all()
        return await self._to_domain(models, Relationships.database_id == database_id)

    async def add(self, entity: Relationship) -> None:
        self._session.add(
            Relationships(
                id=entity.id,
                database_id=entity.database_id,
                name=entity.name,
                source_table_id=entity.source_table_id,
                target_table_id=entity.target_table_id,
                source_cardinality=entity.source_cardinality,
                target_cardinality=entity.target_cardinality,
                on_delete=entity.on_delete,
                on_update=entity.on_update,
                waypoints=self._waypoints(entity),
                author_id=entity.author_id,
                created_at=entity.created_at,
                updated_at=entity.updated_at,
            )
        )

    async def add_columns(self, relationship: Relationship) -> None:
        self._session.add_all(
            RelationshipColumns(
                id=uuid4(),
                relationship_id=relationship.id,
                source_column_id=pair.source_column_id,
                target_column_id=pair.target_column_id,
            )
            for pair in relationship.columns
        )

    async def save(self, relationship: Relationship) -> None:
        model = await self._session.get_one(Relationships, relationship.id)
        model.name = relationship.name
        model.source_cardinality = relationship.source_cardinality
        model.target_cardinality = relationship.target_cardinality
        model.on_delete = relationship.on_delete
        model.on_update = relationship.on_update
        model.waypoints = self._waypoints(relationship)
        model.updated_at = relationship.updated_at

    async def replace_columns(self, relationship: Relationship) -> None:
        await self._session.execute(
            delete(RelationshipColumns).where(
                RelationshipColumns.relationship_id == relationship.id
            )
        )
        await self._session.flush()
        await self.add_columns(relationship)

    async def remove(self, entity: Relationship) -> None:
        await self._session.execute(delete(Relationships).where(Relationships.id == entity.id))

    @staticmethod
    def _waypoints(relationship: Relationship) -> builtins.list[dict[str, float]]:
        return [waypoint.model_dump() for waypoint in relationship.waypoints]

    async def _to_domain(
        self, models: Sequence[Relationships], scope: ColumnElement[bool]
    ) -> builtins.list[Relationship]:
        """Load mappings with the same scope as the relationships, never by bare ids."""
        if not models:
            return []
        rows = (
            await self._session.scalars(
                select(RelationshipColumns).join(Relationships).where(scope)
            )
        ).all()
        columns: defaultdict[UUID, builtins.list[ColumnPair]] = defaultdict(builtins.list)
        for row in rows:
            columns[row.relationship_id].append(
                ColumnPair(
                    source_column_id=row.source_column_id,
                    target_column_id=row.target_column_id,
                )
            )
        return [
            Relationship(
                id=model.id,
                database_id=model.database_id,
                name=model.name,
                source_table_id=model.source_table_id,
                target_table_id=model.target_table_id,
                columns=tuple(columns[model.id]),
                source_cardinality=RelationshipCardinality(model.source_cardinality),
                target_cardinality=RelationshipCardinality(model.target_cardinality),
                on_delete=ReferentialAction(model.on_delete),
                on_update=ReferentialAction(model.on_update),
                waypoints=tuple(
                    CanvasPosition.model_validate(waypoint) for waypoint in model.waypoints
                ),
                author_id=model.author_id,
                created_at=model.created_at,
                updated_at=model.updated_at,
            )
            for model in models
        ]
