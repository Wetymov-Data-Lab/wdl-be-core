from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Response, status
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

from wdl_be_core.infrastructure.database.models.database import Columns, Databases, Tables
from wdl_be_core.infrastructure.database.models.projects import Projects
from wdl_be_core.presentation.api.dependencies.database import get_database_session
from wdl_be_core.presentation.api.routers.crud import (
    apply_values,
    commit_or_conflict,
    get_or_404,
)

router = APIRouter(tags=["database schema"])
DatabaseSession = Annotated[AsyncSession, Depends(get_database_session)]


@router.get("/databases/", response_model=list[DatabaseResponseModel])
async def list_databases(
    session: DatabaseSession,
    project_id: UUID | None = None,
) -> list[DatabaseResponseModel]:
    query = select(Databases).order_by(Databases.created_at)
    if project_id is not None:
        query = query.where(Databases.project_id == project_id)
    databases = (await session.scalars(query)).all()
    return [DatabaseResponseModel.model_validate(database) for database in databases]


@router.get("/databases/{database_id}", response_model=DatabaseResponseModel)
async def get_database(database_id: UUID, session: DatabaseSession) -> DatabaseResponseModel:
    database = await get_or_404(session, Databases, database_id)
    return DatabaseResponseModel.model_validate(database)


@router.post(
    "/databases/",
    response_model=DatabaseResponseModel,
    status_code=status.HTTP_201_CREATED,
)
async def create_database(
    body: DatabaseCreateModel,
    session: DatabaseSession,
) -> DatabaseResponseModel:
    await get_or_404(session, Projects, body.project_id)
    database = Databases(id=uuid4(), **body.model_dump())
    session.add(database)
    await commit_or_conflict(session, f"Database '{body.name}' already exists in this project")
    await session.refresh(database)
    return DatabaseResponseModel.model_validate(database)


@router.put("/databases/{database_id}", response_model=DatabaseResponseModel)
async def update_database(
    database_id: UUID,
    body: DatabaseUpdateModel,
    session: DatabaseSession,
) -> DatabaseResponseModel:
    database = await get_or_404(session, Databases, database_id)
    apply_values(database, body.model_dump())
    await commit_or_conflict(session, f"Database '{body.name}' already exists in this project")
    await session.refresh(database)
    return DatabaseResponseModel.model_validate(database)


@router.delete("/databases/{database_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_database(database_id: UUID, session: DatabaseSession) -> Response:
    database = await get_or_404(session, Databases, database_id)
    await session.delete(database)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/tables/", response_model=list[TableResponseModel])
async def list_tables(
    database_id: UUID,
    session: DatabaseSession,
) -> list[TableResponseModel]:
    tables = (
        await session.scalars(
            select(Tables)
            .where(Tables.database_id == database_id)
            .order_by(Tables.sort_order, Tables.created_at)
        )
    ).all()
    return [TableResponseModel.model_validate(table) for table in tables]


@router.get("/tables/{table_id}", response_model=TableResponseModel)
async def get_table(table_id: UUID, session: DatabaseSession) -> TableResponseModel:
    table = await get_or_404(session, Tables, table_id)
    return TableResponseModel.model_validate(table)


@router.post("/tables/", response_model=TableResponseModel, status_code=status.HTTP_201_CREATED)
async def create_table(body: TableCreateModel, session: DatabaseSession) -> TableResponseModel:
    await get_or_404(session, Databases, body.database_id)
    values = body.model_dump(exclude={"position"})
    table  = Tables(id=uuid4(), **values)
    table.position = body.position
    session.add(table)
    await commit_or_conflict(session, f"Table '{body.name}' already exists in this database")
    await session.refresh(table)
    return TableResponseModel.model_validate(table)


@router.put("/tables/{table_id}", response_model=TableResponseModel)
async def update_table(
    table_id: UUID,
    body: TableUpdateModel,
    session: DatabaseSession,
) -> TableResponseModel:
    table = await get_or_404(session, Tables, table_id)
    apply_values(table, body.model_dump(exclude={"position"}))
    table.position = body.position
    await commit_or_conflict(session, f"Table '{body.name}' already exists in this database")
    await session.refresh(table)
    return TableResponseModel.model_validate(table)


@router.delete("/tables/{table_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_table(table_id: UUID, session: DatabaseSession) -> Response:
    table = await get_or_404(session, Tables, table_id)
    await session.delete(table)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/columns/", response_model=list[ColumnResponseModel])
async def list_columns(table_id: UUID, session: DatabaseSession) -> list[ColumnResponseModel]:
    columns = (
        await session.scalars(
            select(Columns)
            .where(Columns.table_id == table_id)
            .order_by(Columns.sort_order, Columns.created_at)
        )
    ).all()
    return [ColumnResponseModel.model_validate(column) for column in columns]


@router.get("/columns/{column_id}", response_model=ColumnResponseModel)
async def get_column(column_id: UUID, session: DatabaseSession) -> ColumnResponseModel:
    column = await get_or_404(session, Columns, column_id)
    return ColumnResponseModel.model_validate(column)


@router.post(
    "/columns/",
    response_model=ColumnResponseModel,
    status_code=status.HTTP_201_CREATED,
)
async def create_column(
    body: ColumnCreateModel,
    session: DatabaseSession,
) -> ColumnResponseModel:
    await get_or_404(session, Tables, body.table_id)
    column = Columns(id=uuid4(), **body.model_dump())
    session.add(column)
    await commit_or_conflict(session, f"Column '{body.name}' already exists in this table")
    await session.refresh(column)
    return ColumnResponseModel.model_validate(column)


@router.put("/columns/{column_id}", response_model=ColumnResponseModel)
async def update_column(
    column_id: UUID,
    body: ColumnUpdateModel,
    session: DatabaseSession,
) -> ColumnResponseModel:
    column = await get_or_404(session, Columns, column_id)
    apply_values(column, body.model_dump())
    await commit_or_conflict(session, f"Column '{body.name}' already exists in this table")
    await session.refresh(column)
    return ColumnResponseModel.model_validate(column)


@router.delete("/columns/{column_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_column(column_id: UUID, session: DatabaseSession) -> Response:
    column = await get_or_404(session, Columns, column_id)
    await session.delete(column)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
