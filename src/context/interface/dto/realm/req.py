from typing import Any

from pydantic import BaseModel, Field
from wdl_shared.schemas.engine.enums.realms import RealmStatus, RealmVisibility


class RealmCreateRequestModel(BaseModel):
    """Client-controlled realm fields; authorship comes from the access token."""

    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255)
    status: RealmStatus = RealmStatus.ACTIVE
    visibility: RealmVisibility = RealmVisibility.PRIVATE
    settings: dict[str, Any] = Field(default_factory=dict)
    notice: str | None = Field(default=None, max_length=255)


class RealmUpdateRequestModel(RealmCreateRequestModel):
    """Complete mutable realm state; editor identity comes from the access token."""
