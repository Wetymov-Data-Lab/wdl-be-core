from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from common.exceptions.exceptions import EntityNotFoundError
from common.unit_of_work import commit_or_conflict
from context.application.use_case import UseCase
from context.domain.entities.column import Column, ColumnAttributes
from context.infrastructure.repositories.column_contract import (
    ColumnRepository,
    ColumnUnitOfWork,
)
from context.infrastructure.services.authorization import AuthorizationService


@dataclass(frozen=True, slots=True)
class CreateColumnRequest:
    table_id: UUID
    attributes: ColumnAttributes
    author_id: UUID


@dataclass(frozen=True, slots=True)
class UpdateColumnRequest:
    column_id: UUID
    attributes: ColumnAttributes


class ListColumns(UseCase[UUID, list[Column]]):
    def __init__(self, uow: ColumnUnitOfWork, authorization: AuthorizationService) -> None:
        self._uow = uow
        self._authorization = authorization

    async def execute(self, request: UUID) -> list[Column]:
        await self._authorization.require_table(request)
        async with self._uow:
            return await self._uow.columns.list(request)


class GetColumn(UseCase[UUID, Column]):
    def __init__(self, uow: ColumnUnitOfWork, authorization: AuthorizationService) -> None:
        self._uow = uow
        self._authorization = authorization

    async def execute(self, request: UUID) -> Column:
        await self._authorization.require_column(request)
        async with self._uow:
            return await get_column(self._uow, request)


class CreateColumn(UseCase[CreateColumnRequest, Column]):
    def __init__(self, uow: ColumnUnitOfWork, authorization: AuthorizationService) -> None:
        self._uow = uow
        self._authorization = authorization

    async def execute(self, request: CreateColumnRequest) -> Column:
        await self._authorization.require_table(request.table_id)
        async with self._uow:
            column = Column.create(
                table_id=request.table_id,
                attributes=request.attributes,
                author_id=request.author_id,
                created_at=datetime.now(UTC),
            )
            await self._uow.columns.add(column)
            await commit_or_conflict(self._uow, conflict_detail(request.attributes))
            return column


class UpdateColumn(UseCase[UpdateColumnRequest, Column]):
    def __init__(self, uow: ColumnUnitOfWork, authorization: AuthorizationService) -> None:
        self._uow = uow
        self._authorization = authorization

    async def execute(self, request: UpdateColumnRequest) -> Column:
        await self._authorization.require_column(request.column_id)
        async with self._uow:
            column = await get_column(self._uow, request.column_id)
            column.update(attributes=request.attributes, updated_at=datetime.now(UTC))
            await self._uow.columns.save(column)
            await commit_or_conflict(self._uow, conflict_detail(request.attributes))
            return column


class DeleteColumn(UseCase[UUID, None]):
    def __init__(self, uow: ColumnUnitOfWork, authorization: AuthorizationService) -> None:
        self._uow = uow
        self._authorization = authorization

    async def execute(self, request: UUID) -> None:
        await self._authorization.require_column(request)
        async with self._uow:
            column = await get_column(self._uow, request)
            await self._uow.columns.remove(column)
            await self._uow.commit()


async def get_column(uow: ColumnUnitOfWork, column_id: UUID) -> Column:
    return await find_column(uow.columns, column_id)


async def load_accessible_column(
    authorization: AuthorizationService, repository: ColumnRepository, column_id: UUID
) -> Column:
    await authorization.require_column(column_id)
    return await find_column(repository, column_id)


async def find_column(repository: ColumnRepository, column_id: UUID) -> Column:
    column = await repository.get(column_id)
    if column is None:
        raise EntityNotFoundError(f"Column {column_id} was not found")
    return column


def conflict_detail(attributes: ColumnAttributes) -> str:
    return f"Column '{attributes.name}' already exists in this table"
