from abc import abstractmethod
from uuid import UUID

from common.mixins.base_repository import Repository
from common.unit_of_work import UnitOfWork
from context.domain.entities.table import Table


class TableRepository(Repository[Table, UUID]):
    @abstractmethod
    async def list(self, database_id: UUID) -> list[Table]: ...

    @abstractmethod
    async def save(self, table: Table) -> None: ...


class TableUnitOfWork(UnitOfWork):
    tables: TableRepository
