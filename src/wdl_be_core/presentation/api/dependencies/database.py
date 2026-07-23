from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from wdl_be_core.infrastructure.database.session import async_session_factory


async def get_database_session() -> AsyncIterator[AsyncSession]:
    """Provide one transaction-capable session per API request."""

    async with async_session_factory() as session:
        yield session
