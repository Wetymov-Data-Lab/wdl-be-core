from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from common.exceptions.exceptions import EntityNotFoundError
from common.unit_of_work import commit_or_conflict
from context.application.use_case import UseCase
from context.domain.entities.table import Table, TableAttributes
from context.infrastructure.repositories.table_contract import (
    TableRepository,
    TableUnitOfWork,
)
from context.infrastructure.services.authorization import AuthorizationService


@dataclass(frozen=True, slots=True)
class CreateTableRequest:
    database_id: UUID
    attributes: TableAttributes
    author_id: UUID


@dataclass(frozen=True, slots=True)
class UpdateTableRequest:
    table_id: UUID
    attributes: TableAttributes


class ListTables(UseCase[UUID, list[Table]]):
    def __init__(self, uow: TableUnitOfWork, authorization: AuthorizationService) -> None:
        self._uow = uow
        self._authorization = authorization

    async def execute(self, request: UUID) -> list[Table]:
        await self._authorization.require_database(request)
        async with self._uow:
            return await self._uow.tables.list(request)


class GetTable(UseCase[UUID, Table]):
    def __init__(self, uow: TableUnitOfWork, authorization: AuthorizationService) -> None:
        self._uow = uow
        self._authorization = authorization

    async def execute(self, request: UUID) -> Table:
        await self._authorization.require_table(request)
        async with self._uow:
            return await get_table(self._uow, request)


class CreateTable(UseCase[CreateTableRequest, Table]):
    def __init__(self, uow: TableUnitOfWork, authorization: AuthorizationService) -> None:
        self._uow = uow
        self._authorization = authorization

    async def execute(self, request: CreateTableRequest) -> Table:
        await self._authorization.require_database(request.database_id)
        async with self._uow:
            table = Table.create(
                database_id=request.database_id,
                attributes=request.attributes,
                author_id=request.author_id,
                created_at=datetime.now(UTC),
            )
            await self._uow.tables.add(table)
            await commit_or_conflict(self._uow, conflict_detail(request.attributes))
            return table


class UpdateTable(UseCase[UpdateTableRequest, Table]):
    def __init__(self, uow: TableUnitOfWork, authorization: AuthorizationService) -> None:
        self._uow = uow
        self._authorization = authorization

    async def execute(self, request: UpdateTableRequest) -> Table:
        await self._authorization.require_table(request.table_id)
        async with self._uow:
            table = await get_table(self._uow, request.table_id)
            table.update(attributes=request.attributes, updated_at=datetime.now(UTC))
            await self._uow.tables.save(table)
            await commit_or_conflict(self._uow, conflict_detail(request.attributes))
            return table


class DeleteTable(UseCase[UUID, None]):
    def __init__(self, uow: TableUnitOfWork, authorization: AuthorizationService) -> None:
        self._uow = uow
        self._authorization = authorization

    async def execute(self, request: UUID) -> None:
        await self._authorization.require_table(request)
        async with self._uow:
            table = await get_table(self._uow, request)
            await self._uow.tables.remove(table)
            await self._uow.commit()


async def get_table(uow: TableUnitOfWork, table_id: UUID) -> Table:
    return await find_table(uow.tables, table_id)


async def load_accessible_table(
    authorization: AuthorizationService, repository: TableRepository, table_id: UUID
) -> Table:
    await authorization.require_table(table_id)
    return await find_table(repository, table_id)


async def find_table(repository: TableRepository, table_id: UUID) -> Table:
    table = await repository.get(table_id)
    if table is None:
        raise EntityNotFoundError(f"Table {table_id} was not found")
    return table


def conflict_detail(attributes: TableAttributes) -> str:
    return f"Table '{attributes.name}' already exists in this database"
