class DomainError(Exception):
    """Base exception for violations of domain rules."""


class EntityNotFoundError(DomainError):
    """Requested domain entity does not exist."""


class EntityAlreadyExistsError(DomainError):
    """An entity violates a uniqueness constraint."""


class InvalidRealmNameError(DomainError):
    """Realm name is empty after normalization."""


class RealmAlreadyExistsError(DomainError):
    """A realm with the same name already exists."""


class AuthenticationError(Exception):
    """The caller did not provide a valid identity access token."""


class AuthorizationError(Exception):
    """The authenticated caller cannot access the requested resource."""
