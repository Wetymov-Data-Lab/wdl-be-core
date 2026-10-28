from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from context.domain.entities.project import Project
from context.infrastructure.repositories.project_contract import (
    ProjectRepository as AbstractProjectRepository,
)
from context.infrastructure.schemas.project import Projects
from context.infrastructure.services.authorization import AuthorizationService


class ProjectRepository(AbstractProjectRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, entity_id: UUID) -> Project | None:
        model = await self._session.get(Projects, entity_id)
        return None if model is None else self._to_domain(model)

    async def list_accessible(
        self, account_id: UUID, realm_id: UUID | None = None
    ) -> list[Project]:
        query = AuthorizationService(self._session, account_id).projects(realm_id)
        models = (await self._session.scalars(query.order_by(Projects.created_at))).all()
        return [self._to_domain(model) for model in models]

    async def add(self, entity: Project) -> None:
        self._session.add(
            Projects(
                id=entity.id,
                name=entity.name,
                notice=entity.notice,
                realm_id=entity.realm_id,
                author_id=entity.author_id,
                created_at=entity.created_at,
                updated_at=entity.updated_at,
            )
        )

    async def save(self, project: Project) -> None:
        model = await self._session.get_one(Projects, project.id)
        model.name = project.name
        model.notice = project.notice
        model.updated_at = project.updated_at

    async def remove(self, entity: Project) -> None:
        await self._session.execute(delete(Projects).where(Projects.id == entity.id))

    @staticmethod
    def _to_domain(model: Projects) -> Project:
        return Project(
            id=model.id,
            name=model.name,
            notice=model.notice,
            realm_id=model.realm_id,
            author_id=model.author_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
