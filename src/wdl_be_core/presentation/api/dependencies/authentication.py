from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer

from wdl_be_core.application.identity import AccessTokenVerifier, CurrentUser
from wdl_be_core.domain.exceptions import AuthenticationError
from wdl_be_core.infrastructure.config import settings
from wdl_be_core.infrastructure.identity import JWTAccessTokenVerifier

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=settings.IDENTITY_TOKEN_URL, auto_error=False)


def get_access_token_verifier() -> AccessTokenVerifier:
    return JWTAccessTokenVerifier(
        secret_key=settings.JWT_SECRET_KEY.get_secret_value(),
        issuer=settings.JWT_ISSUER,
        audience=settings.JWT_AUDIENCE,
    )


async def get_current_user(
    request: Request,
    bearer_token: Annotated[str | None, Depends(oauth2_scheme)],
    verifier: Annotated[AccessTokenVerifier, Depends(get_access_token_verifier)],
) -> CurrentUser:
    if not bearer_token:
        raise AuthenticationError("Bearer token is required")
    user = verifier.verify(bearer_token)
    request.state.audit_actor_id = str(user.account_id)
    return user
