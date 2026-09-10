from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from wdl_be_core.domain.exceptions import EntityNotFoundError
from wdl_be_core.infrastructure.database.models.database import (
    Columns,
    Databases,
    DiagramIndexes,
    Relationships,
    Tables,
)
from wdl_be_core.infrastructure.database.models.projects import Projects
from wdl_be_core.infrastructure.database.models.realms import RealmSchema


class AuthorizationService:
    """Resolve resources only through a realm owned by the authenticated subject.

    Core does not have a membership model yet, so realm ownership is the only
    grant accepted here. Returning not-found for inaccessible objects prevents
    leaking cross-tenant identifiers.
    """

    def __init__(self, session: AsyncSession, account_id: UUID) -> None:
        self._session = session
        self._account_id = account_id

    def projects(self, realm_id: UUID | None = None) -> Select[tuple[Projects]]:
        query = (
            select(Projects)
            .join(RealmSchema, RealmSchema.id == Projects.realm_id)
            .where(*self._realm_access_filters())
        )
        return query if realm_id is None else query.where(Projects.realm_id == realm_id)

    def databases(self, project_id: UUID | None = None) -> Select[tuple[Databases]]:
        query = (
            select(Databases)
            .join(Projects, Projects.id == Databases.project_id)
            .join(RealmSchema, RealmSchema.id == Projects.realm_id)
            .where(*self._realm_access_filters())
        )
        return query if project_id is None else query.where(Databases.project_id == project_id)

    async def require_realm(self, realm_id: UUID) -> RealmSchema:
        return await self._require(
            select(RealmSchema).where(RealmSchema.id == realm_id, *self._realm_access_filters()),
            "Realm",
            realm_id,
        )

    async def require_project(self, project_id: UUID) -> Projects:
        return await self._require(
            select(Projects)
            .join(RealmSchema, RealmSchema.id == Projects.realm_id)
            .where(Projects.id == project_id, *self._realm_access_filters()),
            "Project",
            project_id,
        )

    async def require_database(self, database_id: UUID) -> Databases:
        return await self._require(
            self.databases().where(Databases.id == database_id), "Database", database_id
        )

    async def require_table(self, table_id: UUID) -> Tables:
        return await self._require(
            select(Tables)
            .join(Databases, Databases.id == Tables.database_id)
            .join(Projects, Projects.id == Databases.project_id)
            .join(RealmSchema, RealmSchema.id == Projects.realm_id)
            .where(Tables.id == table_id, *self._realm_access_filters()),
            "Table",
            table_id,
        )

    async def require_column(self, column_id: UUID) -> Columns:
        return await self._require(
            select(Columns)
            .join(Tables, Tables.id == Columns.table_id)
            .join(Databases, Databases.id == Tables.database_id)
            .join(Projects, Projects.id == Databases.project_id)
            .join(RealmSchema, RealmSchema.id == Projects.realm_id)
            .where(Columns.id == column_id, *self._realm_access_filters()),
            "Column",
            column_id,
        )

    async def require_index(self, index_id: UUID) -> DiagramIndexes:
        return await self._require(
            select(DiagramIndexes)
            .join(Tables, Tables.id == DiagramIndexes.table_id)
            .join(Databases, Databases.id == Tables.database_id)
            .join(Projects, Projects.id == Databases.project_id)
            .join(RealmSchema, RealmSchema.id == Projects.realm_id)
            .where(DiagramIndexes.id == index_id, *self._realm_access_filters()),
            "Diagram index",
            index_id,
        )

    async def require_relationship(self, relationship_id: UUID) -> Relationships:
        return await self._require(
            select(Relationships)
            .join(Databases, Databases.id == Relationships.database_id)
            .join(Projects, Projects.id == Databases.project_id)
            .join(RealmSchema, RealmSchema.id == Projects.realm_id)
            .where(Relationships.id == relationship_id, *self._realm_access_filters()),
            "Relationship",
            relationship_id,
        )

    def _realm_access_filters(self) -> tuple[ColumnElement[bool], ...]:
        return (
            RealmSchema.author_id == self._account_id,
            RealmSchema.status == "active",
            RealmSchema.deleted_at.is_(None),
        )

    async def _require[ResourceT](
        self,
        query: Select[tuple[ResourceT]],
        kind: str,
        resource_id: UUID,
    ) -> ResourceT:
        resource = await self._session.scalar(query)
        if resource is None:
            raise EntityNotFoundError(f"{kind} {resource_id} was not found")
        return resource
