from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from wdl_shared.schemas.engine.models.database import (
    ColumnCreateModel,
    ColumnResponseModel,
    ColumnUpdateModel,
    DatabaseCreateModel,
    DatabaseResponseModel,
    DatabaseUpdateModel,
    TableCreateModel,
    TableResponseModel,
    TableUpdateModel,
)

from wdl_be_core.application.authorization import AuthorizationService
from wdl_be_core.application.identity import CurrentUser
from wdl_be_core.infrastructure.database.models.database import Columns, Databases, Tables
from wdl_be_core.presentation.api.dependencies.authentication import get_current_user
from wdl_be_core.presentation.api.dependencies.authorization import get_authorization_service
from wdl_be_core.presentation.api.dependencies.database import get_database_session
from wdl_be_core.presentation.api.routers.crud import (
    apply_values,
    commit_or_conflict,
)

router = APIRouter(tags=["database schema"], dependencies=[Depends(get_current_user)])
DatabaseSession = Annotated[AsyncSession, Depends(get_database_session)]
AuthenticatedUser = Annotated[CurrentUser, Depends(get_current_user)]
Authorization = Annotated[AuthorizationService, Depends(get_authorization_service)]


@router.get("/databases/", response_model=list[DatabaseResponseModel])
async def list_databases(
    session: DatabaseSession,
    authorization: Authorization,
    project_id: UUID | None = None,
) -> list[DatabaseResponseModel]:
    query = authorization.databases(project_id).order_by(Databases.created_at)
    databases = (await session.scalars(query)).all()
    return [DatabaseResponseModel.model_validate(database) for database in databases]


@router.get("/databases/{database_id}", response_model=DatabaseResponseModel)
async def get_database(database_id: UUID, authorization: Authorization) -> DatabaseResponseModel:
    database = await authorization.require_database(database_id)
    return DatabaseResponseModel.model_validate(database)


@router.post(
    "/databases/",
    response_model=DatabaseResponseModel,
    status_code=status.HTTP_201_CREATED,
)
async def create_database(
    request: Request,
    body: DatabaseCreateModel,
    session: DatabaseSession,
    user: AuthenticatedUser,
    authorization: Authorization,
) -> DatabaseResponseModel:
    await authorization.require_project(body.project_id)
    database = Databases(
        id=uuid4(),
        author_id=user.account_id,
        **body.model_dump(exclude={"author_id"}),
    )
    session.add(database)
    await commit_or_conflict(session, f"Database '{body.name}' already exists in this project")
    await session.refresh(database)
    request.state.audit_resource_id = str(database.id)
    return DatabaseResponseModel.model_validate(database)


@router.put("/databases/{database_id}", response_model=DatabaseResponseModel)
async def update_database(
    database_id: UUID,
    body: DatabaseUpdateModel,
    session: DatabaseSession,
    authorization: Authorization,
) -> DatabaseResponseModel:
    database = await authorization.require_database(database_id)
    apply_values(database, body.model_dump())
    await commit_or_conflict(session, f"Database '{body.name}' already exists in this project")
    await session.refresh(database)
    return DatabaseResponseModel.model_validate(database)


@router.delete("/databases/{database_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_database(
    database_id: UUID, session: DatabaseSession, authorization: Authorization
) -> Response:
    database = await authorization.require_database(database_id)
    await session.delete(database)
    await session.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/tables/", response_model=list[TableResponseModel])
async def list_tables(
    database_id: UUID,
    session: DatabaseSession,
    authorization: Authorization,
) -> list[TableResponseModel]:
    await authorization.require_database(database_id)
    tables = (
        await session.scalars(
            select(Tables)
            .where(Tables.database_id == database_id)
            .order_by(Tables.sort_order, Tables.created_at)
        )
    ).all()
    return [TableResponseModel.model_validate(table) for table in tables]


