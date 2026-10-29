from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from wdl_shared.schemas.engine.models.canvas import DiagramHistoryModel

from common.services.identity import CurrentUser
from context.application.services.history import (
    GetHistoryState,
    HistoryRequest,
    RedoChange,
    UndoChange,
)
from context.infrastructure.guards.authentication import get_current_user
from context.infrastructure.guards.authorization import get_authorization_service
from context.infrastructure.repositories.dependencies import get_diagram_history
from context.infrastructure.services.authorization import AuthorizationService
from context.infrastructure.services.diagram_history import DiagramHistory, HistoryState

router = APIRouter(
    prefix="/databases/{database_id}/history",
    tags=["diagram history"],
    dependencies=[Depends(get_current_user)],
)
AuthenticatedUser = Annotated[CurrentUser, Depends(get_current_user)]
Authorization = Annotated[AuthorizationService, Depends(get_authorization_service)]
History = Annotated[DiagramHistory, Depends(get_diagram_history)]


def history_response(state: HistoryState) -> DiagramHistoryModel:
    return DiagramHistoryModel(undo_action=state.undo_action, redo_action=state.redo_action)


@router.get("", response_model=DiagramHistoryModel)
async def get_history(
    database_id: UUID,
    user: AuthenticatedUser,
    history: History,
    authorization: Authorization,
) -> DiagramHistoryModel:
    state = await GetHistoryState(history, authorization).execute(
        HistoryRequest(database_id=database_id, actor_id=user.account_id)
    )
    return history_response(state)


@router.post("/undo", response_model=DiagramHistoryModel)
async def undo_change(
    database_id: UUID,
    user: AuthenticatedUser,
    history: History,
    authorization: Authorization,
) -> DiagramHistoryModel:
    state = await UndoChange(history, authorization).execute(
        HistoryRequest(database_id=database_id, actor_id=user.account_id)
    )
    return history_response(state)


@router.post("/redo", response_model=DiagramHistoryModel)
async def redo_change(
    database_id: UUID,
    user: AuthenticatedUser,
    history: History,
    authorization: Authorization,
) -> DiagramHistoryModel:
    state = await RedoChange(history, authorization).execute(
        HistoryRequest(database_id=database_id, actor_id=user.account_id)
    )
    return history_response(state)
