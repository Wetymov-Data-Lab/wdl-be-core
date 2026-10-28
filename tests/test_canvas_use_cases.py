from datetime import UTC, datetime
from types import TracebackType
from typing import cast
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from wdl_shared.schemas.engine.models.canvas import CanvasPosition, CanvasViewport

from common.exceptions.exceptions import DomainError, EntityAlreadyExistsError, EntityNotFoundError
from context.application.services.canvas_state import (
    GetCanvasState,
    GetCanvasStateRequest,
    SaveCanvasState,
    SaveCanvasStateRequest,
)
from context.application.services.note import (
    CreateNote,
    CreateNoteRequest,
    DeleteNote,
    ListNotes,
    NoteRequest,
    UpdateNote,
    UpdateNoteRequest,
)
from context.domain.entities.canvas_state import CanvasPreferences, CanvasState
from context.domain.entities.note import DiagramNote, NoteAttributes
from context.infrastructure.repositories.canvas_state import (
    CanvasStateRepository as SqlCanvasStateRepository,
)
from context.infrastructure.repositories.canvas_state_contract import (
    CanvasStateRepository,
    CanvasStateUnitOfWork,
)
from context.infrastructure.repositories.note import NoteRepository as SqlNoteRepository
from context.infrastructure.repositories.note_contract import NoteRepository, NoteUnitOfWork
from context.infrastructure.schemas.canvas import CanvasStates, DiagramNotes
from context.infrastructure.services.authorization import AuthorizationService

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FakeCanvasStateRepository(CanvasStateRepository):
    def __init__(self) -> None:
        self.items: dict[UUID, CanvasState] = {}
        self.saved = 0

    async def get(self, entity_id: UUID) -> CanvasState | None:
        return self.items.get(entity_id)

    async def find(self, database_id: UUID, user_id: UUID | None) -> CanvasState | None:
        return next(
            (
                state
                for state in self.items.values()
                if state.database_id == database_id and state.user_id == user_id
            ),
            None,
        )

    async def add(self, entity: CanvasState) -> None:
        self.items[entity.id] = entity

    async def save(self, state: CanvasState) -> None:
        self.saved += 1
        self.items[state.id] = state

    async def remove(self, entity: CanvasState) -> None:
        del self.items[entity.id]


class FakeNoteRepository(NoteRepository):
    def __init__(self) -> None:
        self.items: dict[UUID, DiagramNote] = {}

    async def get(self, entity_id: UUID) -> DiagramNote | None:
        return self.items.get(entity_id)

    async def list(self, database_id: UUID) -> list[DiagramNote]:
        return [note for note in self.items.values() if note.database_id == database_id]

    async def add(self, entity: DiagramNote) -> None:
        self.items[entity.id] = entity

    async def save(self, note: DiagramNote) -> None:
        self.items[note.id] = note

    async def remove(self, entity: DiagramNote) -> None:
        del self.items[entity.id]


class FakeCanvasUnitOfWork(CanvasStateUnitOfWork, NoteUnitOfWork):
    def __init__(self) -> None:
        self.canvas_states = FakeCanvasStateRepository()
        self.notes = FakeNoteRepository()
        self.commits = 0
        self.conflict = False

    async def commit(self) -> None:
        if self.conflict:
            raise EntityAlreadyExistsError("Entity violates a uniqueness constraint")
        self.commits += 1

    async def rollback(self) -> None:
        return None

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None


class FakeAuthorization:
    def __init__(self) -> None:
        self.denied: set[UUID] = set()

    async def require_database(self, database_id: UUID) -> None:
        if database_id in self.denied:
            raise EntityNotFoundError(f"Database {database_id} was not found")


def authorization(fake: FakeAuthorization | None = None) -> AuthorizationService:
    return cast(AuthorizationService, fake or FakeAuthorization())


def preferences(zoom: float = 1, grid_size: int = 20) -> CanvasPreferences:
    return CanvasPreferences(
        viewport=CanvasViewport(x=5, y=6, zoom=zoom),
        grid_size=grid_size,
        snap_to_grid=True,
        show_relationship_labels=False,
    )


def note_attributes(text: str = "Remember") -> NoteAttributes:
    return NoteAttributes(
        text=text, position=CanvasPosition(x=1, y=2), width=240, height=160, color=None
    )


async def test_save_canvas_state_creates_then_updates_personal_state() -> None:
    uow = FakeCanvasUnitOfWork()
    database_id, account_id = uuid4(), uuid4()

    created = await SaveCanvasState(uow, authorization()).execute(
        SaveCanvasStateRequest(
            database_id=database_id,
            account_id=account_id,
            requested_user_id=None,
            preferences=preferences(),
        )
    )
    assert created.user_id == account_id
    updated = await SaveCanvasState(uow, authorization()).execute(
        SaveCanvasStateRequest(
            database_id=database_id,
            account_id=account_id,
            requested_user_id=account_id,
            preferences=preferences(zoom=2, grid_size=40),
        )
    )

    assert updated.id == created.id
    assert (updated.viewport.zoom, updated.grid_size) == (2, 40)
    assert uow.canvas_states.saved == 1
    assert (
        await GetCanvasState(uow, authorization()).execute(
            GetCanvasStateRequest(database_id=database_id, account_id=account_id)
        )
        == created
    )


