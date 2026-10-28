from uuid import UUID

from context.application.services.database import get_database
from context.application.use_case import UseCase
from context.domain.services.sql_export import SqlDiagram, generate_postgresql_sql
from context.infrastructure.repositories.sql_export_contract import SqlExportUnitOfWork
from context.infrastructure.services.authorization import AuthorizationService


class ExportDatabaseSql(UseCase[UUID, str]):
    def __init__(self, uow: SqlExportUnitOfWork, authorization: AuthorizationService) -> None:
        self._uow = uow
        self._authorization = authorization

    async def execute(self, request: UUID) -> str:
        # Children are read only after the database itself is authorized.
        await self._authorization.require_database(request)
        async with self._uow:
            diagram = SqlDiagram(
                database=await get_database(self._uow, request),
                tables=tuple(await self._uow.tables.list(request)),
                columns=tuple(await self._uow.columns.list_by_database(request)),
                indexes=tuple(await self._uow.indexes.list_by_database(request)),
                relationships=tuple(await self._uow.relationships.list(request)),
            )
        return generate_postgresql_sql(diagram)
