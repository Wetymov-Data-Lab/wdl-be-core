import builtins
from abc import abstractmethod
from uuid import UUID

from common.mixins.base_repository import Repository
from common.unit_of_work import UnitOfWork
from context.domain.entities.column import Column


class ColumnRepository(Repository[Column, UUID]):
    @abstractmethod
    async def list(self, table_id: UUID) -> list[Column]: ...

    @abstractmethod
    async def list_by_database(self, database_id: UUID) -> builtins.list[Column]: ...

    @abstractmethod
    async def save(self, column: Column) -> None: ...


class ColumnUnitOfWork(UnitOfWork):
    columns: ColumnRepository
