from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from wdl_be_core.infrastructure.config import get_settings

database_uri = get_settings().SQLALCHEMY_ASYNC_DATABASE_URI
if database_uri is None:  # pragma: no cover - populated by Settings validator
    raise RuntimeError("SQLALCHEMY_ASYNC_DATABASE_URI is not configured")

engine = create_async_engine(
    database_uri,
    echo=get_settings().SQLALCHEMY_ECHO,
    pool_pre_ping=True,
)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session
