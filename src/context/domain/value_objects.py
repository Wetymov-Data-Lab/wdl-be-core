from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class ValueObject(ABC):
    """Immutable domain value compared by its attributes."""

    def __post_init__(self) -> None:
        self.validate()

    @abstractmethod
    def validate(self) -> None:
        """Raise a domain exception when the value is invalid."""
