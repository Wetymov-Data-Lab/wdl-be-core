from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from common.exceptions.exceptions import EntityNotFoundError
from common.unit_of_work import commit_or_conflict
from context.application.use_case import UseCase
from context.domain.entities.project import Project
from context.infrastructure.repositories.project_contract import ProjectUnitOfWork
from context.infrastructure.services.authorization import AuthorizationService


@dataclass(frozen=True, slots=True)
class ListProjectsRequest:
    account_id: UUID
    realm_id: UUID | None


@dataclass(frozen=True, slots=True)
class CreateProjectRequest:
    name: str
    notice: str | None
    realm_id: UUID
    author_id: UUID


@dataclass(frozen=True, slots=True)
class UpdateProjectRequest:
    project_id: UUID
    name: str
    notice: str | None


class ListProjects(UseCase[ListProjectsRequest, list[Project]]):
    def __init__(self, uow: ProjectUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, request: ListProjectsRequest) -> list[Project]:
        async with self._uow:
            return await self._uow.projects.list_accessible(request.account_id, request.realm_id)


class GetProject(UseCase[UUID, Project]):
    def __init__(self, uow: ProjectUnitOfWork, authorization: AuthorizationService) -> None:
        self._uow = uow
        self._authorization = authorization

    async def execute(self, request: UUID) -> Project:
        await self._authorization.require_project(request)
        async with self._uow:
            return await get_project(self._uow, request)


class CreateProject(UseCase[CreateProjectRequest, Project]):
    def __init__(self, uow: ProjectUnitOfWork, authorization: AuthorizationService) -> None:
        self._uow = uow
        self._authorization = authorization

    async def execute(self, request: CreateProjectRequest) -> Project:
        await self._authorization.require_realm(request.realm_id)
        async with self._uow:
            project = Project.create(
                name=request.name,
                notice=request.notice,
                realm_id=request.realm_id,
                author_id=request.author_id,
                created_at=datetime.now(UTC),
            )
            await self._uow.projects.add(project)
            await commit_or_conflict(
                self._uow, f"Project '{request.name}' already exists in this realm"
            )
            return project


class UpdateProject(UseCase[UpdateProjectRequest, Project]):
    def __init__(self, uow: ProjectUnitOfWork, authorization: AuthorizationService) -> None:
        self._uow = uow
        self._authorization = authorization

    async def execute(self, request: UpdateProjectRequest) -> Project:
        await self._authorization.require_project(request.project_id)
        async with self._uow:
            project = await get_project(self._uow, request.project_id)
            project.update(name=request.name, notice=request.notice, updated_at=datetime.now(UTC))
            await self._uow.projects.save(project)
            await commit_or_conflict(
                self._uow, f"Project '{request.name}' already exists in this realm"
            )
            return project


class DeleteProject(UseCase[UUID, None]):
    def __init__(self, uow: ProjectUnitOfWork, authorization: AuthorizationService) -> None:
        self._uow = uow
        self._authorization = authorization

    async def execute(self, request: UUID) -> None:
        await self._authorization.require_project(request)
        async with self._uow:
            project = await get_project(self._uow, request)
            await self._uow.projects.remove(project)
            await self._uow.commit()


async def get_project(uow: ProjectUnitOfWork, project_id: UUID) -> Project:
    project = await uow.projects.get(project_id)
    if project is None:
        raise EntityNotFoundError(f"Project {project_id} was not found")
    return project
