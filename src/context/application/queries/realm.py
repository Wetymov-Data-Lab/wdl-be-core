from dataclasses import dataclass
from uuid import UUID

from common.exceptions.exceptions import EntityNotFoundError
from context.application.use_case import UseCase
from context.domain.entities.realm import Realm
from context.infrastructure.repositories.realm_contract import RealmUnitOfWork


class ListRealms(UseCase[UUID, list[Realm]]):
    def __init__(self, uow: RealmUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, request: UUID) -> list[Realm]:
        async with self._uow:
            return await self._uow.realms.list_visible_to(request)


@dataclass(frozen=True, slots=True)
class GetRealmRequest:
    realm_id: UUID
    user_id: UUID


class GetRealm(UseCase[GetRealmRequest, Realm]):
    def __init__(self, uow: RealmUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, request: GetRealmRequest) -> Realm:
        async with self._uow:
            realm = await self._uow.realms.get(request.realm_id)
            if realm is None:
                raise EntityNotFoundError(f"Realm {request.realm_id} was not found")
            realm.ensure_visible_to(request.user_id)
            return realm
