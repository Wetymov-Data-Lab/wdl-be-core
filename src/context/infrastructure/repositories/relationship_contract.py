from abc import abstractmethod
from uuid import UUID

from common.mixins.base_repository import Repository
from common.unit_of_work import UnitOfWork
from context.domain.entities.relationship import Relationship
from context.infrastructure.repositories.column_contract import ColumnRepository
from context.infrastructure.repositories.table_contract import TableRepository


class RelationshipRepository(Repository[Relationship, UUID]):
    """Relationship rows and their column mappings.

    `add` stores only the relationship row and `add_columns` its mappings, so the
    caller can flush between them and report name and mapping conflicts apart.
    """

    @abstractmethod
    async def list(self, database_id: UUID) -> list[Relationship]: ...

    @abstractmethod
    async def add_columns(self, relationship: Relationship) -> None: ...

    @abstractmethod
    async def save(self, relationship: Relationship) -> None: ...

    @abstractmethod
    async def replace_columns(self, relationship: Relationship) -> None: ...


class RelationshipUnitOfWork(UnitOfWork):
    relationships: RelationshipRepository
    tables: TableRepository
    columns: ColumnRepository
