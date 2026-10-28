from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from common.exceptions.exceptions import EntityNotFoundError
from common.unit_of_work import commit_or_conflict
from context.application.use_case import UseCase
from context.domain.entities.note import DiagramNote, NoteAttributes
from context.infrastructure.repositories.note_contract import NoteUnitOfWork
from context.infrastructure.services.authorization import AuthorizationService


@dataclass(frozen=True, slots=True)
class NoteRequest:
    database_id: UUID
    note_id: UUID


@dataclass(frozen=True, slots=True)
class CreateNoteRequest:
    database_id: UUID
    note_id: UUID
    attributes: NoteAttributes
    author_id: UUID


@dataclass(frozen=True, slots=True)
class UpdateNoteRequest:
    database_id: UUID
    note_id: UUID
    attributes: NoteAttributes


class ListNotes(UseCase[UUID, list[DiagramNote]]):
    def __init__(self, uow: NoteUnitOfWork, authorization: AuthorizationService) -> None:
        self._uow = uow
        self._authorization = authorization

    async def execute(self, request: UUID) -> list[DiagramNote]:
        await self._authorization.require_database(request)
        async with self._uow:
            return await self._uow.notes.list(request)


class CreateNote(UseCase[CreateNoteRequest, DiagramNote]):
    def __init__(self, uow: NoteUnitOfWork, authorization: AuthorizationService) -> None:
        self._uow = uow
        self._authorization = authorization

    async def execute(self, request: CreateNoteRequest) -> DiagramNote:
        await self._authorization.require_database(request.database_id)
        async with self._uow:
            note = DiagramNote.create(
                note_id=request.note_id,
                database_id=request.database_id,
                attributes=request.attributes,
                author_id=request.author_id,
                created_at=datetime.now(UTC),
            )
            await self._uow.notes.add(note)
            await commit_or_conflict(self._uow, f"Diagram note {request.note_id} already exists")
            return note


class UpdateNote(UseCase[UpdateNoteRequest, DiagramNote]):
    def __init__(self, uow: NoteUnitOfWork, authorization: AuthorizationService) -> None:
        self._uow = uow
        self._authorization = authorization

    async def execute(self, request: UpdateNoteRequest) -> DiagramNote:
        await self._authorization.require_database(request.database_id)
        async with self._uow:
            note = await get_note(self._uow, request.database_id, request.note_id)
            note.update(attributes=request.attributes, updated_at=datetime.now(UTC))
            await self._uow.notes.save(note)
            await self._uow.commit()
            return note


class DeleteNote(UseCase[NoteRequest, None]):
    def __init__(self, uow: NoteUnitOfWork, authorization: AuthorizationService) -> None:
        self._uow = uow
        self._authorization = authorization

    async def execute(self, request: NoteRequest) -> None:
        await self._authorization.require_database(request.database_id)
        async with self._uow:
            note = await get_note(self._uow, request.database_id, request.note_id)
            await self._uow.notes.remove(note)
            await self._uow.commit()


async def get_note(uow: NoteUnitOfWork, database_id: UUID, note_id: UUID) -> DiagramNote:
    note = await uow.notes.get(note_id)
    if note is None:
        raise EntityNotFoundError(f"DiagramNotes {note_id} was not found")
    note.ensure_in_database(database_id)
    return note
