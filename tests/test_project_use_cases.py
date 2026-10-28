from types import TracebackType
from typing import cast
from uuid import UUID, uuid4

import pytest

from common.exceptions.exceptions import EntityAlreadyExistsError, EntityNotFoundError
from context.application.services.project import (
    CreateProject,
    CreateProjectRequest,
    DeleteProject,
    GetProject,
    ListProjects,
    ListProjectsRequest,
    UpdateProject,
    UpdateProjectRequest,
)
from context.domain.entities.project import Project
from context.infrastructure.repositories.project_contract import (
    ProjectRepository,
    ProjectUnitOfWork,
)
from context.infrastructure.services.authorization import AuthorizationService


class FakeProjectRepository(ProjectRepository):
    def __init__(self) -> None:
        self.items: dict[UUID, Project] = {}

    async def get(self, entity_id: UUID) -> Project | None:
        return self.items.get(entity_id)

    async def list_accessible(
        self, account_id: UUID, realm_id: UUID | None = None
    ) -> list[Project]:
        return [
            project
            for project in self.items.values()
            if realm_id is None or project.realm_id == realm_id
        ]

    async def add(self, entity: Project) -> None:
        self.items[entity.id] = entity

    async def save(self, project: Project) -> None:
        self.items[project.id] = project

    async def remove(self, entity: Project) -> None:
        del self.items[entity.id]


class FakeProjectUnitOfWork(ProjectUnitOfWork):
    def __init__(self) -> None:
        self.projects = FakeProjectRepository()
        self.commits = 0
        self.conflict = False

    async def commit(self) -> None:
        if self.conflict:
            raise EntityAlreadyExistsError("Entity violates a uniqueness constraint")
        self.commits += 1

    async def rollback(self) -> None:
        return None

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None


class FakeAuthorization:
    def __init__(self) -> None:
        self.denied: set[UUID] = set()
        self.checked: list[UUID] = []

    async def require_realm(self, realm_id: UUID) -> None:
        self._require("Realm", realm_id)

    async def require_project(self, project_id: UUID) -> None:
        self._require("Project", project_id)

    def _require(self, kind: str, resource_id: UUID) -> None:
        self.checked.append(resource_id)
        if resource_id in self.denied:
            raise EntityNotFoundError(f"{kind} {resource_id} was not found")


def authorization(fake: FakeAuthorization) -> AuthorizationService:
    return cast(AuthorizationService, fake)


async def test_create_get_update_list_delete_project() -> None:
    uow = FakeProjectUnitOfWork()
    access = FakeAuthorization()
    realm_id = uuid4()
    author_id = uuid4()

    created = await CreateProject(uow, authorization(access)).execute(
        CreateProjectRequest(name="Main", notice=None, realm_id=realm_id, author_id=author_id)
    )
    assert created.author_id == author_id
    assert access.checked == [realm_id]
    assert await GetProject(uow, authorization(access)).execute(created.id) == created

    updated = await UpdateProject(uow, authorization(access)).execute(
        UpdateProjectRequest(project_id=created.id, name="Renamed", notice="Note")
    )
    assert (updated.name, updated.notice) == ("Renamed", "Note")
    assert updated.updated_at is not None

    listed = await ListProjects(uow).execute(
        ListProjectsRequest(account_id=author_id, realm_id=realm_id)
    )
    assert listed == [created]

    await DeleteProject(uow, authorization(access)).execute(created.id)
    assert uow.projects.items == {}
    assert uow.commits == 3


async def test_create_project_requires_realm_access() -> None:
    uow = FakeProjectUnitOfWork()
    access = FakeAuthorization()
    realm_id = uuid4()
    access.denied.add(realm_id)

    with pytest.raises(EntityNotFoundError):
        await CreateProject(uow, authorization(access)).execute(
            CreateProjectRequest(name="Main", notice=None, realm_id=realm_id, author_id=uuid4())
        )
    assert uow.projects.items == {}


async def test_project_access_is_checked_before_loading() -> None:
    uow = FakeProjectUnitOfWork()
    access = FakeAuthorization()
    project_id = uuid4()
    access.denied.add(project_id)

    for use_case in (GetProject, DeleteProject):
        with pytest.raises(EntityNotFoundError, match="Project"):
            await use_case(uow, authorization(access)).execute(project_id)


async def test_create_project_reports_name_conflict() -> None:
    uow = FakeProjectUnitOfWork()
    uow.conflict = True

    with pytest.raises(EntityAlreadyExistsError, match="Project 'Main' already exists"):
        await CreateProject(uow, authorization(FakeAuthorization())).execute(
            CreateProjectRequest(name="Main", notice=None, realm_id=uuid4(), author_id=uuid4())
        )
