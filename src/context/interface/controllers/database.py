from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
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

from common.services.identity import CurrentUser
from context.application.services.column import (
    CreateColumn,
    CreateColumnRequest,
    DeleteColumn,
    GetColumn,
    ListColumns,
    UpdateColumn,
    UpdateColumnRequest,
)
from context.application.services.database import (
    CreateDatabase,
    CreateDatabaseRequest,
    DeleteDatabase,
    GetDatabase,
    ListDatabases,
    ListDatabasesRequest,
    UpdateDatabase,
    UpdateDatabaseRequest,
)
from context.application.services.table import (
    CreateTable,
    CreateTableRequest,
    DeleteTable,
    GetTable,
    ListTables,
    UpdateTable,
    UpdateTableRequest,
)
from context.domain.entities.column import ColumnAttributes
from context.domain.entities.database import DatabaseAttributes
from context.domain.entities.table import TableAttributes
from context.infrastructure.guards.authentication import get_current_user
from context.infrastructure.guards.authorization import get_authorization_service
from context.infrastructure.repositories.dependencies import get_realm_uow
from context.infrastructure.repositories.unit_of_work import SQLAlchemyUnitOfWork
from context.infrastructure.services.authorization import AuthorizationService

router = APIRouter(tags=["database schema"], dependencies=[Depends(get_current_user)])
SchemaUow = Annotated[SQLAlchemyUnitOfWork, Depends(get_realm_uow)]
AuthenticatedUser = Annotated[CurrentUser, Depends(get_current_user)]
Authorization = Annotated[AuthorizationService, Depends(get_authorization_service)]


def database_attributes(body: DatabaseCreateModel | DatabaseUpdateModel) -> DatabaseAttributes:
    return DatabaseAttributes(
        name=body.name,
        type=body.type,
        notice=body.notice,
        default_schema=body.default_schema,
        charset=body.charset,
        collation=body.collation,
    )


def table_attributes(body: TableCreateModel | TableUpdateModel) -> TableAttributes:
    return TableAttributes(
        name=body.name,
        schema_name=body.schema_name,
        description=body.description,
        notice=body.notice,
        color=body.color,
        position=body.position,
        width=body.width,
        is_collapsed=body.is_collapsed,
        sort_order=body.sort_order,
    )


def column_attributes(body: ColumnCreateModel | ColumnUpdateModel) -> ColumnAttributes:
    return ColumnAttributes(
        name=body.name,
        type=body.type,
        custom_type=body.custom_type,
        length=body.length,
        precision=body.precision,
        scale=body.scale,
        array_dimensions=body.array_dimensions,
        nullable=body.nullable,
        primary_key=body.primary_key,
        unique=body.unique,
        auto_increment=body.auto_increment,
        unsigned=body.unsigned,
        default=body.default,
        check=body.check,
        enum_values=list(body.enum_values),
        sort_order=body.sort_order,
        notice=body.notice,
    )


@router.get("/databases/", response_model=list[DatabaseResponseModel])
async def list_databases(
    uow: SchemaUow,
    user: AuthenticatedUser,
    project_id: UUID | None = None,
) -> list[DatabaseResponseModel]:
    databases = await ListDatabases(uow).execute(
        ListDatabasesRequest(account_id=user.account_id, project_id=project_id)
    )
    return [DatabaseResponseModel.model_validate(database) for database in databases]


@router.get("/databases/{database_id}", response_model=DatabaseResponseModel)
async def get_database(
    database_id: UUID, uow: SchemaUow, authorization: Authorization
) -> DatabaseResponseModel:
    database = await GetDatabase(uow, authorization).execute(database_id)
    return DatabaseResponseModel.model_validate(database)


@router.post(
    "/databases/",
    response_model=DatabaseResponseModel,
    status_code=status.HTTP_201_CREATED,
)
async def create_database(
    request: Request,
    body: DatabaseCreateModel,
    uow: SchemaUow,
    user: AuthenticatedUser,
    authorization: Authorization,
) -> DatabaseResponseModel:
    database = await CreateDatabase(uow, authorization).execute(
        CreateDatabaseRequest(
            project_id=body.project_id,
            attributes=database_attributes(body),
            author_id=user.account_id,
        )
    )
    request.state.audit_resource_id = str(database.id)
    return DatabaseResponseModel.model_validate(database)


