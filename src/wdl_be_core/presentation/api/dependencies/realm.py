from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from wdl_be_core.infrastructure.database.session import async_session_factory
from wdl_be_core.infrastructure.database.unit_of_work import SQLAlchemyUnitOfWork
from wdl_be_core.presentation.api.dependencies.database import get_database_session


def get_realm_uow(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> SQLAlchemyUnitOfWork:
    return SQLAlchemyUnitOfWork(async_session_factory, managed_session=session)
