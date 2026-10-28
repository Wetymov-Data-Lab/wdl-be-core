from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from context.domain.entities.canvas_state import CanvasState
from context.infrastructure.repositories.canvas_state_contract import (
    CanvasStateRepository as AbstractCanvasStateRepository,
)
from context.infrastructure.schemas.canvas import CanvasStates


class CanvasStateRepository(AbstractCanvasStateRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, entity_id: UUID) -> CanvasState | None:
        model = await self._session.get(CanvasStates, entity_id)
        return None if model is None else self._to_domain(model)

    async def find(self, database_id: UUID, user_id: UUID | None) -> CanvasState | None:
        query = select(CanvasStates).where(CanvasStates.database_id == database_id)
        query = (
            query.where(CanvasStates.user_id.is_(None))
            if user_id is None
            else query.where(CanvasStates.user_id == user_id)
        )
        model = await self._session.scalar(query)
        return None if model is None else self._to_domain(model)

    async def add(self, entity: CanvasState) -> None:
        model = CanvasStates(
            id=entity.id,
            database_id=entity.database_id,
            user_id=entity.user_id,
            grid_size=entity.grid_size,
            snap_to_grid=entity.snap_to_grid,
            show_relationship_labels=entity.show_relationship_labels,
        )
        model.viewport = entity.viewport
        self._session.add(model)

    async def save(self, state: CanvasState) -> None:
        model = await self._session.get_one(CanvasStates, state.id)
        model.viewport = state.viewport
        model.grid_size = state.grid_size
        model.snap_to_grid = state.snap_to_grid
        model.show_relationship_labels = state.show_relationship_labels

    async def remove(self, entity: CanvasState) -> None:
        await self._session.execute(delete(CanvasStates).where(CanvasStates.id == entity.id))

    @staticmethod
    def _to_domain(model: CanvasStates) -> CanvasState:
        return CanvasState(
            id=model.id,
            database_id=model.database_id,
            user_id=model.user_id,
            viewport=model.viewport,
            grid_size=model.grid_size,
            snap_to_grid=model.snap_to_grid,
            show_relationship_labels=model.show_relationship_labels,
        )
