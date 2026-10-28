from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response

from context.application.services.sql_export import ExportDatabaseSql
from context.infrastructure.guards.authentication import get_current_user
from context.infrastructure.guards.authorization import get_authorization_service
from context.infrastructure.repositories.dependencies import get_realm_uow
from context.infrastructure.repositories.unit_of_work import SQLAlchemyUnitOfWork
from context.infrastructure.services.authorization import AuthorizationService

router = APIRouter(tags=["database schema"], dependencies=[Depends(get_current_user)])


@router.get(
    "/databases/{database_id}/export/sql",
    response_class=Response,
    responses={
        200: {"content": {"application/sql": {"schema": {"type": "string"}}}},
        422: {"description": "Unsupported dialect or invalid ER model"},
    },
)
async def export_database_sql(
    database_id: UUID,
    uow: Annotated[SQLAlchemyUnitOfWork, Depends(get_realm_uow)],
    authorization: Annotated[AuthorizationService, Depends(get_authorization_service)],
) -> Response:
    sql = await ExportDatabaseSql(uow, authorization).execute(database_id)
    return Response(
        content=sql,
        media_type="application/sql; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="wdl-{database_id}.sql"',
            "Cache-Control": "no-store",
        },
    )
