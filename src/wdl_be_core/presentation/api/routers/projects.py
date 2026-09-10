from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from wdl_shared.schemas.engine.models.projects import (
    ProjectCreateModel,
    ProjectResponseModel,
    ProjectUpdateModel,
)

from wdl_be_core.application.authorization import AuthorizationService
from wdl_be_core.application.identity import CurrentUser
from wdl_be_core.infrastructure.database.models.projects import Projects
from wdl_be_core.presentation.api.dependencies.authentication import get_current_user
from wdl_be_core.presentation.api.dependencies.authorization import get_authorization_service
from wdl_be_core.presentation.api.dependencies.database import get_database_session
from wdl_be_core.presentation.api.routers.crud import (
    apply_values,
    commit_or_conflict,
)

router = APIRouter(prefix="/projects", tags=["projects"], dependencies=[Depends(get_current_user)])
DatabaseSession = Annotated[AsyncSession, Depends(get_database_session)]
AuthenticatedUser = Annotated[CurrentUser, Depends(get_current_user)]
Authorization = Annotated[AuthorizationService, Depends(get_authorization_service)]


@router.get("/", response_model=list[ProjectResponseModel])
async def list_projects(
    session: DatabaseSession,
    authorization: Authorization,
    realm_id: UUID | None = None,
) -> list[ProjectResponseModel]:
    query = authorization.projects(realm_id).order_by(Projects.created_at)
    projects = (await session.scalars(query)).all()
    return [ProjectResponseModel.model_validate(project) for project in projects]


@router.get("/{project_id}", response_model=ProjectResponseModel)
async def get_project(project_id: UUID, authorization: Authorization) -> ProjectResponseModel:
    project = await authorization.require_project(project_id)
    return ProjectResponseModel.model_validate(project)


@router.post(
    "/",
    response_model=ProjectResponseModel,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    request: Request,
    body: ProjectCreateModel,
    session: DatabaseSession,
    user: AuthenticatedUser,
    authorization: Authorization,
) -> ProjectResponseModel:
    await authorization.require_realm(body.realm_id)
    project = Projects(
        id=uuid4(),
        author_id=user.account_id,
        **body.model_dump(exclude={"author_id"}),
    )
    session.add(project)
    await commit_or_conflict(session, f"Project '{body.name}' already exists in this realm")
    await session.refresh(project)
    request.state.audit_resource_id = str(project.id)
    return ProjectResponseModel.model_validate(project)


@router.put("/{project_id}", response_model=ProjectResponseModel)
async def update_project(
    project_id: UUID,
    body: ProjectUpdateModel,
    session: DatabaseSession,
    authorization: Authorization,
) -> ProjectResponseModel:
    project = await authorization.require_project(project_id)
    apply_values(project, body.model_dump())
    await commit_or_conflict(session, f"Project '{body.name}' already exists in this realm")
    await session.refresh(project)
    return ProjectResponseModel.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID, session: DatabaseSession, authorization: Authorization
) -> Response:
    project = await authorization.require_project(project_id)
    await session.delete(project)
    await session.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
