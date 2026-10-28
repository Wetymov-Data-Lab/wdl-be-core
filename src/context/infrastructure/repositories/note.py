import builtins
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from context.domain.entities.note import DiagramNote
from context.infrastructure.repositories.note_contract import (
    NoteRepository as AbstractNoteRepository,
)
from context.infrastructure.schemas.canvas import DiagramNotes


class NoteRepository(AbstractNoteRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, entity_id: UUID) -> DiagramNote | None:
        model = await self._session.get(DiagramNotes, entity_id)
        return None if model is None else self._to_domain(model)

    async def list(self, database_id: UUID) -> builtins.list[DiagramNote]:
        models = (
            await self._session.scalars(
                select(DiagramNotes)
                .where(DiagramNotes.database_id == database_id)
                .order_by(DiagramNotes.created_at)
            )
        ).all()
        return [self._to_domain(model) for model in models]

    async def add(self, entity: DiagramNote) -> None:
        model = DiagramNotes(
            id=entity.id,
            database_id=entity.database_id,
            text=entity.text,
            width=entity.width,
            height=entity.height,
            color=entity.color,
            author_id=entity.author_id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        model.position = entity.position
        self._session.add(model)

    async def save(self, note: DiagramNote) -> None:
        model = await self._session.get_one(DiagramNotes, note.id)
        model.text = note.text
        model.position = note.position
        model.width = note.width
        model.height = note.height
        model.color = note.color
        model.updated_at = note.updated_at

    async def remove(self, entity: DiagramNote) -> None:
        await self._session.execute(delete(DiagramNotes).where(DiagramNotes.id == entity.id))

    @staticmethod
    def _to_domain(model: DiagramNotes) -> DiagramNote:
        return DiagramNote(
            id=model.id,
            database_id=model.database_id,
            text=model.text,
            position=model.position,
            width=model.width,
            height=model.height,
            color=model.color,
            author_id=model.author_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
