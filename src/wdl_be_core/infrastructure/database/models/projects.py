from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from wdl_be_core.infrastructure.database.base import Base
from wdl_be_core.infrastructure.database.models.mixins import AuditMixin


class Projects(AuditMixin, Base):
    """Project model"""

    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("realm_id", "name", name="uq_projects_realm_id_name"),
    )

    # Permissions
    __model_permissions__ = [
        ("create", "Разрешает создание объекта Project"),
        ("read", "Разрешает просмотр объекта Project"),
        ("update", "Разрешает редактирование объекта Project"),
        ("delete", "Разрешает удаление объекта Project"),
    ]

    # Base attributes
    id:       Mapped[UUID]       = mapped_column(Uuid, primary_key=True)
    name:     Mapped[str]        = mapped_column(String(255), nullable=False)
    notice:   Mapped[str | None] = mapped_column(String(255), nullable=True)
    realm_id: Mapped[UUID]       = mapped_column(
        Uuid,
        ForeignKey("realms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
