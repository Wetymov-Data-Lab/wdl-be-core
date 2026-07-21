from dataclasses import dataclass


@dataclass(eq=False, kw_only=True)
class Entity[EntityId]:
    """Base class for domain objects that have identity."""

    id: EntityId

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash((self.__class__, self.id))
