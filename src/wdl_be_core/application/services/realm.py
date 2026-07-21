from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from wdl_be_core.application.use_cases import UseCase
from wdl_be_core.domain.entities.realm import Realm, RealmName, RealmStatus, RealmVisibility
from wdl_be_core.domain.exceptions import EntityNotFoundError, RealmAlreadyExistsError
from wdl_be_core.domain.repositories.realm import RealmUnitOfWork


@dataclass(frozen=True, slots=True)
class CreateRealmRequest:
    name: str
    slug: str
    status: RealmStatus
    visibility: RealmVisibility
    settings: dict[str, Any]
    notice: str | None
    author_id: UUID


@dataclass(frozen=True, slots=True)
class UpdateRealmRequest:
    realm_id: UUID
    name: str
    slug: str
    status: RealmStatus
    visibility: RealmVisibility
    settings: dict[str, Any]
    notice: str | None
    updated_by: UUID


@dataclass(frozen=True, slots=True)
class DeleteRealmRequest:
    realm_id: UUID
    updated_by: UUID


class ListRealms(UseCase[None, list[Realm]]):
    def __init__(self, uow: RealmUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, request: None = None) -> list[Realm]:
        async with self._uow:
            return await self._uow.realms.list()


class GetRealm(UseCase[UUID, Realm]):
    def __init__(self, uow: RealmUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, request: UUID) -> Realm:
        async with self._uow:
            realm = await self._uow.realms.get(request)
            if realm is None:
                raise EntityNotFoundError(f"Realm {request} was not found")
            return realm


class CreateRealm(UseCase[CreateRealmRequest, Realm]):
    def __init__(self, uow: RealmUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, request: CreateRealmRequest) -> Realm:
        name = RealmName(value=request.name)
        async with self._uow:
            if await self._uow.realms.exists_by_name(name):
                raise RealmAlreadyExistsError(f"Realm '{name.value}' already exists")
            if await self._uow.realms.exists_by_slug(request.slug):
                raise RealmAlreadyExistsError(f"Realm with slug '{request.slug}' already exists")
            realm = Realm(
                id=uuid4(),
                name=name,
                slug=request.slug,
                status=request.status,
                visibility=request.visibility,
                settings=request.settings,
                notice=request.notice,
                author_id=request.author_id,
                created_at=datetime.now(UTC),
            )
            await self._uow.realms.add(realm)
            await self._uow.commit()
            return realm


class UpdateRealm(UseCase[UpdateRealmRequest, Realm]):
    def __init__(self, uow: RealmUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, request: UpdateRealmRequest) -> Realm:
        name = RealmName(value=request.name)
        async with self._uow:
            realm = await self._uow.realms.get(request.realm_id)
            if realm is None:
                raise EntityNotFoundError(f"Realm {request.realm_id} was not found")
            if await self._uow.realms.exists_by_name(name, exclude_id=realm.id):
                raise RealmAlreadyExistsError(f"Realm '{name.value}' already exists")
            if await self._uow.realms.exists_by_slug(request.slug, exclude_id=realm.id):
                raise RealmAlreadyExistsError(f"Realm with slug '{request.slug}' already exists")
            realm.update(
                name=name,
                slug=request.slug,
                status=request.status,
                visibility=request.visibility,
                settings=request.settings,
                notice=request.notice,
                updated_at=datetime.now(UTC),
                updated_by=request.updated_by,
            )
            await self._uow.realms.save(realm)
            await self._uow.commit()
            return realm


class DeleteRealm(UseCase[DeleteRealmRequest, None]):
    def __init__(self, uow: RealmUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, request: DeleteRealmRequest) -> None:
        async with self._uow:
            realm = await self._uow.realms.get(request.realm_id)
            if realm is None:
                raise EntityNotFoundError(f"Realm {request.realm_id} was not found")
            realm.delete(deleted_at=datetime.now(UTC), updated_by=request.updated_by)
            await self._uow.realms.save(realm)
            await self._uow.commit()
