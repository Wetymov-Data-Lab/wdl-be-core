import builtins
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from wdl_shared.schemas.engine.enums.database import ColumnType

from context.domain.entities.column import Column
from context.infrastructure.repositories.column_contract import (
    ColumnRepository as AbstractColumnRepository,
)
from context.infrastructure.schemas.database import Columns, Tables


class ColumnRepository(AbstractColumnRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, entity_id: UUID) -> Column | None:
        model = await self._session.get(Columns, entity_id)
        return None if model is None else self._to_domain(model)

    async def list(self, table_id: UUID) -> builtins.list[Column]:
        models = (
            await self._session.scalars(
                select(Columns)
                .where(Columns.table_id == table_id)
                .order_by(Columns.sort_order, Columns.created_at)
            )
        ).all()
        return [self._to_domain(model) for model in models]

    async def list_by_database(self, database_id: UUID) -> builtins.list[Column]:
        models = (
            await self._session.scalars(
                select(Columns).join(Tables).where(Tables.database_id == database_id)
            )
        ).all()
        return [self._to_domain(model) for model in models]

    async def add(self, entity: Column) -> None:
        self._session.add(
            Columns(
                id=entity.id,
                table_id=entity.table_id,
                author_id=entity.author_id,
                created_at=entity.created_at,
                updated_at=entity.updated_at,
                **self._values(entity),
            )
        )

    async def save(self, column: Column) -> None:
        model = await self._session.get_one(Columns, column.id)
        for field, value in self._values(column).items():
            setattr(model, field, value)
        model.updated_at = column.updated_at

    async def remove(self, entity: Column) -> None:
        await self._session.execute(delete(Columns).where(Columns.id == entity.id))

    @staticmethod
    def _values(column: Column) -> dict[str, object]:
        return {
            "name": column.name,
            "type": column.type,
            "custom_type": column.custom_type,
            "length": column.length,
            "precision": column.precision,
            "scale": column.scale,
            "array_dimensions": column.array_dimensions,
            "nullable": column.nullable,
            "primary_key": column.primary_key,
            "unique": column.unique,
            "auto_increment": column.auto_increment,
            "unsigned": column.unsigned,
            "default": column.default,
            "check": column.check,
            "enum_values": list(column.enum_values),
            "sort_order": column.sort_order,
            "notice": column.notice,
        }

    @staticmethod
    def _to_domain(model: Columns) -> Column:
        return Column(
            id=model.id,
            table_id=model.table_id,
            name=model.name,
            type=ColumnType(model.type),
            custom_type=model.custom_type,
            length=model.length,
            precision=model.precision,
            scale=model.scale,
            array_dimensions=model.array_dimensions,
            nullable=model.nullable,
            primary_key=model.primary_key,
            unique=model.unique,
            auto_increment=model.auto_increment,
            unsigned=model.unsigned,
            default=model.default,
            check=model.check,
            enum_values=list(model.enum_values),
            sort_order=model.sort_order,
            notice=model.notice,
            author_id=model.author_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
