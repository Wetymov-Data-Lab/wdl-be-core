import builtins
from abc import abstractmethod
from uuid import UUID

from common.mixins.base_repository import Repository
from common.unit_of_work import UnitOfWork
from context.domain.entities.index import DiagramIndex
from context.infrastructure.repositories.column_contract import ColumnRepository


class IndexRepository(Repository[DiagramIndex, UUID]):
    """Index rows and their column memberships.

    `add` stores only the index row and `add_columns` its memberships, so the
    caller can flush between them and report name and membership conflicts apart.
    """

    @abstractmethod
    async def list(self, table_id: UUID) -> list[DiagramIndex]: ...

    @abstractmethod
    async def list_by_database(self, database_id: UUID) -> builtins.list[DiagramIndex]: ...

    @abstractmethod
    async def add_columns(self, index: DiagramIndex) -> None: ...

    @abstractmethod
    async def save(self, index: DiagramIndex) -> None: ...

    @abstractmethod
    async def replace_columns(self, index: DiagramIndex) -> None: ...


class IndexUnitOfWork(UnitOfWork):
    indexes: IndexRepository
    columns: ColumnRepository
