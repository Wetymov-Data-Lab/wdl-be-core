from typing import Annotated, cast
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from wdl_shared.schemas.engine.models.canvas import (
    CanvasStateModel,
    DiagramGroupModel,
    DiagramNoteModel,
)

from wdl_be_core.domain.exceptions import DomainError, EntityNotFoundError
from wdl_be_core.infrastructure.database.models.canvas import (
    CanvasStates,
    DiagramGroups,
    DiagramGroupTables,
    DiagramNotes,
)
from wdl_be_core.infrastructure.database.models.database import Databases, Tables
from wdl_be_core.presentation.api.dependencies.database import get_database_session
from wdl_be_core.presentation.api.routers.crud import (
    commit_or_conflict,
    flush_or_conflict,
    get_or_404,
)

router = APIRouter(prefix="/canvas", tags=["canvas"])
DatabaseSession = Annotated[AsyncSession, Depends(get_database_session)]


def canvas_response(state: CanvasStates) -> CanvasStateModel:
    return CanvasStateModel(
        database_id=state.database_id,
        user_id=state.user_id,
        viewport=state.viewport,
        grid_size=state.grid_size,
        snap_to_grid=state.snap_to_grid,
        show_relationship_labels=state.show_relationship_labels,
    )


async def group_response(
    session: AsyncSession,
    group: DiagramGroups,
) -> DiagramGroupModel:
    table_ids = (
        await session.scalars(
            select(DiagramGroupTables.table_id).where(
                DiagramGroupTables.group_id == group.id
            )
        )
    ).all()
    return DiagramGroupModel(
        id=group.id,
        database_id=group.database_id,
        name=group.name,
        position=group.position,
        width=group.width,
        height=group.height,
        color=group.color,
        is_collapsed=group.is_collapsed,
        table_ids=list(table_ids),
    )


def note_response(note: DiagramNotes) -> DiagramNoteModel:
    return DiagramNoteModel(
        id=note.id,
        database_id=note.database_id,
        text=note.text,
        position=note.position,
        width=note.width,
        height=note.height,
        color=note.color,
    )


async def find_canvas_state(
    session: AsyncSession,
    database_id: UUID,
    user_id: UUID | None,
) -> CanvasStates | None:
    query = select(CanvasStates).where(CanvasStates.database_id == database_id)
    query = (
        query.where(CanvasStates.user_id.is_(None))
        if user_id is None
        else query.where(CanvasStates.user_id == user_id)
    )
    return cast(CanvasStates | None, await session.scalar(query))


@router.get("/{database_id}", response_model=CanvasStateModel)
async def get_canvas_state(
    database_id: UUID,
    session: DatabaseSession,
    user_id: UUID | None = None,
) -> CanvasStateModel:
    state = await find_canvas_state(session, database_id, user_id)
    if state is None:
        raise EntityNotFoundError(f"Canvas state for database {database_id} was not found")
    return canvas_response(state)


@router.put("/{database_id}", response_model=CanvasStateModel)
async def save_canvas_state(
    database_id: UUID,
    body: CanvasStateModel,
    session: DatabaseSession,
) -> CanvasStateModel:
    if body.database_id != database_id:
        raise DomainError("Path database_id must match body database_id")
    await get_or_404(session, Databases, database_id)
    state = await find_canvas_state(session, database_id, body.user_id)
    if state is None:
        state = CanvasStates(id=uuid4(), database_id=database_id, user_id=body.user_id)
        session.add(state)
    state.viewport                 = body.viewport
    state.grid_size                = body.grid_size
    state.snap_to_grid             = body.snap_to_grid
    state.show_relationship_labels = body.show_relationship_labels
    await commit_or_conflict(session, "Canvas state already exists")
    await session.refresh(state)
    return canvas_response(state)


@router.get("/{database_id}/groups", response_model=list[DiagramGroupModel])
async def list_groups(
    database_id: UUID,
    session: DatabaseSession,
) -> list[DiagramGroupModel]:
    groups = (
        await session.scalars(
            select(DiagramGroups)
            .where(DiagramGroups.database_id == database_id)
            .order_by(DiagramGroups.created_at)
        )
    ).all()
    return [await group_response(session, group) for group in groups]


