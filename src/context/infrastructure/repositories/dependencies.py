from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from context.infrastructure.repositories.unit_of_work import SQLAlchemyUnitOfWork
from context.infrastructure.services.diagram_history import DiagramHistory
from infrastructure.database.dependencies import get_database_session
from infrastructure.database.session import async_session_factory


def get_realm_uow(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> SQLAlchemyUnitOfWork:
    return SQLAlchemyUnitOfWork(async_session_factory, managed_session=session)


def get_diagram_history(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> DiagramHistory:
    return DiagramHistory(session)
