from dataclasses import dataclass
from uuid import UUID, uuid4

from wdl_shared.schemas.engine.models.canvas import CanvasViewport

from common.exceptions.exceptions import DomainError
from context.domain.entities.base import Entity


@dataclass(frozen=True, slots=True, kw_only=True)
class CanvasPreferences:
    """Presentation preferences saved for a database diagram."""

    viewport: CanvasViewport
    grid_size: int
    snap_to_grid: bool
    show_relationship_labels: bool


@dataclass(eq=False, kw_only=True)
class CanvasState(Entity[UUID]):
    database_id: UUID
    user_id: UUID | None
    viewport: CanvasViewport
    grid_size: int
    snap_to_grid: bool
    show_relationship_labels: bool

    @classmethod
    def create(
        cls,
        *,
        database_id: UUID,
        user_id: UUID | None,
        preferences: CanvasPreferences,
        state_id: UUID | None = None,
    ) -> "CanvasState":
        return cls(
            id=state_id or uuid4(),
            database_id=database_id,
            user_id=user_id,
            viewport=preferences.viewport,
            grid_size=preferences.grid_size,
            snap_to_grid=preferences.snap_to_grid,
            show_relationship_labels=preferences.show_relationship_labels,
        )

    @staticmethod
    def ensure_owner(requested_user_id: UUID | None, account_id: UUID) -> None:
        if requested_user_id not in (None, account_id):
            raise DomainError("Canvas user_id must match the authenticated account")

    def apply(self, preferences: CanvasPreferences) -> None:
        self.viewport = preferences.viewport
        self.grid_size = preferences.grid_size
        self.snap_to_grid = preferences.snap_to_grid
        self.show_relationship_labels = preferences.show_relationship_labels
