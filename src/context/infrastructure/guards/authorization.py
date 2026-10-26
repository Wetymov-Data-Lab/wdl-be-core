from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from common.services.identity import CurrentUser
from context.infrastructure.guards.authentication import get_current_user
from context.infrastructure.services.authorization import AuthorizationService
from infrastructure.database.dependencies import get_database_session


def get_authorization_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> AuthorizationService:
    return AuthorizationService(session, user.account_id)
