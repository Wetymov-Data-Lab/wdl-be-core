import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from wdl_shared.schemas.engine.enums.realms import (
    RealmStatus as RealmStatus,
)
from wdl_shared.schemas.engine.enums.realms import (
    RealmVisibility as RealmVisibility,
)

from wdl_be_core.domain.entities.base import Entity
from wdl_be_core.domain.exceptions import AuthorizationError, DomainError, InvalidRealmNameError
from wdl_be_core.domain.value_objects import ValueObject


@dataclass(frozen=True, kw_only=True)
class RealmName(ValueObject):
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", self.value.strip())
        super().__post_init__()

    def validate(self) -> None:
        if not self.value:
            raise InvalidRealmNameError("Realm name must not be empty")
        if len(self.value) > 255:
            raise InvalidRealmNameError("Realm name must not exceed 255 characters")


@dataclass(frozen=True, kw_only=True)
class RealmSlug(ValueObject):
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", self.value.strip().lower())
        super().__post_init__()

    def validate(self) -> None:
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", self.value):
            raise DomainError("Realm slug must contain lowercase letters, numbers and hyphens")
        if len(self.value) > 255:
            raise DomainError("Realm slug must not exceed 255 characters")


@dataclass(eq=False, kw_only=True)
class Realm(Entity[UUID]):
    name: RealmName
    slug: RealmSlug
    status: RealmStatus
    visibility: RealmVisibility
    settings: dict[str, Any]
    notice: str | None
    author_id: UUID
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    updated_by: UUID | None = None

    @classmethod
    def create(
        cls,
        *,
        name: str,
        slug: str,
        status: RealmStatus,
        visibility: RealmVisibility,
        settings: dict[str, Any],
        notice: str | None,
        author_id: UUID,
        created_at: datetime,
        realm_id: UUID | None = None,
    ) -> "Realm":
        return cls(
            id=realm_id or uuid4(),
            name=RealmName(value=name),
            slug=RealmSlug(value=slug),
            status=status,
            visibility=visibility,
            settings=dict(settings),
            notice=notice,
            author_id=author_id,
            created_at=created_at,
        )

    @property
    def is_published(self) -> bool:
        return self.visibility is RealmVisibility.PUBLIC

    def is_visible_to(self, user_id: UUID) -> bool:
        return self.author_id == user_id or self.is_published

    def ensure_visible_to(self, user_id: UUID) -> None:
        if not self.is_visible_to(user_id):
            raise AuthorizationError("This realm is private")

    def ensure_owned_by(self, user_id: UUID) -> None:
        if self.author_id != user_id:
            raise AuthorizationError("Only the realm author can modify it")

    def update(
        self,
        *,
        name: RealmName,
        slug: RealmSlug,
        status: RealmStatus,
        visibility: RealmVisibility,
        settings: dict[str, Any],
        notice: str | None,
        updated_at: datetime,
        updated_by: UUID,
    ) -> None:
        self.ensure_owned_by(updated_by)
        self.name = name
        self.slug = slug
        self.status = status
        self.visibility = visibility
        self.settings = dict(settings)
        self.notice = notice
        self.updated_at = updated_at
        self.updated_by = updated_by

    def delete(self, *, deleted_at: datetime, updated_by: UUID) -> None:
        self.ensure_owned_by(updated_by)
        self.deleted_at = deleted_at
        self.updated_at = deleted_at
        self.updated_by = updated_by
