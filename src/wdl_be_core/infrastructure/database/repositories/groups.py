from uuid import UUID, uuid4

from sqlalchemy import delete, exists, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from wdl_be_core.domain.entities.group import (
    CanvasColor,
    CanvasPoint,
    DiagramGroup,
    GroupName,
    GroupSize,
)
from wdl_be_core.domain.repositories.group import GroupRepository as AbstractGroupRepository
from wdl_be_core.infrastructure.database.models.canvas import DiagramGroups, DiagramGroupTables
from wdl_be_core.infrastructure.database.models.database import Databases, Tables


class GroupRepository(AbstractGroupRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, entity_id: UUID) -> DiagramGroup | None:
        model = await self._session.get(DiagramGroups, entity_id)
        return None if model is None else await self._to_domain(model)

    async def list(self, database_id: UUID) -> list[DiagramGroup]:
        models = (
            await self._session.scalars(
                select(DiagramGroups)
                .where(DiagramGroups.database_id == database_id)
                .order_by(DiagramGroups.created_at)
            )
        ).all()
        return [await self._to_domain(model) for model in models]

    async def database_exists(self, database_id: UUID) -> bool:
        return bool(await self._session.scalar(select(exists().where(Databases.id == database_id))))

    async def tables_belong_to_database(
        self, table_ids: tuple[UUID, ...], database_id: UUID
    ) -> bool:
        if not table_ids:
            return True
        count = await self._session.scalar(
            select(func.count())
            .select_from(Tables)
            .where(Tables.id.in_(table_ids), Tables.database_id == database_id)
        )
        return count == len(table_ids)

    async def exists_by_name(
        self, database_id: UUID, name: GroupName, *, exclude_id: UUID | None = None
    ) -> bool:
        filters = [DiagramGroups.database_id == database_id, DiagramGroups.name == name.value]
        if exclude_id is not None:
            filters.append(DiagramGroups.id != exclude_id)
        return bool(await self._session.scalar(select(exists().where(*filters))))

    async def add(self, entity: DiagramGroup) -> None:
        self._session.add(
            DiagramGroups(
                id=entity.id,
                database_id=entity.database_id,
                name=entity.name.value,
                position_x=entity.position.x,
                position_y=entity.position.y,
                width=entity.size.width,
                height=entity.size.height,
                color=None if entity.color is None else entity.color.value,
                is_collapsed=entity.is_collapsed,
                author_id=entity.author_id,
                created_at=entity.created_at,
                updated_at=entity.updated_at,
            )
        )
        self._session.add_all(
            DiagramGroupTables(id=uuid4(), group_id=entity.id, table_id=table_id)
            for table_id in entity.table_ids
        )

    async def save(self, group: DiagramGroup) -> None:
        await self._session.execute(
            update(DiagramGroups)
            .where(DiagramGroups.id == group.id)
            .values(
                name=group.name.value,
                position_x=group.position.x,
                position_y=group.position.y,
                width=group.size.width,
                height=group.size.height,
                color=None if group.color is None else group.color.value,
                is_collapsed=group.is_collapsed,
                updated_at=group.updated_at,
            )
        )
        await self._session.execute(
            delete(DiagramGroupTables).where(DiagramGroupTables.group_id == group.id)
        )
        self._session.add_all(
            DiagramGroupTables(id=uuid4(), group_id=group.id, table_id=table_id)
            for table_id in group.table_ids
        )

    async def remove(self, entity: DiagramGroup) -> None:
        await self._session.execute(delete(DiagramGroups).where(DiagramGroups.id == entity.id))

    async def _to_domain(self, model: DiagramGroups) -> DiagramGroup:
        table_ids = (
            await self._session.scalars(
                select(DiagramGroupTables.table_id).where(DiagramGroupTables.group_id == model.id)
            )
        ).all()
        return DiagramGroup(
            id=model.id,
            database_id=model.database_id,
            name=GroupName(value=model.name),
            position=CanvasPoint(x=model.position_x, y=model.position_y),
            size=GroupSize(width=model.width, height=model.height),
            color=None if model.color is None else CanvasColor(value=model.color),
            is_collapsed=model.is_collapsed,
            table_ids=tuple(table_ids),
            author_id=model.author_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
