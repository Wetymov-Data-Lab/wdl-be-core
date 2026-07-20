from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from wdl_be_core.infrastructure.config import get_settings
from wdl_be_core.infrastructure.database.base import Base

database_uri = get_settings().SQLALCHEMY_ASYNC_DATABASE_URI
if database_uri is None:
    raise RuntimeError("SQLALCHEMY_ASYNC_DATABASE_URI is not configured")

engine = create_async_engine(
    database_uri,
    echo=get_settings().SQLALCHEMY_ECHO,
    pool_pre_ping=True,
)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def create_tables() -> None:
    """Create tables missing from the database without running Alembic."""
    import wdl_be_core.infrastructure.database.models  # noqa: F401, PLC0415

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session
