from datetime import datetime
from uuid import UUID

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from wdl_be_core.infrastructure.database.base import Base


class Realms(Base):
    """Realm model"""

    __tablename__ = "realms"

    __model_permissions__ = [
        ("create", "Разрешает создание объекта Realm"),
        ("read", "Разрешает просмотр объекта Realm"),
        ("update", "Разрешает редактирование объекта Realm"),
        ("delete", "Разрешает удаление объекта Realm"),
    ]

    # Base attributes
    id:         Mapped[UUID]            = mapped_column(Uuid, primary_key=True)
    name:       Mapped[str]             = mapped_column(unique=True)
    notice:     Mapped[str | None]      = mapped_column(String(255), nullable=True)
 
    # Additional attributes 
    created_at: Mapped[datetime]        = mapped_column(insert_default=datetime.now)
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=datetime.now)
    author_id:  Mapped[UUID]            = mapped_column(Uuid, nullable=False)
