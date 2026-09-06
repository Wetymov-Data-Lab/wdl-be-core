from typing import Any
from uuid import UUID

import jwt

from wdl_be_core.application.identity import CurrentUser
from wdl_be_core.domain.exceptions import AuthenticationError


class JWTAccessTokenVerifier:
    """Verify access tokens issued by wdl-be-identity."""

    def __init__(self, *, secret_key: str, issuer: str, audience: str) -> None:
        self._secret_key = secret_key
        self._issuer = issuer
        self._audience = audience

    def verify(self, token: str) -> CurrentUser:
        try:
            payload: dict[str, Any] = jwt.decode(
                token,
                self._secret_key,
                algorithms=["HS256"],
                audience=self._audience,
                issuer=self._issuer,
                options={"require": ["sub", "sid", "type", "iat", "nbf", "exp", "jti"]},
            )
            if payload["type"] != "access":
                raise AuthenticationError("Invalid token type")
            return CurrentUser(
                account_id=UUID(payload["sub"]),
                session_id=UUID(payload["sid"]),
            )
        except AuthenticationError:
            raise
        except (jwt.PyJWTError, KeyError, TypeError, ValueError) as error:
            raise AuthenticationError("Invalid or expired access token") from error
