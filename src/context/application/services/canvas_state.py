from dataclasses import dataclass
from uuid import UUID

from common.exceptions.exceptions import EntityNotFoundError
from common.unit_of_work import commit_or_conflict
from context.application.use_case import UseCase
from context.domain.entities.canvas_state import CanvasPreferences, CanvasState
from context.infrastructure.repositories.canvas_state_contract import CanvasStateUnitOfWork
from context.infrastructure.services.authorization import AuthorizationService


@dataclass(frozen=True, slots=True)
class GetCanvasStateRequest:
    database_id: UUID
    account_id: UUID


@dataclass(frozen=True, slots=True)
class SaveCanvasStateRequest:
    database_id: UUID
    account_id: UUID
    requested_user_id: UUID | None
    preferences: CanvasPreferences


class GetCanvasState(UseCase[GetCanvasStateRequest, CanvasState]):
    def __init__(self, uow: CanvasStateUnitOfWork, authorization: AuthorizationService) -> None:
        self._uow = uow
        self._authorization = authorization

    async def execute(self, request: GetCanvasStateRequest) -> CanvasState:
        await self._authorization.require_database(request.database_id)
        async with self._uow:
            state = await self._uow.canvas_states.find(request.database_id, request.account_id)
            if state is None:
                raise EntityNotFoundError(
                    f"Canvas state for database {request.database_id} was not found"
                )
            return state


class SaveCanvasState(UseCase[SaveCanvasStateRequest, CanvasState]):
    def __init__(self, uow: CanvasStateUnitOfWork, authorization: AuthorizationService) -> None:
        self._uow = uow
        self._authorization = authorization

    async def execute(self, request: SaveCanvasStateRequest) -> CanvasState:
        await self._authorization.require_database(request.database_id)
        CanvasState.ensure_owner(request.requested_user_id, request.account_id)
        async with self._uow:
            state = await self._uow.canvas_states.find(request.database_id, request.account_id)
            if state is None:
                state = CanvasState.create(
                    database_id=request.database_id,
                    user_id=request.account_id,
                    preferences=request.preferences,
                )
                await self._uow.canvas_states.add(state)
            else:
                state.apply(request.preferences)
                await self._uow.canvas_states.save(state)
            await commit_or_conflict(self._uow, "Canvas state already exists")
            return state
