from dataclasses import dataclass
from uuid import UUID

from context.application.use_case import UseCase
from context.infrastructure.services.authorization import AuthorizationService
from context.infrastructure.services.diagram_history import DiagramHistory, HistoryState


@dataclass(frozen=True, slots=True)
class HistoryRequest:
    database_id: UUID
    actor_id: UUID


class GetHistoryState(UseCase[HistoryRequest, HistoryState]):
    def __init__(self, history: DiagramHistory, authorization: AuthorizationService) -> None:
        self._history = history
        self._authorization = authorization

    async def execute(self, request: HistoryRequest) -> HistoryState:
        await self._authorization.require_database(request.database_id)
        return await self._history.state(request.database_id, request.actor_id)


class UndoChange(UseCase[HistoryRequest, HistoryState]):
    def __init__(self, history: DiagramHistory, authorization: AuthorizationService) -> None:
        self._history = history
        self._authorization = authorization

    async def execute(self, request: HistoryRequest) -> HistoryState:
        await self._authorization.require_database(request.database_id)
        return await self._history.undo(request.database_id, request.actor_id)


class RedoChange(UseCase[HistoryRequest, HistoryState]):
    def __init__(self, history: DiagramHistory, authorization: AuthorizationService) -> None:
        self._history = history
        self._authorization = authorization

    async def execute(self, request: HistoryRequest) -> HistoryState:
        await self._authorization.require_database(request.database_id)
        return await self._history.redo(request.database_id, request.actor_id)
