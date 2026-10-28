from abc import abstractmethod
from uuid import UUID

from common.mixins.base_repository import Repository
from common.unit_of_work import UnitOfWork
from context.domain.entities.project import Project


class ProjectRepository(Repository[Project, UUID]):
    @abstractmethod
    async def list_accessible(
        self, account_id: UUID, realm_id: UUID | None = None
    ) -> list[Project]: ...

    @abstractmethod
    async def save(self, project: Project) -> None: ...


class ProjectUnitOfWork(UnitOfWork):
    projects: ProjectRepository
