from abc import abstractmethod
from uuid import UUID

from wdl_be_core.application.repositories import Repository
from wdl_be_core.application.unit_of_work import UnitOfWork
from wdl_be_core.domain.entities.group import DiagramGroup, GroupName


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
