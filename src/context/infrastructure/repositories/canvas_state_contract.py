from abc import abstractmethod
from uuid import UUID

from common.mixins.base_repository import Repository
from common.unit_of_work import UnitOfWork
from context.domain.entities.canvas_state import CanvasState


class CanvasStateRepository(Repository[CanvasState, UUID]):
    @abstractmethod
    async def find(self, database_id: UUID, user_id: UUID | None) -> CanvasState | None: ...

    @abstractmethod
    async def save(self, state: CanvasState) -> None: ...


class CanvasStateUnitOfWork(UnitOfWork):
    canvas_states: CanvasStateRepository
