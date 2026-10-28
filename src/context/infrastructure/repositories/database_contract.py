from abc import abstractmethod
from uuid import UUID

from common.mixins.base_repository import Repository
from common.unit_of_work import UnitOfWork
from context.domain.entities.database import Database


class DatabaseRepository(Repository[Database, UUID]):
    @abstractmethod
    async def list_accessible(
        self, account_id: UUID, project_id: UUID | None = None
    ) -> list[Database]: ...

    @abstractmethod
    async def save(self, database: Database) -> None: ...


class DatabaseUnitOfWork(UnitOfWork):
    databases: DatabaseRepository
