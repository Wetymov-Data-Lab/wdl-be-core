from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, CheckConstraint, DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from wdl_be_core.infrastructure.database.base import Base


class RealmSchema(Base):
    """Realm model"""

    __tablename__ = "realms"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'archived', 'disabled')",
            name="ck_realms_status",
        ),
        CheckConstraint(
            "visibility IN ('private', 'internal', 'public')",
            name="ck_realms_visibility",
        ),
    )

    # Permissions
    __model_permissions__ = [
        ("create", "Разрешает создание объекта Realm"),
        ("read", "Разрешает просмотр объекта Realm"),
        ("update", "Разрешает редактирование объекта Realm"),
        ("delete", "Разрешает удаление объекта Realm"),
    ]

    # Base attributes
    id:     Mapped[UUID]       = mapped_column(Uuid, primary_key=True)
    name:   Mapped[str]        = mapped_column(unique=True)
    slug:   Mapped[str]        = mapped_column(String(255), unique=True)
    status: Mapped[str]        = mapped_column(String(32), default="active")
    visibility: Mapped[str]    = mapped_column(String(32), default="private")
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    notice: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Additional attributes
    created_at: Mapped[datetime]        = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    author_id:  Mapped[UUID]            = mapped_column(Uuid, nullable=False)
    updated_by: Mapped[UUID | None]     = mapped_column(Uuid, nullable=True)
