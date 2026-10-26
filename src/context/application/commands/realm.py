from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from common.exceptions.exceptions import EntityNotFoundError, RealmAlreadyExistsError
from context.application.use_case import UseCase
from context.domain.entities.realm import (
    Realm,
    RealmName,
    RealmSlug,
    RealmStatus,
    RealmVisibility,
)
from context.infrastructure.repositories.realm_contract import RealmUnitOfWork


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


class CreateRealm(UseCase[CreateRealmRequest, Realm]):
    def __init__(self, uow: RealmUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, request: CreateRealmRequest) -> Realm:
        name = RealmName(value=request.name)
        slug = RealmSlug(value=request.slug)
        async with self._uow:
            if await self._uow.realms.exists_by_name(name):
                raise RealmAlreadyExistsError(f"Realm '{name.value}' already exists")
            if await self._uow.realms.exists_by_slug(slug):
                raise RealmAlreadyExistsError(f"Realm with slug '{slug.value}' already exists")
            realm = Realm.create(
                name=name.value,
                slug=slug.value,
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
        slug = RealmSlug(value=request.slug)
        async with self._uow:
            realm = await self._uow.realms.get(request.realm_id)
            if realm is None:
                raise EntityNotFoundError(f"Realm {request.realm_id} was not found")
            realm.ensure_owned_by(request.updated_by)
            if await self._uow.realms.exists_by_name(name, exclude_id=realm.id):
                raise RealmAlreadyExistsError(f"Realm '{name.value}' already exists")
            if await self._uow.realms.exists_by_slug(slug, exclude_id=realm.id):
                raise RealmAlreadyExistsError(f"Realm with slug '{slug.value}' already exists")
            realm.update(
                name=name,
                slug=slug,
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
