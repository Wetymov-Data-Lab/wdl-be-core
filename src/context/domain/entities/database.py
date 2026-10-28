from dataclasses import dataclass, fields
from datetime import datetime
from uuid import UUID, uuid4

from wdl_shared.schemas.engine.enums.database import DataBaseName

from context.domain.entities.base import Entity


@dataclass(frozen=True, slots=True, kw_only=True)
class DatabaseAttributes:
    """Mutable attributes of a database diagram."""

    name: str
    type: DataBaseName
    notice: str | None
    default_schema: str | None
    charset: str | None
    collation: str | None


@dataclass(eq=False, kw_only=True)
class Database(Entity[UUID]):
    project_id: UUID
    name: str
    type: DataBaseName
    notice: str | None
    default_schema: str | None
    charset: str | None
    collation: str | None
    author_id: UUID
    created_at: datetime
    updated_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        project_id: UUID,
        attributes: DatabaseAttributes,
        author_id: UUID,
        created_at: datetime,
        database_id: UUID | None = None,
    ) -> "Database":
        return cls(
            id=database_id or uuid4(),
            project_id=project_id,
            name=attributes.name,
            type=attributes.type,
            notice=attributes.notice,
            default_schema=attributes.default_schema,
            charset=attributes.charset,
            collation=attributes.collation,
            author_id=author_id,
            created_at=created_at,
        )

    def update(self, *, attributes: DatabaseAttributes, updated_at: datetime) -> None:
        for field in fields(attributes):
            setattr(self, field.name, getattr(attributes, field.name))
        self.updated_at = updated_at
