from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from wdl_shared.schemas.engine.enums.database import DataBaseName

from context.domain.entities.database import Database
from context.infrastructure.repositories.database_contract import (
    DatabaseRepository as AbstractDatabaseRepository,
)
from context.infrastructure.schemas.database import Databases
from context.infrastructure.services.authorization import AuthorizationService


class DatabaseRepository(AbstractDatabaseRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, entity_id: UUID) -> Database | None:
        model = await self._session.get(Databases, entity_id)
        return None if model is None else self._to_domain(model)

    async def list_accessible(
        self, account_id: UUID, project_id: UUID | None = None
    ) -> list[Database]:
        query = AuthorizationService(self._session, account_id).databases(project_id)
        models = (await self._session.scalars(query.order_by(Databases.created_at))).all()
        return [self._to_domain(model) for model in models]

    async def add(self, entity: Database) -> None:
        self._session.add(
            Databases(
                id=entity.id,
                project_id=entity.project_id,
                name=entity.name,
                type=entity.type,
                notice=entity.notice,
                default_schema=entity.default_schema,
                charset=entity.charset,
                collation=entity.collation,
                author_id=entity.author_id,
                created_at=entity.created_at,
                updated_at=entity.updated_at,
            )
        )

    async def save(self, database: Database) -> None:
        model = await self._session.get_one(Databases, database.id)
        model.name = database.name
        model.type = database.type
        model.notice = database.notice
        model.default_schema = database.default_schema
        model.charset = database.charset
        model.collation = database.collation
        model.updated_at = database.updated_at

    async def remove(self, entity: Database) -> None:
        await self._session.execute(delete(Databases).where(Databases.id == entity.id))

    @staticmethod
    def _to_domain(model: Databases) -> Database:
        return Database(
            id=model.id,
            project_id=model.project_id,
            name=model.name,
            type=DataBaseName(model.type),
            notice=model.notice,
            default_schema=model.default_schema,
            charset=model.charset,
            collation=model.collation,
            author_id=model.author_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
