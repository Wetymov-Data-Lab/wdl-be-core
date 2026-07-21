from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from wdl_shared.schemas.engine.enums.realms import (
    RealmStatus as RealmStatus,
)
from wdl_shared.schemas.engine.enums.realms import (
    RealmVisibility as RealmVisibility,
)

from wdl_be_core.domain.entities.base import Entity
from wdl_be_core.domain.exceptions import InvalidRealmNameError
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


@dataclass(eq=False, kw_only=True)
class Realm(Entity[UUID]):
    name: RealmName
    slug: str
    status: RealmStatus
    visibility: RealmVisibility
    settings: dict[str, Any]
    notice: str | None
    author_id: UUID
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    updated_by: UUID | None = None

    def update(
        self,
        *,
        name: RealmName,
        slug: str,
        status: RealmStatus,
        visibility: RealmVisibility,
        settings: dict[str, Any],
        notice: str | None,
        updated_at: datetime,
        updated_by: UUID,
    ) -> None:
        self.name = name
        self.slug = slug
        self.status = status
        self.visibility = visibility
        self.settings = settings
        self.notice = notice
        self.updated_at = updated_at
        self.updated_by = updated_by

    def delete(self, *, deleted_at: datetime, updated_by: UUID) -> None:
        self.deleted_at = deleted_at
        self.updated_at = deleted_at
        self.updated_by = updated_by
