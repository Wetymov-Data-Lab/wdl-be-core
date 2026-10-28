import builtins
from collections import defaultdict
from collections.abc import Sequence
from uuid import UUID, uuid4

from sqlalchemy import ColumnElement, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from wdl_shared.schemas.engine.enums.database import IndexType, SortOrder

from context.domain.entities.index import DiagramIndex, IndexColumn
from context.infrastructure.repositories.index_contract import (
    IndexRepository as AbstractIndexRepository,
)
from context.infrastructure.schemas.database import DiagramIndexColumns, DiagramIndexes, Tables


class IndexRepository(AbstractIndexRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, entity_id: UUID) -> DiagramIndex | None:
        model = await self._session.get(DiagramIndexes, entity_id)
        if model is None:
            return None
        return (await self._to_domain([model], DiagramIndexColumns.index_id == model.id))[0]

    async def list(self, table_id: UUID) -> builtins.list[DiagramIndex]:
        models = (
            await self._session.scalars(
                select(DiagramIndexes)
                .where(DiagramIndexes.table_id == table_id)
                .order_by(DiagramIndexes.created_at)
            )
        ).all()
        return await self._to_domain(models, DiagramIndexes.table_id == table_id)

    async def list_by_database(self, database_id: UUID) -> builtins.list[DiagramIndex]:
        models = (
            await self._session.scalars(
                select(DiagramIndexes).join(Tables).where(Tables.database_id == database_id)
            )
        ).all()
        return await self._to_domain(models, Tables.database_id == database_id)

    async def add(self, entity: DiagramIndex) -> None:
        self._session.add(
            DiagramIndexes(
                id=entity.id,
                table_id=entity.table_id,
                name=entity.name,
                type=entity.type,
                method=entity.method,
                where=entity.where,
                author_id=entity.author_id,
                created_at=entity.created_at,
                updated_at=entity.updated_at,
            )
        )

    async def add_columns(self, index: DiagramIndex) -> None:
        self._session.add_all(
            DiagramIndexColumns(
                id=uuid4(),
                index_id=index.id,
                column_id=column.column_id,
                sort_order=column.sort_order,
                position=column.position,
            )
            for column in index.columns
        )

    async def save(self, index: DiagramIndex) -> None:
        model = await self._session.get_one(DiagramIndexes, index.id)
        model.name = index.name
        model.type = index.type
        model.method = index.method
        model.where = index.where
        model.updated_at = index.updated_at

    async def replace_columns(self, index: DiagramIndex) -> None:
        await self._session.execute(
            delete(DiagramIndexColumns).where(DiagramIndexColumns.index_id == index.id)
        )
        await self._session.flush()
        await self.add_columns(index)

    async def remove(self, entity: DiagramIndex) -> None:
        await self._session.execute(delete(DiagramIndexes).where(DiagramIndexes.id == entity.id))

    async def _to_domain(
        self, models: Sequence[DiagramIndexes], scope: ColumnElement[bool]
    ) -> builtins.list[DiagramIndex]:
        """Load memberships with the same scope as the indexes, never by bare ids."""
        if not models:
            return []
        rows = (
            await self._session.scalars(
                select(DiagramIndexColumns)
                .join(DiagramIndexes)
                .join(Tables)
                .where(scope)
                .order_by(DiagramIndexColumns.position)
            )
        ).all()
        columns: defaultdict[UUID, builtins.list[IndexColumn]] = defaultdict(builtins.list)
        for row in rows:
            columns[row.index_id].append(
                IndexColumn(
                    column_id=row.column_id,
                    sort_order=SortOrder(row.sort_order),
                    position=row.position,
                )
            )
        return [
            DiagramIndex(
                id=model.id,
                table_id=model.table_id,
                name=model.name,
                type=IndexType(model.type),
                columns=tuple(columns[model.id]),
                method=model.method,
                where=model.where,
                author_id=model.author_id,
                created_at=model.created_at,
                updated_at=model.updated_at,
            )
            for model in models
        ]
