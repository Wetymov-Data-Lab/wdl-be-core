from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]

T = TypeVar("T")
type Operation[T] = Callable[[AsyncSession], Awaitable[T]]


@dataclass(frozen=True, slots=True)
class OutboxEvent:
    topic: str
    event_type: str
    payload: Mapping[str, Any]
    aggregate_type: str | None = None
    aggregate_id: str | UUID | None = None
    headers: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AuditEntry:
    action: str
    resource_type: str
    resource_id: str | UUID | None = None
    actor_id: str | UUID | None = None
    input: Mapping[str, Any] | None = None
    changes: Mapping[str, Any] | None = None
    context: Mapping[str, Any] = field(default_factory=dict)
    trace_id: str | None = None


type OutboxSource[T] = (
    OutboxEvent
    | Iterable[OutboxEvent]
    | Callable[[T], OutboxEvent | Iterable[OutboxEvent] | None]
    | None
)
