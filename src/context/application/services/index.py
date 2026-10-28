from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from common.exceptions.exceptions import EntityNotFoundError
from common.unit_of_work import commit_or_conflict
from context.application.services.column import load_accessible_column
from context.application.use_case import UseCase
from context.domain.entities.index import DiagramIndex, IndexAttributes
from context.infrastructure.repositories.index_contract import IndexUnitOfWork
from context.infrastructure.services.authorization import AuthorizationService

DUPLICATE_COLUMNS = "Index contains duplicate columns or positions"


@dataclass(frozen=True, slots=True)
class CreateIndexRequest:
    table_id: UUID
    attributes: IndexAttributes
    author_id: UUID


@dataclass(frozen=True, slots=True)
class UpdateIndexRequest:
    index_id: UUID
    attributes: IndexAttributes


class ListIndexes(UseCase[UUID, list[DiagramIndex]]):
    def __init__(self, uow: IndexUnitOfWork, authorization: AuthorizationService) -> None:
        self._uow = uow
        self._authorization = authorization

    async def execute(self, request: UUID) -> list[DiagramIndex]:
        await self._authorization.require_table(request)
        async with self._uow:
            return await self._uow.indexes.list(request)


class GetIndex(UseCase[UUID, DiagramIndex]):
    def __init__(self, uow: IndexUnitOfWork, authorization: AuthorizationService) -> None:
        self._uow = uow
        self._authorization = authorization

    async def execute(self, request: UUID) -> DiagramIndex:
        await self._authorization.require_index(request)
        async with self._uow:
            return await get_index(self._uow, request)


class CreateIndex(UseCase[CreateIndexRequest, DiagramIndex]):
    def __init__(self, uow: IndexUnitOfWork, authorization: AuthorizationService) -> None:
        self._uow = uow
        self._authorization = authorization

    async def execute(self, request: CreateIndexRequest) -> DiagramIndex:
        await self._authorization.require_table(request.table_id)
        async with self._uow:
            index = DiagramIndex.create(
                table_id=request.table_id,
                attributes=request.attributes,
                author_id=request.author_id,
                created_at=datetime.now(UTC),
            )
            await ensure_columns(self._uow, self._authorization, index, request.attributes)
            await self._uow.indexes.add(index)
            await commit_or_conflict(self._uow, f"Index '{request.attributes.name}' already exists")
            await self._uow.indexes.add_columns(index)
            await commit_or_conflict(self._uow, DUPLICATE_COLUMNS)
            return index


class UpdateIndex(UseCase[UpdateIndexRequest, DiagramIndex]):
    def __init__(self, uow: IndexUnitOfWork, authorization: AuthorizationService) -> None:
        self._uow = uow
        self._authorization = authorization

    async def execute(self, request: UpdateIndexRequest) -> DiagramIndex:
        await self._authorization.require_index(request.index_id)
        async with self._uow:
            index = await get_index(self._uow, request.index_id)
            await ensure_columns(self._uow, self._authorization, index, request.attributes)
            index.update(attributes=request.attributes, updated_at=datetime.now(UTC))
            await self._uow.indexes.save(index)
            await self._uow.indexes.replace_columns(index)
            await commit_or_conflict(self._uow, DUPLICATE_COLUMNS)
            return index


class DeleteIndex(UseCase[UUID, None]):
    def __init__(self, uow: IndexUnitOfWork, authorization: AuthorizationService) -> None:
        self._uow = uow
        self._authorization = authorization

    async def execute(self, request: UUID) -> None:
        await self._authorization.require_index(request)
        async with self._uow:
            index = await get_index(self._uow, request)
            await self._uow.indexes.remove(index)
            await self._uow.commit()


async def get_index(uow: IndexUnitOfWork, index_id: UUID) -> DiagramIndex:
    index = await uow.indexes.get(index_id)
    if index is None:
        raise EntityNotFoundError(f"Diagram index {index_id} was not found")
    return index


async def ensure_columns(
    uow: IndexUnitOfWork,
    authorization: AuthorizationService,
    index: DiagramIndex,
    attributes: IndexAttributes,
) -> None:
    """Check access to every requested column and that it belongs to the index table."""
    for member in attributes.columns:
        column = await load_accessible_column(authorization, uow.columns, member.column_id)
        index.ensure_column_in_table(column)
