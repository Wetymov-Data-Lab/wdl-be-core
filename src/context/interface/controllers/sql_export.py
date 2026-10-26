from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from context.infrastructure.guards.authentication import get_current_user
from context.infrastructure.guards.authorization import get_authorization_service
from context.infrastructure.services.authorization import AuthorizationService
from context.infrastructure.services.sql_export import generate_postgresql_sql, load_sql_diagram
from infrastructure.database.dependencies import get_database_session

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
    session: Annotated[AsyncSession, Depends(get_database_session)],
    authorization: Annotated[AuthorizationService, Depends(get_authorization_service)],
) -> Response:
    database = await authorization.require_database(database_id)
    diagram = await load_sql_diagram(session, database)
    sql = generate_postgresql_sql(diagram)
    return Response(
        content=sql,
        media_type="application/sql; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="wdl-{database_id}.sql"',
            "Cache-Control": "no-store",
        },
    )
