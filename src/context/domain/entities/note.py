from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from wdl_shared.schemas.engine.models.canvas import CanvasPosition

from common.exceptions.exceptions import EntityNotFoundError
from context.domain.entities.base import Entity


@dataclass(frozen=True, slots=True, kw_only=True)
class NoteAttributes:
    """Mutable attributes of a canvas note."""

    text: str
    position: CanvasPosition
    width: float
    height: float
    color: str | None


@dataclass(eq=False, kw_only=True)
class DiagramNote(Entity[UUID]):
    database_id: UUID
    text: str
    position: CanvasPosition
    width: float
    height: float
    color: str | None
    author_id: UUID
    created_at: datetime
    updated_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        note_id: UUID,
        database_id: UUID,
        attributes: NoteAttributes,
        author_id: UUID,
        created_at: datetime,
    ) -> "DiagramNote":
        return cls(
            id=note_id,
            database_id=database_id,
            text=attributes.text,
            position=attributes.position,
            width=attributes.width,
            height=attributes.height,
            color=attributes.color,
            author_id=author_id,
            created_at=created_at,
        )

    def ensure_in_database(self, database_id: UUID) -> None:
        if self.database_id != database_id:
            raise EntityNotFoundError(f"DiagramNotes {self.id} was not found")

    def update(self, *, attributes: NoteAttributes, updated_at: datetime) -> None:
        self.text = attributes.text
        self.position = attributes.position
        self.width = attributes.width
        self.height = attributes.height
        self.color = attributes.color
        self.updated_at = updated_at