async def test_canvas_state_rejects_foreign_user_after_access_check() -> None:
    uow = FakeCanvasUnitOfWork()
    access = FakeAuthorization()
    database_id = uuid4()
    request = SaveCanvasStateRequest(
        database_id=database_id,
        account_id=uuid4(),
        requested_user_id=uuid4(),
        preferences=preferences(),
    )

    with pytest.raises(DomainError, match="must match the authenticated account"):
        await SaveCanvasState(uow, authorization(access)).execute(request)

    access.denied.add(database_id)
    with pytest.raises(EntityNotFoundError, match="Database"):
        await SaveCanvasState(uow, authorization(access)).execute(request)
    assert uow.canvas_states.items == {}


async def test_missing_canvas_state_is_not_found() -> None:
    database_id = uuid4()

    with pytest.raises(EntityNotFoundError, match=f"Canvas state for database {database_id}"):
        await GetCanvasState(FakeCanvasUnitOfWork(), authorization()).execute(
            GetCanvasStateRequest(database_id=database_id, account_id=uuid4())
        )


async def test_note_lifecycle() -> None:
    uow = FakeCanvasUnitOfWork()
    database_id, note_id = uuid4(), uuid4()

    note = await CreateNote(uow, authorization()).execute(
        CreateNoteRequest(
            database_id=database_id,
            note_id=note_id,
            attributes=note_attributes(),
            author_id=uuid4(),
        )
    )
    assert note.id == note_id
    assert await ListNotes(uow, authorization()).execute(database_id) == [note]

    updated = await UpdateNote(uow, authorization()).execute(
        UpdateNoteRequest(
            database_id=database_id, note_id=note_id, attributes=note_attributes("Changed")
        )
    )
    assert updated.text == "Changed"
    assert updated.updated_at is not None

    await DeleteNote(uow, authorization()).execute(
        NoteRequest(database_id=database_id, note_id=note_id)
    )
    assert uow.notes.items == {}


async def test_note_from_another_database_is_not_found() -> None:
    uow = FakeCanvasUnitOfWork()
    note = DiagramNote.create(
        note_id=uuid4(),
        database_id=uuid4(),
        attributes=note_attributes(),
        author_id=uuid4(),
        created_at=NOW,
    )
    uow.notes.items[note.id] = note

    for use_case, request in (
        (
            UpdateNote,
            UpdateNoteRequest(database_id=uuid4(), note_id=note.id, attributes=note_attributes()),
        ),
        (DeleteNote, NoteRequest(database_id=uuid4(), note_id=note.id)),
    ):
        with pytest.raises(EntityNotFoundError, match=f"DiagramNotes {note.id} was not found"):
            await use_case(uow, authorization()).execute(request)  # type: ignore[attr-defined]
    assert uow.notes.items == {note.id: note}


async def test_create_note_reports_duplicate_id() -> None:
    uow = FakeCanvasUnitOfWork()
    uow.conflict = True
    note_id = uuid4()

    with pytest.raises(EntityAlreadyExistsError, match=f"Diagram note {note_id} already exists"):
        await CreateNote(uow, authorization()).execute(
            CreateNoteRequest(
                database_id=uuid4(),
                note_id=note_id,
                attributes=note_attributes(),
                author_id=uuid4(),
            )
        )


async def test_sql_repositories_map_canvas_entities() -> None:
    session = Mock(spec=AsyncSession)
    session.execute = AsyncMock()
    state = CanvasState.create(database_id=uuid4(), user_id=uuid4(), preferences=preferences())
    note = DiagramNote.create(
        note_id=uuid4(),
        database_id=uuid4(),
        attributes=note_attributes(),
        author_id=uuid4(),
        created_at=NOW,
    )
    states = SqlCanvasStateRepository(cast(AsyncSession, session))
    notes = SqlNoteRepository(cast(AsyncSession, session))

    await states.add(state)
    await notes.add(note)
    state_model, note_model = (call.args[0] for call in session.add.call_args_list)
    assert isinstance(state_model, CanvasStates)
    assert isinstance(note_model, DiagramNotes)
    assert (state_model.viewport_x, state_model.viewport_y, state_model.zoom) == (5, 6, 1)
    assert (note_model.position_x, note_model.position_y) == (1, 2)
    assert SqlCanvasStateRepository._to_domain(state_model).viewport == state.viewport
    assert SqlNoteRepository._to_domain(note_model).position == note.position

    state.apply(preferences(zoom=3))
    note.update(attributes=note_attributes("Changed"), updated_at=NOW)
    session.get_one = AsyncMock(side_effect=[state_model, note_model])
    await states.save(state)
    await notes.save(note)

    session.execute.assert_not_awaited()
    assert state_model.zoom == 3
    assert (note_model.text, note_model.updated_at) == ("Changed", NOW)
