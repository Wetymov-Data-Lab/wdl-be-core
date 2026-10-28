from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from wdl_shared.schemas.engine.models.projects import (
    ProjectCreateModel,
    ProjectResponseModel,
    ProjectUpdateModel,
)

from common.services.identity import CurrentUser
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
from context.infrastructure.guards.authentication import get_current_user
from context.infrastructure.guards.authorization import get_authorization_service
from context.infrastructure.repositories.dependencies import get_realm_uow
from context.infrastructure.repositories.unit_of_work import SQLAlchemyUnitOfWork
from context.infrastructure.services.authorization import AuthorizationService

router = APIRouter(prefix="/projects", tags=["projects"], dependencies=[Depends(get_current_user)])
ProjectUow = Annotated[SQLAlchemyUnitOfWork, Depends(get_realm_uow)]
AuthenticatedUser = Annotated[CurrentUser, Depends(get_current_user)]
Authorization = Annotated[AuthorizationService, Depends(get_authorization_service)]


@router.get("/", response_model=list[ProjectResponseModel])
async def list_projects(
    uow: ProjectUow,
    user: AuthenticatedUser,
    realm_id: UUID | None = None,
) -> list[ProjectResponseModel]:
    projects = await ListProjects(uow).execute(
        ListProjectsRequest(account_id=user.account_id, realm_id=realm_id)
    )
    return [ProjectResponseModel.model_validate(project) for project in projects]


@router.get("/{project_id}", response_model=ProjectResponseModel)
async def get_project(
    project_id: UUID, uow: ProjectUow, authorization: Authorization
) -> ProjectResponseModel:
    project = await GetProject(uow, authorization).execute(project_id)
    return ProjectResponseModel.model_validate(project)


@router.post(
    "/",
    response_model=ProjectResponseModel,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    request: Request,
    body: ProjectCreateModel,
    uow: ProjectUow,
    user: AuthenticatedUser,
    authorization: Authorization,
) -> ProjectResponseModel:
    project = await CreateProject(uow, authorization).execute(
        CreateProjectRequest(
            name=body.name,
            notice=body.notice,
            realm_id=body.realm_id,
            author_id=user.account_id,
        )
    )
    request.state.audit_resource_id = str(project.id)
    return ProjectResponseModel.model_validate(project)


@router.put("/{project_id}", response_model=ProjectResponseModel)
async def update_project(
    project_id: UUID,
    body: ProjectUpdateModel,
    uow: ProjectUow,
    authorization: Authorization,
) -> ProjectResponseModel:
    project = await UpdateProject(uow, authorization).execute(
        UpdateProjectRequest(project_id=project_id, name=body.name, notice=body.notice)
    )
    return ProjectResponseModel.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID, uow: ProjectUow, authorization: Authorization
) -> Response:
    await DeleteProject(uow, authorization).execute(project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
