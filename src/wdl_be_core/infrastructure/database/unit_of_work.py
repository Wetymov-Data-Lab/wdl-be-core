from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from wdl_be_core.domain.repositories.group import GroupUnitOfWork
from wdl_be_core.domain.repositories.realm import RealmUnitOfWork
from wdl_be_core.infrastructure.database.repositories.groups import GroupRepository
from wdl_be_core.infrastructure.database.repositories.realms import RealmRepository


class SQLAlchemyUnitOfWork(RealmUnitOfWork, GroupUnitOfWork):
    """Base SQLAlchemy transaction; domain repositories are added by subclasses."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        managed_session: AsyncSession | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._managed_session = managed_session
        self.session: AsyncSession | None = None

    async def __aenter__(self) -> "SQLAlchemyUnitOfWork":
        self.session = self._managed_session or self._session_factory()
        self.realms = RealmRepository(self.session)
        self.groups = GroupRepository(self.session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self.session is None:
            return
        try:
            if self._managed_session is None:
                await self.rollback()
        finally:
            if self._managed_session is None:
                await self.session.close()
            self.session = None

    async def commit(self) -> None:
        if self._managed_session is None:
            await self._get_session().commit()
        else:
            await self._get_session().flush()

    async def rollback(self) -> None:
        if self._managed_session is None:
            await self._get_session().rollback()

    def _get_session(self) -> AsyncSession:
        if self.session is None:
            raise RuntimeError("Unit of work must be used as an async context manager")
        return self.session
