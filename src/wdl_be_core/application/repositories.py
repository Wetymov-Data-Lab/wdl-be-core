from abc import ABC, abstractmethod
from typing import Any

from wdl_be_core.domain.entities.base import Entity


class Repository[EntityT: Entity[Any], EntityId](ABC):
    """Persistence contract used by application use cases."""

    @abstractmethod
    async def get(self, entity_id: EntityId) -> EntityT | None:
        """Return an entity by identity or None."""

    @abstractmethod
    async def add(self, entity: EntityT) -> None:
        """Add an entity to the current unit of work."""

    @abstractmethod
    async def remove(self, entity: EntityT) -> None:
        """Remove an entity in the current unit of work."""
