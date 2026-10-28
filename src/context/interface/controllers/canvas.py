from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from wdl_shared.schemas.engine.models.canvas import (
    CanvasStateModel,
    DiagramGroupModel,
    DiagramNoteModel,
)

from common.exceptions.exceptions import DomainError
from common.services.identity import CurrentUser
from context.application.services.canvas_state import (
    GetCanvasState,
    GetCanvasStateRequest,
    SaveCanvasState,
    SaveCanvasStateRequest,
)
from context.application.services.group import (
    CreateGroup,
    CreateGroupRequest,
    DeleteGroup,
    DeleteGroupRequest,
    ListGroups,
    UpdateGroup,
    UpdateGroupRequest,
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
from context.domain.entities.group import DiagramGroup
from context.domain.entities.note import DiagramNote, NoteAttributes
from context.infrastructure.guards.authentication import get_current_user
from context.infrastructure.guards.authorization import get_authorization_service
from context.infrastructure.repositories.dependencies import get_realm_uow
from context.infrastructure.repositories.unit_of_work import SQLAlchemyUnitOfWork
from context.infrastructure.services.authorization import AuthorizationService

router = APIRouter(prefix="/canvas", tags=["canvas"], dependencies=[Depends(get_current_user)])
CanvasUow = Annotated[SQLAlchemyUnitOfWork, Depends(get_realm_uow)]
AuthenticatedUser = Annotated[CurrentUser, Depends(get_current_user)]
Authorization = Annotated[AuthorizationService, Depends(get_authorization_service)]


def canvas_response(state: CanvasState) -> CanvasStateModel:
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


def note_response(note: DiagramNote) -> DiagramNoteModel:
    return DiagramNoteModel(
        id=note.id,
        database_id=note.database_id,
        text=note.text,
        position=note.position,
        width=note.width,
        height=note.height,
        color=note.color,
    )


def note_attributes(body: DiagramNoteModel) -> NoteAttributes:
    return NoteAttributes(
        text=body.text,
        position=body.position,
        width=body.width,
        height=body.height,
        color=body.color,
    )


@router.get("/{database_id}", response_model=CanvasStateModel)
async def get_canvas_state(
    database_id: UUID,
    uow: CanvasUow,
    user: AuthenticatedUser,
    authorization: Authorization,
) -> CanvasStateModel:
    state = await GetCanvasState(uow, authorization).execute(
        GetCanvasStateRequest(database_id=database_id, account_id=user.account_id)
    )
    return canvas_response(state)


@router.put("/{database_id}", response_model=CanvasStateModel)
async def save_canvas_state(
    database_id: UUID,
    body: CanvasStateModel,
    uow: CanvasUow,
    user: AuthenticatedUser,
    authorization: Authorization,
) -> CanvasStateModel:
    if body.database_id != database_id:
        raise DomainError("Path database_id must match body database_id")
    state = await SaveCanvasState(uow, authorization).execute(
        SaveCanvasStateRequest(
            database_id=database_id,
            account_id=user.account_id,
            requested_user_id=body.user_id,
            preferences=CanvasPreferences(
                viewport=body.viewport,
                grid_size=body.grid_size,
                snap_to_grid=body.snap_to_grid,
                show_relationship_labels=body.show_relationship_labels,
            ),
        )
    )
    return canvas_response(state)


@router.get("/{database_id}/groups", response_model=list[DiagramGroupModel])
async def list_groups(
    database_id: UUID,
    uow: CanvasUow,
    user: AuthenticatedUser,
    authorization: Authorization,
) -> list[DiagramGroupModel]:
    del user
    await authorization.require_database(database_id)
    return [group_response(group) for group in await ListGroups(uow).execute(database_id)]


@router.post(
    "/{database_id}/groups",
    response_model=DiagramGroupModel,
    status_code=status.HTTP_201_CREATED,
)
async def create_group(
    request: Request,
    database_id: UUID,
    body: DiagramGroupModel,
    uow: CanvasUow,
    user: AuthenticatedUser,
    authorization: Authorization,
) -> DiagramGroupModel:
    if body.database_id != database_id:
        raise DomainError("Path database_id must match body database_id")
    await authorization.require_database(database_id)
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
    request.state.audit_resource_id = str(group.id)
    return group_response(group)


@router.put("/{database_id}/groups/{group_id}", response_model=DiagramGroupModel)
async def update_group(
    database_id: UUID,
    group_id: UUID,
    body: DiagramGroupModel,
    uow: CanvasUow,
    user: AuthenticatedUser,
    authorization: Authorization,
) -> DiagramGroupModel:
    if body.id != group_id or body.database_id != database_id:
        raise DomainError("Path identifiers must match body identifiers")
    await authorization.require_database(database_id)
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
    uow: CanvasUow,
    user: AuthenticatedUser,
    authorization: Authorization,
) -> Response:
    await authorization.require_database(database_id)
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
    uow: CanvasUow,
    authorization: Authorization,
) -> list[DiagramNoteModel]:
    notes = await ListNotes(uow, authorization).execute(database_id)
    return [note_response(note) for note in notes]


@router.post(
    "/{database_id}/notes",
    response_model=DiagramNoteModel,
    status_code=status.HTTP_201_CREATED,
)
async def create_note(
    request: Request,
    database_id: UUID,
    body: DiagramNoteModel,
    uow: CanvasUow,
    user: AuthenticatedUser,
    authorization: Authorization,
) -> DiagramNoteModel:
    if body.database_id != database_id:
        raise DomainError("Path database_id must match body database_id")
    note = await CreateNote(uow, authorization).execute(
        CreateNoteRequest(
            database_id=database_id,
            note_id=body.id,
            attributes=note_attributes(body),
            author_id=user.account_id,
        )
    )
    request.state.audit_resource_id = str(note.id)
    return note_response(note)


@router.put("/{database_id}/notes/{note_id}", response_model=DiagramNoteModel)
async def update_note(
    database_id: UUID,
    note_id: UUID,
    body: DiagramNoteModel,
    uow: CanvasUow,
    authorization: Authorization,
) -> DiagramNoteModel:
    if body.id != note_id or body.database_id != database_id:
        raise DomainError("Path identifiers must match body identifiers")
    note = await UpdateNote(uow, authorization).execute(
        UpdateNoteRequest(
            database_id=database_id,
            note_id=note_id,
            attributes=note_attributes(body),
        )
    )
    return note_response(note)


@router.delete(
    "/{database_id}/notes/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_note(
    database_id: UUID,
    note_id: UUID,
    uow: CanvasUow,
    authorization: Authorization,
) -> Response:
    await DeleteNote(uow, authorization).execute(
        NoteRequest(database_id=database_id, note_id=note_id)
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