@router.post(
    "/{database_id}/groups",
    response_model=DiagramGroupModel,
    status_code=status.HTTP_201_CREATED,
)
async def create_group(
    database_id: UUID,
    body: DiagramGroupModel,
    author_id: UUID,
    session: DatabaseSession,
) -> DiagramGroupModel:
    if body.database_id != database_id:
        raise DomainError("Path database_id must match body database_id")
    await get_or_404(session, Databases, database_id)
    for table_id in body.table_ids:
        table = await get_or_404(session, Tables, table_id)
        if table.database_id != database_id:
            raise EntityNotFoundError(f"Table {table_id} does not belong to database {database_id}")
    group = DiagramGroups(
        id=body.id,
        database_id=database_id,
        name=body.name,
        width=body.width,
        height=body.height,
        color=body.color,
        is_collapsed=body.is_collapsed,
        author_id=author_id,
    )
    group.position = body.position
    session.add(group)
    await flush_or_conflict(session, f"Diagram group '{body.name}' already exists")
    session.add_all(
        DiagramGroupTables(id=uuid4(), group_id=group.id, table_id=table_id)
        for table_id in body.table_ids
    )
    await commit_or_conflict(session, f"Diagram group '{body.name}' already exists")
    await session.refresh(group)
    return await group_response(session, group)


@router.put("/{database_id}/groups/{group_id}", response_model=DiagramGroupModel)
async def update_group(
    database_id: UUID,
    group_id: UUID,
    body: DiagramGroupModel,
    session: DatabaseSession,
) -> DiagramGroupModel:
    if body.id != group_id or body.database_id != database_id:
        raise DomainError("Path identifiers must match body identifiers")
    group = await get_or_404(session, DiagramGroups, group_id)
    if group.database_id != database_id:
        raise EntityNotFoundError(f"DiagramGroups {group_id} was not found")
    for table_id in body.table_ids:
        table = await get_or_404(session, Tables, table_id)
        if table.database_id != database_id:
            raise EntityNotFoundError(f"Table {table_id} does not belong to database {database_id}")
    group.name         = body.name
    group.position     = body.position
    group.width        = body.width
    group.height       = body.height
    group.color        = body.color
    group.is_collapsed = body.is_collapsed
    await session.execute(
        delete(DiagramGroupTables).where(DiagramGroupTables.group_id == group.id)
    )
    await session.flush()
    session.add_all(
        DiagramGroupTables(id=uuid4(), group_id=group.id, table_id=table_id)
        for table_id in body.table_ids
    )
    await commit_or_conflict(session, f"Diagram group '{body.name}' already exists")
    await session.refresh(group)
    return await group_response(session, group)


@router.delete(
    "/{database_id}/groups/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_group(
    database_id: UUID,
    group_id: UUID,
    session: DatabaseSession,
) -> Response:
    group = await get_or_404(session, DiagramGroups, group_id)
    if group.database_id != database_id:
        raise EntityNotFoundError(f"DiagramGroups {group_id} was not found")
    await session.delete(group)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{database_id}/notes", response_model=list[DiagramNoteModel])
async def list_notes(
    database_id: UUID,
    session: DatabaseSession,
) -> list[DiagramNoteModel]:
    notes = (
        await session.scalars(
            select(DiagramNotes)
            .where(DiagramNotes.database_id == database_id)
            .order_by(DiagramNotes.created_at)
        )
    ).all()
    return [note_response(note) for note in notes]


@router.post(
    "/{database_id}/notes",
    response_model=DiagramNoteModel,
    status_code=status.HTTP_201_CREATED,
)
async def create_note(
    database_id: UUID,
    body: DiagramNoteModel,
    author_id: UUID,
    session: DatabaseSession,
) -> DiagramNoteModel:
    if body.database_id != database_id:
        raise DomainError("Path database_id must match body database_id")
    await get_or_404(session, Databases, database_id)
    note = DiagramNotes(
        id=body.id,
        database_id=database_id,
        text=body.text,
        width=body.width,
        height=body.height,
        color=body.color,
        author_id=author_id,
    )
    note.position = body.position
    session.add(note)
    await commit_or_conflict(session, f"Diagram note {body.id} already exists")
    await session.refresh(note)
    return note_response(note)


@router.put("/{database_id}/notes/{note_id}", response_model=DiagramNoteModel)
async def update_note(
    database_id: UUID,
    note_id: UUID,
    body: DiagramNoteModel,
    session: DatabaseSession,
) -> DiagramNoteModel:
    if body.id != note_id or body.database_id != database_id:
        raise DomainError("Path identifiers must match body identifiers")
    note = await get_or_404(session, DiagramNotes, note_id)
    if note.database_id != database_id:
        raise EntityNotFoundError(f"DiagramNotes {note_id} was not found")
    note.text     = body.text
    note.position = body.position
    note.width    = body.width
    note.height   = body.height
    note.color    = body.color
    await session.commit()
    await session.refresh(note)
    return note_response(note)


@router.delete(
    "/{database_id}/notes/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_note(
    database_id: UUID,
    note_id: UUID,
    session: DatabaseSession,
) -> Response:
    note = await get_or_404(session, DiagramNotes, note_id)
    if note.database_id != database_id:
        raise EntityNotFoundError(f"DiagramNotes {note_id} was not found")
    await session.delete(note)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
