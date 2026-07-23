from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from wdl_shared.schemas.engine.models.projects import (
    ProjectCreateModel,
    ProjectResponseModel,
    ProjectUpdateModel,
)

from wdl_be_core.infrastructure.database.models.projects import Projects
from wdl_be_core.infrastructure.database.models.realms import RealmSchema
from wdl_be_core.presentation.api.dependencies.database import get_database_session
from wdl_be_core.presentation.api.routers.crud import (
    apply_values,
    commit_or_conflict,
    get_or_404,
)

router = APIRouter(prefix="/projects", tags=["projects"])
DatabaseSession = Annotated[AsyncSession, Depends(get_database_session)]


@router.get("/", response_model=list[ProjectResponseModel])
async def list_projects(
    session: DatabaseSession,
    realm_id: UUID | None = None,
) -> list[ProjectResponseModel]:
    query = select(Projects).order_by(Projects.created_at)
    if realm_id is not None:
        query = query.where(Projects.realm_id == realm_id)
    projects = (await session.scalars(query)).all()
    return [ProjectResponseModel.model_validate(project) for project in projects]


@router.get("/{project_id}", response_model=ProjectResponseModel)
async def get_project(project_id: UUID, session: DatabaseSession) -> ProjectResponseModel:
    project = await get_or_404(session, Projects, project_id)
    return ProjectResponseModel.model_validate(project)


@router.post(
    "/",
    response_model=ProjectResponseModel,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    body: ProjectCreateModel,
    session: DatabaseSession,
) -> ProjectResponseModel:
    await get_or_404(session, RealmSchema, body.realm_id)
    project = Projects(id=uuid4(), **body.model_dump())
    session.add(project)
    await commit_or_conflict(session, f"Project '{body.name}' already exists in this realm")
    await session.refresh(project)
    return ProjectResponseModel.model_validate(project)


@router.put("/{project_id}", response_model=ProjectResponseModel)
async def update_project(
    project_id: UUID,
    body: ProjectUpdateModel,
    session: DatabaseSession,
) -> ProjectResponseModel:
    project = await get_or_404(session, Projects, project_id)
    apply_values(project, body.model_dump())
    await commit_or_conflict(session, f"Project '{body.name}' already exists in this realm")
    await session.refresh(project)
    return ProjectResponseModel.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: UUID, session: DatabaseSession) -> Response:
    project = await get_or_404(session, Projects, project_id)
    await session.delete(project)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
