from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from wdl_be_core.application.use_cases import UseCase
from wdl_be_core.domain.entities.group import DiagramGroup, GroupName
from wdl_be_core.domain.exceptions import EntityAlreadyExistsError, EntityNotFoundError
from wdl_be_core.domain.repositories.group import GroupUnitOfWork


@dataclass(frozen=True, slots=True)
class GroupData:
    database_id: UUID
    name: str
    x: float
    y: float
    width: float
    height: float
    color: str | None
    is_collapsed: bool
    table_ids: list[UUID]


@dataclass(frozen=True, slots=True)
class CreateGroupRequest(GroupData):
    author_id: UUID
    group_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class UpdateGroupRequest(GroupData):
    group_id: UUID
    updated_by: UUID


@dataclass(frozen=True, slots=True)
class DeleteGroupRequest:
    database_id: UUID
    group_id: UUID
    deleted_by: UUID


class ListGroups(UseCase[UUID, list[DiagramGroup]]):
    def __init__(self, uow: GroupUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, request: UUID) -> list[DiagramGroup]:
        async with self._uow:
            return await self._uow.groups.list(request)


class CreateGroup(UseCase[CreateGroupRequest, DiagramGroup]):
    def __init__(self, uow: GroupUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, request: CreateGroupRequest) -> DiagramGroup:
        group = DiagramGroup.create(
            database_id=request.database_id,
            name=request.name,
            x=request.x,
            y=request.y,
            width=request.width,
            height=request.height,
            color=request.color,
            is_collapsed=request.is_collapsed,
            table_ids=request.table_ids,
            author_id=request.author_id,
            created_at=datetime.now(UTC),
            group_id=request.group_id,
        )
        async with self._uow:
            await self._validate_references(group)
            if await self._uow.groups.exists_by_name(group.database_id, group.name):
                raise EntityAlreadyExistsError(f"Diagram group '{group.name.value}' already exists")
            await self._uow.groups.add(group)
            await self._uow.commit()
            return group

    async def _validate_references(self, group: DiagramGroup) -> None:
        if not await self._uow.groups.database_exists(group.database_id):
            raise EntityNotFoundError(f"Database {group.database_id} was not found")
        if not await self._uow.groups.tables_belong_to_database(group.table_ids, group.database_id):
            raise EntityNotFoundError("Every grouped table must belong to the target database")


class UpdateGroup(UseCase[UpdateGroupRequest, DiagramGroup]):
    def __init__(self, uow: GroupUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, request: UpdateGroupRequest) -> DiagramGroup:
        async with self._uow:
            group = await self._uow.groups.get(request.group_id)
            if group is None or group.database_id != request.database_id:
                raise EntityNotFoundError(f"Diagram group {request.group_id} was not found")
            group.update(
                name=request.name,
                x=request.x,
                y=request.y,
                width=request.width,
                height=request.height,
                color=request.color,
                is_collapsed=request.is_collapsed,
                table_ids=request.table_ids,
                updated_by=request.updated_by,
                updated_at=datetime.now(UTC),
            )
            if not await self._uow.groups.tables_belong_to_database(
                group.table_ids, group.database_id
            ):
                raise EntityNotFoundError("Every grouped table must belong to the target database")
            if await self._uow.groups.exists_by_name(
                group.database_id, GroupName(value=request.name), exclude_id=group.id
            ):
                raise EntityAlreadyExistsError(f"Diagram group '{group.name.value}' already exists")
            await self._uow.groups.save(group)
            await self._uow.commit()
            return group


class DeleteGroup(UseCase[DeleteGroupRequest, None]):
    def __init__(self, uow: GroupUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, request: DeleteGroupRequest) -> None:
        async with self._uow:
            group = await self._uow.groups.get(request.group_id)
            if group is None or group.database_id != request.database_id:
                raise EntityNotFoundError(f"Diagram group {request.group_id} was not found")
            group.ensure_owned_by(request.deleted_by)
            await self._uow.groups.remove(group)
            await self._uow.commit()
