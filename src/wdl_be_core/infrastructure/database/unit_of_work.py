from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from wdl_be_core.domain.repositories.realm import RealmUnitOfWork
from wdl_be_core.infrastructure.database.repositories.realms import RealmRepository


class SQLAlchemyUnitOfWork(RealmUnitOfWork):
    """Base SQLAlchemy transaction; domain repositories are added by subclasses."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self.session: AsyncSession | None = None

    async def __aenter__(self) -> "SQLAlchemyUnitOfWork":
        self.session = self._session_factory()
        self.realms = RealmRepository(self.session)
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
            await self.rollback()
        finally:
            await self.session.close()
            self.session = None

    async def commit(self) -> None:
        await self._get_session().commit()

    async def rollback(self) -> None:
        await self._get_session().rollback()

    def _get_session(self) -> AsyncSession:
        if self.session is None:
            raise RuntimeError("Unit of work must be used as an async context manager")
        return self.session
