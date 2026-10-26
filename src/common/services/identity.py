from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CurrentUser:
    """Authenticated identity propagated into application use cases."""

    account_id: UUID
    session_id: UUID


class AccessTokenVerifier(Protocol):
    """Port implemented by the identity-token infrastructure adapter."""

    def verify(self, token: str) -> CurrentUser: ...
