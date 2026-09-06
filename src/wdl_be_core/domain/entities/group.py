import re
from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from uuid import UUID, uuid4

from wdl_be_core.domain.entities.base import Entity
from wdl_be_core.domain.exceptions import AuthorizationError, DomainError
from wdl_be_core.domain.value_objects import ValueObject


@dataclass(frozen=True, kw_only=True)
class GroupName(ValueObject):
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", self.value.strip())
        super().__post_init__()

    def validate(self) -> None:
        if not self.value:
            raise DomainError("Group name must not be empty")
        if len(self.value) > 255:
            raise DomainError("Group name must not exceed 255 characters")


@dataclass(frozen=True, kw_only=True)
class CanvasPoint(ValueObject):
    x: float
    y: float

    def validate(self) -> None:
        if not (float("-inf") < self.x < float("inf")):
            raise DomainError("Group x coordinate must be finite")
        if not (float("-inf") < self.y < float("inf")):
            raise DomainError("Group y coordinate must be finite")


@dataclass(frozen=True, kw_only=True)
class GroupSize(ValueObject):
    width: float
    height: float

    def validate(self) -> None:
        if not isfinite(self.width) or not isfinite(self.height):
            raise DomainError("Group width and height must be finite")
        if self.width <= 0 or self.height <= 0:
            raise DomainError("Group width and height must be positive")


@dataclass(frozen=True, kw_only=True)
class CanvasColor(ValueObject):
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", self.value.upper())
        super().__post_init__()

    def validate(self) -> None:
        if not re.fullmatch(r"#[0-9A-F]{6}", self.value):
            raise DomainError("Group color must use #RRGGBB format")


@dataclass(eq=False, kw_only=True)
class DiagramGroup(Entity[UUID]):
    database_id: UUID
    name: GroupName
    position: CanvasPoint
    size: GroupSize
    color: CanvasColor | None
    is_collapsed: bool
    table_ids: tuple[UUID, ...]
    author_id: UUID
    created_at: datetime
    updated_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        database_id: UUID,
        name: str,
        x: float,
        y: float,
        width: float,
        height: float,
        color: str | None,
        is_collapsed: bool,
        table_ids: list[UUID],
        author_id: UUID,
        created_at: datetime,
        group_id: UUID | None = None,
    ) -> "DiagramGroup":
        return cls(
            id=group_id or uuid4(),
            database_id=database_id,
            name=GroupName(value=name),
            position=CanvasPoint(x=x, y=y),
            size=GroupSize(width=width, height=height),
            color=None if color is None else CanvasColor(value=color),
            is_collapsed=is_collapsed,
            table_ids=cls._unique_table_ids(table_ids),
            author_id=author_id,
            created_at=created_at,
        )

    def update(
        self,
        *,
        name: str,
        x: float,
        y: float,
        width: float,
        height: float,
        color: str | None,
        is_collapsed: bool,
        table_ids: list[UUID],
        updated_by: UUID,
        updated_at: datetime,
    ) -> None:
        self.ensure_owned_by(updated_by)
        self.name = GroupName(value=name)
        self.position = CanvasPoint(x=x, y=y)
        self.size = GroupSize(width=width, height=height)
        self.color = None if color is None else CanvasColor(value=color)
        self.is_collapsed = is_collapsed
        self.table_ids = self._unique_table_ids(table_ids)
        self.updated_at = updated_at

    def ensure_owned_by(self, user_id: UUID) -> None:
        if self.author_id != user_id:
            raise AuthorizationError("Only the group author can modify it")

    @staticmethod
    def _unique_table_ids(table_ids: list[UUID]) -> tuple[UUID, ...]:
        if len(table_ids) != len(set(table_ids)):
            raise DomainError("A table cannot occur in a group more than once")
        return tuple(table_ids)
