from uuid import UUID

from sqlalchemy import delete, exists, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from wdl_be_core.domain.entities.realm import Realm, RealmName, RealmStatus, RealmVisibility
from wdl_be_core.domain.repositories.realm import RealmRepository as AbstractRealmRepository
from wdl_be_core.infrastructure.database.models.realms import RealmSchema


class RealmRepository(AbstractRealmRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, entity_id: UUID) -> Realm | None:
        model = await self._session.scalar(
            select(RealmSchema).where(
                RealmSchema.id == entity_id,
                RealmSchema.deleted_at.is_(None),
            )
        )
        return None if model is None else self._to_domain(model)

    async def list(self) -> list[Realm]:
        models = (
            await self._session.scalars(
                select(RealmSchema)
                .where(RealmSchema.deleted_at.is_(None))
                .order_by(RealmSchema.created_at)
            )
        ).all()
        return [self._to_domain(model) for model in models]

    async def exists_by_name(self, name: RealmName, *, exclude_id: UUID | None = None) -> bool:
        query = select(exists().where(RealmSchema.name == name.value))
        if exclude_id is not None:
            query = select(
                exists().where(RealmSchema.name == name.value, RealmSchema.id != exclude_id)
            )
        return bool(await self._session.scalar(query))

    async def exists_by_slug(self, slug: str, *, exclude_id: UUID | None = None) -> bool:
        query = select(exists().where(RealmSchema.slug == slug))
        if exclude_id is not None:
            query = select(exists().where(RealmSchema.slug == slug, RealmSchema.id != exclude_id))
        return bool(await self._session.scalar(query))

    async def add(self, entity: Realm) -> None:
        self._session.add(
            RealmSchema(
                id=entity.id,
                name=entity.name.value,
                slug=entity.slug,
                status=entity.status.value,
                visibility=entity.visibility.value,
                settings=entity.settings,
                notice=entity.notice,
                author_id=entity.author_id,
                created_at=entity.created_at,
                updated_at=entity.updated_at,
                deleted_at=entity.deleted_at,
                updated_by=entity.updated_by,
            )
        )

    async def save(self, realm: Realm) -> None:
        await self._session.execute(
            update(RealmSchema)
            .where(RealmSchema.id == realm.id)
            .values(
                name=realm.name.value,
                slug=realm.slug,
                status=realm.status.value,
                visibility=realm.visibility.value,
                settings=realm.settings,
                notice=realm.notice,
                updated_at=realm.updated_at,
                deleted_at=realm.deleted_at,
                updated_by=realm.updated_by,
            )
        )

    async def remove(self, entity: Realm) -> None:
        await self._session.execute(delete(RealmSchema).where(RealmSchema.id == entity.id))

    @staticmethod
    def _to_domain(model: RealmSchema) -> Realm:
        return Realm(
            id=model.id,
            name=RealmName(value=model.name),
            slug=model.slug,
            status=RealmStatus(model.status),
            visibility=RealmVisibility(model.visibility),
            settings=model.settings,
            notice=model.notice,
            author_id=model.author_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            updated_by=model.updated_by,
        )
