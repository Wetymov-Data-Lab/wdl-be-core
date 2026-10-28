from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from context.domain.entities.base import Entity


@dataclass(eq=False, kw_only=True)
class Project(Entity[UUID]):
    name: str
    notice: str | None
    realm_id: UUID
    author_id: UUID
    created_at: datetime
    updated_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        name: str,
        notice: str | None,
        realm_id: UUID,
        author_id: UUID,
        created_at: datetime,
        project_id: UUID | None = None,
    ) -> "Project":
        return cls(
            id=project_id or uuid4(),
            name=name,
            notice=notice,
            realm_id=realm_id,
            author_id=author_id,
            created_at=created_at,
        )

    def update(self, *, name: str, notice: str | None, updated_at: datetime) -> None:
        self.name = name
        self.notice = notice
        self.updated_at = updated_at
