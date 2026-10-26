from abc import abstractmethod
from uuid import UUID

from common.mixins.base_repository import Repository
from common.unit_of_work import UnitOfWork
from context.domain.entities.group import DiagramGroup, GroupName


class GroupRepository(Repository[DiagramGroup, UUID]):
    @abstractmethod
    async def list(self, database_id: UUID) -> list[DiagramGroup]: ...

    @abstractmethod
    async def database_exists(self, database_id: UUID) -> bool: ...

    @abstractmethod
    async def tables_belong_to_database(
        self, table_ids: tuple[UUID, ...], database_id: UUID
    ) -> bool: ...

    @abstractmethod
    async def exists_by_name(
        self, database_id: UUID, name: GroupName, *, exclude_id: UUID | None = None
    ) -> bool: ...

    @abstractmethod
    async def save(self, group: DiagramGroup) -> None: ...


class GroupUnitOfWork(UnitOfWork):
    groups: GroupRepository
