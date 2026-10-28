from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from common.exceptions.exceptions import EntityNotFoundError
from common.unit_of_work import commit_or_conflict
from context.application.use_case import UseCase
from context.domain.entities.database import Database, DatabaseAttributes
from context.infrastructure.repositories.database_contract import DatabaseUnitOfWork
from context.infrastructure.services.authorization import AuthorizationService


@dataclass(frozen=True, slots=True)
class ListDatabasesRequest:
    account_id: UUID
    project_id: UUID | None


@dataclass(frozen=True, slots=True)
class CreateDatabaseRequest:
    project_id: UUID
    attributes: DatabaseAttributes
    author_id: UUID


@dataclass(frozen=True, slots=True)
class UpdateDatabaseRequest:
    database_id: UUID
    attributes: DatabaseAttributes


class ListDatabases(UseCase[ListDatabasesRequest, list[Database]]):
    def __init__(self, uow: DatabaseUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, request: ListDatabasesRequest) -> list[Database]:
        async with self._uow:
            return await self._uow.databases.list_accessible(request.account_id, request.project_id)


class GetDatabase(UseCase[UUID, Database]):
    def __init__(self, uow: DatabaseUnitOfWork, authorization: AuthorizationService) -> None:
        self._uow = uow
        self._authorization = authorization

    async def execute(self, request: UUID) -> Database:
        await self._authorization.require_database(request)
        async with self._uow:
            return await get_database(self._uow, request)


class CreateDatabase(UseCase[CreateDatabaseRequest, Database]):
    def __init__(self, uow: DatabaseUnitOfWork, authorization: AuthorizationService) -> None:
        self._uow = uow
        self._authorization = authorization

    async def execute(self, request: CreateDatabaseRequest) -> Database:
        await self._authorization.require_project(request.project_id)
        async with self._uow:
            database = Database.create(
                project_id=request.project_id,
                attributes=request.attributes,
                author_id=request.author_id,
                created_at=datetime.now(UTC),
            )
            await self._uow.databases.add(database)
            await commit_or_conflict(self._uow, conflict_detail(request.attributes))
            return database


class UpdateDatabase(UseCase[UpdateDatabaseRequest, Database]):
    def __init__(self, uow: DatabaseUnitOfWork, authorization: AuthorizationService) -> None:
        self._uow = uow
        self._authorization = authorization

    async def execute(self, request: UpdateDatabaseRequest) -> Database:
        await self._authorization.require_database(request.database_id)
        async with self._uow:
            database = await get_database(self._uow, request.database_id)
            database.update(attributes=request.attributes, updated_at=datetime.now(UTC))
            await self._uow.databases.save(database)
            await commit_or_conflict(self._uow, conflict_detail(request.attributes))
            return database


class DeleteDatabase(UseCase[UUID, None]):
    def __init__(self, uow: DatabaseUnitOfWork, authorization: AuthorizationService) -> None:
        self._uow = uow
        self._authorization = authorization

    async def execute(self, request: UUID) -> None:
        await self._authorization.require_database(request)
        async with self._uow:
            database = await get_database(self._uow, request)
            await self._uow.databases.remove(database)
            await self._uow.commit()


async def get_database(uow: DatabaseUnitOfWork, database_id: UUID) -> Database:
    database = await uow.databases.get(database_id)
    if database is None:
        raise EntityNotFoundError(f"Database {database_id} was not found")
    return database


def conflict_detail(attributes: DatabaseAttributes) -> str:
    return f"Database '{attributes.name}' already exists in this project"