@router.get("/tables/{table_id}", response_model=TableResponseModel)
async def get_table(table_id: UUID, authorization: Authorization) -> TableResponseModel:
    table = await authorization.require_table(table_id)
    return TableResponseModel.model_validate(table)


@router.post("/tables/", response_model=TableResponseModel, status_code=status.HTTP_201_CREATED)
async def create_table(
    request: Request,
    body: TableCreateModel,
    session: DatabaseSession,
    user: AuthenticatedUser,
    authorization: Authorization,
) -> TableResponseModel:
    await authorization.require_database(body.database_id)
    values = body.model_dump(exclude={"position", "author_id"})
    table = Tables(id=uuid4(), author_id=user.account_id, **values)
    table.position = body.position
    session.add(table)
    await commit_or_conflict(session, f"Table '{body.name}' already exists in this database")
    await session.refresh(table)
    request.state.audit_resource_id = str(table.id)
    return TableResponseModel.model_validate(table)


@router.put("/tables/{table_id}", response_model=TableResponseModel)
async def update_table(
    table_id: UUID,
    body: TableUpdateModel,
    session: DatabaseSession,
    authorization: Authorization,
) -> TableResponseModel:
    table = await authorization.require_table(table_id)
    apply_values(table, body.model_dump(exclude={"position"}))
    table.position = body.position
    await commit_or_conflict(session, f"Table '{body.name}' already exists in this database")
    await session.refresh(table)
    return TableResponseModel.model_validate(table)


@router.delete("/tables/{table_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_table(
    table_id: UUID, session: DatabaseSession, authorization: Authorization
) -> Response:
    table = await authorization.require_table(table_id)
    await session.delete(table)
    await session.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/columns/", response_model=list[ColumnResponseModel])
async def list_columns(
    table_id: UUID, session: DatabaseSession, authorization: Authorization
) -> list[ColumnResponseModel]:
    await authorization.require_table(table_id)
    columns = (
        await session.scalars(
            select(Columns)
            .where(Columns.table_id == table_id)
            .order_by(Columns.sort_order, Columns.created_at)
        )
    ).all()
    return [ColumnResponseModel.model_validate(column) for column in columns]


@router.get("/columns/{column_id}", response_model=ColumnResponseModel)
async def get_column(column_id: UUID, authorization: Authorization) -> ColumnResponseModel:
    column = await authorization.require_column(column_id)
    return ColumnResponseModel.model_validate(column)


@router.post(
    "/columns/",
    response_model=ColumnResponseModel,
    status_code=status.HTTP_201_CREATED,
)
async def create_column(
    request: Request,
    body: ColumnCreateModel,
    session: DatabaseSession,
    user: AuthenticatedUser,
    authorization: Authorization,
) -> ColumnResponseModel:
    await authorization.require_table(body.table_id)
    column = Columns(
        id=uuid4(),
        author_id=user.account_id,
        **body.model_dump(exclude={"author_id"}),
    )
    session.add(column)
    await commit_or_conflict(session, f"Column '{body.name}' already exists in this table")
    await session.refresh(column)
    request.state.audit_resource_id = str(column.id)
    return ColumnResponseModel.model_validate(column)


@router.put("/columns/{column_id}", response_model=ColumnResponseModel)
async def update_column(
    request: Request,
    column_id: UUID,
    body: ColumnUpdateModel,
    session: DatabaseSession,
    authorization: Authorization,
) -> ColumnResponseModel:
    column = await authorization.require_column(column_id)
    apply_values(column, body.model_dump())
    await commit_or_conflict(session, f"Column '{body.name}' already exists in this table")
    await session.refresh(column)
    request.state.audit_resource_id = str(column.id)
    return ColumnResponseModel.model_validate(column)


@router.delete("/columns/{column_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_column(
    column_id: UUID, session: DatabaseSession, authorization: Authorization
) -> Response:
    column = await authorization.require_column(column_id)
    await session.delete(column)
    await session.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
