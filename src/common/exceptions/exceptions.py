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


class SqlExportError(DomainError):
    """The ER model cannot be represented by the supported SQL dialect."""


class HistoryConflictError(DomainError):
    """An undo/redo step is missing or no longer matches the current diagram."""
