from types import TracebackType
from uuid import UUID, uuid4

import pytest

from wdl_be_core.application.services.realm import (
    CreateRealm,
    CreateRealmRequest,
    DeleteRealm,
    DeleteRealmRequest,
    GetRealm,
    UpdateRealm,
    UpdateRealmRequest,
)
from wdl_be_core.domain.entities.realm import Realm, RealmName, RealmStatus, RealmVisibility
from wdl_be_core.domain.exceptions import EntityNotFoundError, RealmAlreadyExistsError
from wdl_be_core.domain.repositories.realm import RealmRepository, RealmUnitOfWork


class FakeRealmRepository(RealmRepository):
    def __init__(self) -> None:
        self.items: dict[UUID, Realm] = {}

    async def get(self, entity_id: UUID) -> Realm | None:
        realm = self.items.get(entity_id)
        return realm if realm is not None and realm.deleted_at is None else None

    async def list(self) -> list[Realm]:
        return [realm for realm in self.items.values() if realm.deleted_at is None]

    async def exists_by_name(self, name: RealmName, *, exclude_id: UUID | None = None) -> bool:
        return any(realm.name == name and realm.id != exclude_id for realm in self.items.values())

    async def exists_by_slug(self, slug: str, *, exclude_id: UUID | None = None) -> bool:
        return any(realm.slug == slug and realm.id != exclude_id for realm in self.items.values())

    async def add(self, entity: Realm) -> None:
        self.items[entity.id] = entity

    async def save(self, realm: Realm) -> None:
        self.items[realm.id] = realm

    async def remove(self, entity: Realm) -> None:
        del self.items[entity.id]


class FakeRealmUnitOfWork(RealmUnitOfWork):
    def __init__(self) -> None:
        self.realms = FakeRealmRepository()
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()


async def test_create_get_update_delete_realm() -> None:
    uow = FakeRealmUnitOfWork()
    author_id = uuid4()

    created = await CreateRealm(uow).execute(
        CreateRealmRequest(
            name="  Main realm  ",
            slug="main-realm",
            status=RealmStatus.ACTIVE,
            visibility=RealmVisibility.PRIVATE,
            settings={"locale": "ru"},
            notice="Initial",
            author_id=author_id,
        )
    )
    assert created.name.value == "Main realm"
    assert created.author_id == author_id
    assert await GetRealm(uow).execute(created.id) == created

    updated = await UpdateRealm(uow).execute(
        UpdateRealmRequest(
            realm_id=created.id,
            name="Renamed",
            slug="renamed",
            status=RealmStatus.ARCHIVED,
            visibility=RealmVisibility.INTERNAL,
            settings={},
            notice=None,
            updated_by=author_id,
        )
    )
    assert updated.name.value == "Renamed"
    assert updated.notice is None
    assert updated.updated_at is not None

    await DeleteRealm(uow).execute(DeleteRealmRequest(created.id, author_id))
    assert created.deleted_at is not None
    assert uow.commits == 3


async def test_duplicate_realm_name_is_rejected() -> None:
    uow = FakeRealmUnitOfWork()
    request = CreateRealmRequest(
        name="Main",
        slug="main",
        status=RealmStatus.ACTIVE,
        visibility=RealmVisibility.PRIVATE,
        settings={},
        notice=None,
        author_id=uuid4(),
    )
    await CreateRealm(uow).execute(request)

    with pytest.raises(RealmAlreadyExistsError):
        await CreateRealm(uow).execute(request)


async def test_missing_realm_is_rejected() -> None:
    with pytest.raises(EntityNotFoundError):
        await GetRealm(FakeRealmUnitOfWork()).execute(uuid4())
