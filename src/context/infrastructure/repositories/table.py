import builtins
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from context.domain.entities.table import Table, TableCheck
from context.infrastructure.repositories.table_contract import (
    TableRepository as AbstractTableRepository,
)
from context.infrastructure.schemas.database import Tables


class TableRepository(AbstractTableRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, entity_id: UUID) -> Table | None:
        model = await self._session.get(Tables, entity_id)
        return None if model is None else self._to_domain(model)

    async def list(self, database_id: UUID) -> builtins.list[Table]:
        models = (
            await self._session.scalars(
                select(Tables)
                .where(Tables.database_id == database_id)
                .order_by(Tables.sort_order, Tables.created_at)
            )
        ).all()
        return [self._to_domain(model) for model in models]

    async def add(self, entity: Table) -> None:
        model = Tables(
            id=entity.id,
            database_id=entity.database_id,
            name=entity.name,
            schema_name=entity.schema_name,
            description=entity.description,
            notice=entity.notice,
            color=entity.color,
            width=entity.width,
            is_collapsed=entity.is_collapsed,
            sort_order=entity.sort_order,
            checks=checks_to_json(entity.checks),
            author_id=entity.author_id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        model.position = entity.position
        self._session.add(model)

    async def save(self, table: Table) -> None:
        model = await self._session.get_one(Tables, table.id)
        model.name = table.name
        model.schema_name = table.schema_name
        model.description = table.description
        model.notice = table.notice
        model.color = table.color
        model.position = table.position
        model.width = table.width
        model.is_collapsed = table.is_collapsed
        model.sort_order = table.sort_order
        model.checks = checks_to_json(table.checks)
        model.updated_at = table.updated_at

    async def remove(self, entity: Table) -> None:
        await self._session.execute(delete(Tables).where(Tables.id == entity.id))

    @staticmethod
    def _to_domain(model: Tables) -> Table:
        return Table(
            id=model.id,
            database_id=model.database_id,
            name=model.name,
            schema_name=model.schema_name,
            description=model.description,
            notice=model.notice,
            color=model.color,
            position=model.position,
            width=model.width,
            is_collapsed=model.is_collapsed,
            sort_order=model.sort_order,
            checks=tuple(
                TableCheck(name=check["name"], expression=check["expression"])
                for check in model.checks
            ),
            author_id=model.author_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


def checks_to_json(checks: tuple[TableCheck, ...]) -> list[dict[str, Any]]:
    return [{"name": check.name, "expression": check.expression} for check in checks]
