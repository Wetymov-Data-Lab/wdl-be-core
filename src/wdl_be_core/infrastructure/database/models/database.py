from datetime import datetime
from uuid import UUID

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from wdl_shared.schemas.engine.enums.database import ColumnType, DataBaseName

from wdl_be_core.infrastructure.database.base import Base


class Databases(Base):
    """Database model"""

    __tablename__ = "databases"

    # Permissions
    __model_permissions__ = [
        ("create", "Разрешает создание объекта Database"),
        ("read", "Разрешает просмотр объекта Database"),
        ("update", "Разрешает редактирование объекта Database"),
        ("delete", "Разрешает удаление объекта Database"),
    ]

    # Base attributes
    id:         Mapped[UUID]            = mapped_column(Uuid, primary_key=True)
    name:       Mapped[str]             = mapped_column(unique=True)
    notice:     Mapped[str | None]      = mapped_column(String(255), nullable=True)
    project_id: Mapped[UUID]            = mapped_column(Uuid, nullable=False)
    type:       Mapped[DataBaseName]    = mapped_column(String(50), nullable=False)

    # Additional attributes
    created_at: Mapped[datetime]        = mapped_column(insert_default=datetime.now)
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=datetime.now)
    author_id:  Mapped[UUID]            = mapped_column(Uuid, nullable=False)


class Tables(Base):
    """Table model"""

    __tablename__ = "tables"

    # Permissions
    __model_permissions__ = [
        ("create", "Разрешает создание объекта Table"),
        ("read", "Разрешает просмотр объекта Table"),
        ("update", "Разрешает редактирование объекта Table"),
        ("delete", "Разрешает удаление объекта Table"),
    ]

    # Base attributes
    id:          Mapped[UUID]            = mapped_column(Uuid, primary_key=True)
    name:        Mapped[str]             = mapped_column(unique=True)
    description: Mapped[str | None]      = mapped_column(String(255), nullable=True)
    notice:      Mapped[str | None]      = mapped_column(String(255), nullable=True)
    database_id: Mapped[UUID]            = mapped_column(Uuid, nullable=False)
    color:       Mapped[str | None]      = mapped_column(String(7), nullable=True)

    # Additional attributes
    created_at:  Mapped[datetime]        = mapped_column(insert_default=datetime.now)
    updated_at:  Mapped[datetime | None] = mapped_column(onupdate=datetime.now)
    author_id:   Mapped[UUID]            = mapped_column(Uuid, nullable=False)


class Columns(Base):
    """Column model"""

    __tablename__ = "columns"

    # Permissions
    __model_permissions__ = [
        ("create", "Разрешает создание объекта Column"),
        ("read", "Разрешает просмотр объекта Column"),
        ("update", "Разрешает редактирование объекта Column"),
        ("delete", "Разрешает удаление объекта Column"),
    ]

    # Base attributes
    id:         Mapped[UUID]            = mapped_column(Uuid, primary_key=True)
    name:       Mapped[str]             = mapped_column(unique=True)
    notice:     Mapped[str | None]      = mapped_column(String(255), nullable=True)
    table_id:   Mapped[UUID]            = mapped_column(Uuid, nullable=False)
    type:       Mapped[ColumnType]      = mapped_column(String(50), nullable=False)

    # Additional attributes
    created_at: Mapped[datetime]        = mapped_column(insert_default=datetime.now)
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=datetime.now)
    author_id:  Mapped[UUID]            = mapped_column(Uuid, nullable=False)
