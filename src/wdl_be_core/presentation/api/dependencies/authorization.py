from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from wdl_be_core.application.authorization import AuthorizationService
from wdl_be_core.application.identity import CurrentUser
from wdl_be_core.presentation.api.dependencies.authentication import get_current_user
from wdl_be_core.presentation.api.dependencies.database import get_database_session


def get_authorization_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> AuthorizationService:
    return AuthorizationService(session, user.account_id)