@router.put("/databases/{database_id}", response_model=DatabaseResponseModel)
async def update_database(
    database_id: UUID,
    body: DatabaseUpdateModel,
    uow: SchemaUow,
    authorization: Authorization,
) -> DatabaseResponseModel:
    database = await UpdateDatabase(uow, authorization).execute(
        UpdateDatabaseRequest(database_id=database_id, attributes=database_attributes(body))
    )
    return DatabaseResponseModel.model_validate(database)


@router.delete("/databases/{database_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_database(
    database_id: UUID, uow: SchemaUow, authorization: Authorization
) -> Response:
    await DeleteDatabase(uow, authorization).execute(database_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/tables/", response_model=list[TableResponseModel])
async def list_tables(
    database_id: UUID,
    uow: SchemaUow,
    authorization: Authorization,
) -> list[TableResponseModel]:
    tables = await ListTables(uow, authorization).execute(database_id)
    return [TableResponseModel.model_validate(table) for table in tables]


@router.get("/tables/{table_id}", response_model=TableResponseModel)
async def get_table(
    table_id: UUID, uow: SchemaUow, authorization: Authorization
) -> TableResponseModel:
    table = await GetTable(uow, authorization).execute(table_id)
    return TableResponseModel.model_validate(table)


@router.post("/tables/", response_model=TableResponseModel, status_code=status.HTTP_201_CREATED)
async def create_table(
    request: Request,
    body: TableCreateModel,
    uow: SchemaUow,
    user: AuthenticatedUser,
    authorization: Authorization,
) -> TableResponseModel:
    table = await CreateTable(uow, authorization).execute(
        CreateTableRequest(
            database_id=body.database_id,
            attributes=table_attributes(body),
            author_id=user.account_id,
        )
    )
    request.state.audit_resource_id = str(table.id)
    return TableResponseModel.model_validate(table)


@router.put("/tables/{table_id}", response_model=TableResponseModel)
async def update_table(
    table_id: UUID,
    body: TableUpdateModel,
    uow: SchemaUow,
    authorization: Authorization,
) -> TableResponseModel:
    table = await UpdateTable(uow, authorization).execute(
        UpdateTableRequest(table_id=table_id, attributes=table_attributes(body))
    )
    return TableResponseModel.model_validate(table)


@router.delete("/tables/{table_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_table(table_id: UUID, uow: SchemaUow, authorization: Authorization) -> Response:
    await DeleteTable(uow, authorization).execute(table_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/columns/", response_model=list[ColumnResponseModel])
async def list_columns(
    table_id: UUID, uow: SchemaUow, authorization: Authorization
) -> list[ColumnResponseModel]:
    columns = await ListColumns(uow, authorization).execute(table_id)
    return [ColumnResponseModel.model_validate(column) for column in columns]


@router.get("/columns/{column_id}", response_model=ColumnResponseModel)
async def get_column(
    column_id: UUID, uow: SchemaUow, authorization: Authorization
) -> ColumnResponseModel:
    column = await GetColumn(uow, authorization).execute(column_id)
    return ColumnResponseModel.model_validate(column)


@router.post(
    "/columns/",
    response_model=ColumnResponseModel,
    status_code=status.HTTP_201_CREATED,
)
async def create_column(
    request: Request,
    body: ColumnCreateModel,
    uow: SchemaUow,
    user: AuthenticatedUser,
    authorization: Authorization,
) -> ColumnResponseModel:
    column = await CreateColumn(uow, authorization).execute(
        CreateColumnRequest(
            table_id=body.table_id,
            attributes=column_attributes(body),
            author_id=user.account_id,
        )
    )
    request.state.audit_resource_id = str(column.id)
    return ColumnResponseModel.model_validate(column)


@router.put("/columns/{column_id}", response_model=ColumnResponseModel)
async def update_column(
    request: Request,
    column_id: UUID,
    body: ColumnUpdateModel,
    uow: SchemaUow,
    authorization: Authorization,
) -> ColumnResponseModel:
    column = await UpdateColumn(uow, authorization).execute(
        UpdateColumnRequest(column_id=column_id, attributes=column_attributes(body))
    )
    request.state.audit_resource_id = str(column.id)
    return ColumnResponseModel.model_validate(column)


@router.delete("/columns/{column_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_column(column_id: UUID, uow: SchemaUow, authorization: Authorization) -> Response:
    await DeleteColumn(uow, authorization).execute(column_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
