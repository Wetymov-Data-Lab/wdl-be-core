from abc import abstractmethod
from uuid import UUID

from wdl_be_core.application.repositories import Repository
from wdl_be_core.application.unit_of_work import UnitOfWork
from wdl_be_core.domain.entities.realm import Realm, RealmName


class RealmRepository(Repository[Realm, UUID]):
    @abstractmethod
    async def list(self) -> list[Realm]: ...

    @abstractmethod
    async def exists_by_name(self, name: RealmName, *, exclude_id: UUID | None = None) -> bool: ...

    @abstractmethod
    async def exists_by_slug(self, slug: str, *, exclude_id: UUID | None = None) -> bool: ...

    @abstractmethod
    async def save(self, realm: Realm) -> None: ...


class RealmUnitOfWork(UnitOfWork):
    realms: RealmRepository
