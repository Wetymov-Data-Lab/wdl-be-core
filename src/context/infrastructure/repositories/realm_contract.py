import builtins
from abc import abstractmethod
from uuid import UUID

from common.mixins.base_repository import Repository
from common.unit_of_work import UnitOfWork
from context.domain.entities.realm import Realm, RealmName, RealmSlug


class RealmRepository(Repository[Realm, UUID]):
    @abstractmethod
    async def list(self) -> builtins.list[Realm]: ...

    async def list_visible_to(self, user_id: UUID) -> builtins.list[Realm]:
        return [realm for realm in await self.list() if realm.is_visible_to(user_id)]

    @abstractmethod
    async def exists_by_name(self, name: RealmName, *, exclude_id: UUID | None = None) -> bool: ...

    @abstractmethod
    async def exists_by_slug(self, slug: RealmSlug, *, exclude_id: UUID | None = None) -> bool: ...

    @abstractmethod
    async def save(self, realm: Realm) -> None: ...


class RealmUnitOfWork(UnitOfWork):
    realms: RealmRepository
