from typing import Annotated, cast
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from wdl_shared.schemas.engine.models.canvas import (
    CanvasStateModel,
    DiagramGroupModel,
    DiagramNoteModel,
)

from wdl_be_core.application.identity import CurrentUser
from wdl_be_core.application.services.group import (
    CreateGroup,
    CreateGroupRequest,
    DeleteGroup,
    DeleteGroupRequest,
    ListGroups,
    UpdateGroup,
    UpdateGroupRequest,
)
from wdl_be_core.domain.entities.group import DiagramGroup
from wdl_be_core.domain.exceptions import DomainError, EntityNotFoundError
from wdl_be_core.infrastructure.database.models.canvas import (
    CanvasStates,
    DiagramNotes,
)
from wdl_be_core.infrastructure.database.models.database import Databases
from wdl_be_core.infrastructure.database.unit_of_work import SQLAlchemyUnitOfWork
from wdl_be_core.presentation.api.dependencies.authentication import get_current_user
from wdl_be_core.presentation.api.dependencies.database import get_database_session
from wdl_be_core.presentation.api.dependencies.realm import get_realm_uow
from wdl_be_core.presentation.api.routers.crud import (
    commit_or_conflict,
    get_or_404,
)

router = APIRouter(prefix="/canvas", tags=["canvas"], dependencies=[Depends(get_current_user)])
DatabaseSession = Annotated[AsyncSession, Depends(get_database_session)]
GroupUow = Annotated[SQLAlchemyUnitOfWork, Depends(get_realm_uow)]
AuthenticatedUser = Annotated[CurrentUser, Depends(get_current_user)]


def canvas_response(state: CanvasStates) -> CanvasStateModel:
    return CanvasStateModel(
        database_id=state.database_id,
        user_id=state.user_id,
        viewport=state.viewport,
        grid_size=state.grid_size,
        snap_to_grid=state.snap_to_grid,
        show_relationship_labels=state.show_relationship_labels,
    )


def group_response(group: DiagramGroup) -> DiagramGroupModel:
    return DiagramGroupModel(
        id=group.id,
        database_id=group.database_id,
        name=group.name.value,
        position={"x": group.position.x, "y": group.position.y},
        width=group.size.width,
        height=group.size.height,
        color=None if group.color is None else group.color.value,
        is_collapsed=group.is_collapsed,
        table_ids=list(group.table_ids),
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
    state.viewport = body.viewport
    state.grid_size = body.grid_size
    state.snap_to_grid = body.snap_to_grid
    state.show_relationship_labels = body.show_relationship_labels
    await commit_or_conflict(session, "Canvas state already exists")
    await session.refresh(state)
    return canvas_response(state)


@router.get("/{database_id}/groups", response_model=list[DiagramGroupModel])
async def list_groups(
    database_id: UUID,
    uow: GroupUow,
    user: AuthenticatedUser,
) -> list[DiagramGroupModel]:
    del user
    return [group_response(group) for group in await ListGroups(uow).execute(database_id)]


@router.post(
    "/{database_id}/groups",
    response_model=DiagramGroupModel,
    status_code=status.HTTP_201_CREATED,
)
async def create_group(
    database_id: UUID,
    body: DiagramGroupModel,
    uow: GroupUow,
    user: AuthenticatedUser,
) -> DiagramGroupModel:
    if body.database_id != database_id:
        raise DomainError("Path database_id must match body database_id")
    group = await CreateGroup(uow).execute(
        CreateGroupRequest(
            database_id=database_id,
            group_id=body.id,
            name=body.name,
            x=body.position.x,
            y=body.position.y,
            width=body.width,
            height=body.height,
            color=body.color,
            is_collapsed=body.is_collapsed,
            table_ids=body.table_ids,
            author_id=user.account_id,
        )
    )
    return group_response(group)


@router.put("/{database_id}/groups/{group_id}", response_model=DiagramGroupModel)
async def update_group(
    database_id: UUID,
    group_id: UUID,
    body: DiagramGroupModel,
    uow: GroupUow,
    user: AuthenticatedUser,
) -> DiagramGroupModel:
    if body.id != group_id or body.database_id != database_id:
        raise DomainError("Path identifiers must match body identifiers")
    group = await UpdateGroup(uow).execute(
        UpdateGroupRequest(
            database_id=database_id,
            group_id=group_id,
            name=body.name,
            x=body.position.x,
            y=body.position.y,
            width=body.width,
            height=body.height,
            color=body.color,
            is_collapsed=body.is_collapsed,
            table_ids=body.table_ids,
            updated_by=user.account_id,
        )
    )
    return group_response(group)


@router.delete(
    "/{database_id}/groups/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_group(
    database_id: UUID,
    group_id: UUID,
    uow: GroupUow,
    user: AuthenticatedUser,
) -> Response:
    await DeleteGroup(uow).execute(
        DeleteGroupRequest(
            database_id=database_id,
            group_id=group_id,
            deleted_by=user.account_id,
        )
    )
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
    session: DatabaseSession,
    user: AuthenticatedUser,
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
        author_id=user.account_id,
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
    note.text = body.text
    note.position = body.position
    note.width = body.width
    note.height = body.height
    note.color = body.color
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
