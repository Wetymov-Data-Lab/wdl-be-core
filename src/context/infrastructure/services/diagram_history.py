"""Per-user undo/redo journal of diagram changes.

Every recorded request stores only the rows it changed, with their state before
and after it. Rows are compared on whole-diagram snapshots, so database-level
cascades (for example columns removed together with their table) are captured
without per-entity code.
"""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Select, Table, Uuid, delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from common.exceptions.exceptions import HistoryConflictError
from context.infrastructure.schemas.canvas import DiagramGroups, DiagramGroupTables, DiagramNotes
from context.infrastructure.schemas.database import (
    Columns,
    DiagramIndexColumns,
    DiagramIndexes,
    RelationshipColumns,
    Relationships,
    Tables,
)
from context.infrastructure.schemas.history import DiagramHistoryEntries
from infrastructure.database.base import Base

HISTORY_LIMIT = 50

Row = dict[str, Any]
RowKey = tuple[str, str]

def _table(model: type[Base]) -> Table:
    return Base.metadata.tables[model.__tablename__]


_tables = _table(Tables)
_columns = _table(Columns)
_indexes = _table(DiagramIndexes)
_index_columns = _table(DiagramIndexColumns)
_relationships = _table(Relationships)
_relationship_columns = _table(RelationshipColumns)
_groups = _table(DiagramGroups)
_group_tables = _table(DiagramGroupTables)
_notes = _table(DiagramNotes)


def _scoped(table: Table) -> Callable[[UUID], Select[Any]]:
    return lambda database_id: select(table).where(table.c.database_id == database_id)


def _of_tables(table: Table) -> Callable[[UUID], Select[Any]]:
    return lambda database_id: (
        select(table)
        .join(_tables, _tables.c.id == table.c.table_id)
        .where(_tables.c.database_id == database_id)
    )


# Parent tables go first: inserts follow this order, deletes run in reverse.
_TRACKED: tuple[tuple[Table, Callable[[UUID], Select[Any]]], ...] = (
    (_tables, _scoped(_tables)),
    (_columns, _of_tables(_columns)),
    (_indexes, _of_tables(_indexes)),
    (
        _index_columns,
        lambda database_id: select(_index_columns)
        .join(_indexes, _indexes.c.id == _index_columns.c.index_id)
        .join(_tables, _tables.c.id == _indexes.c.table_id)
        .where(_tables.c.database_id == database_id),
    ),
    (_relationships, _scoped(_relationships)),
    (
        _relationship_columns,
        lambda database_id: select(_relationship_columns)
        .join(_relationships, _relationships.c.id == _relationship_columns.c.relationship_id)
        .where(_relationships.c.database_id == database_id),
    ),
    (_groups, _scoped(_groups)),
    (
        _group_tables,
        lambda database_id: select(_group_tables)
        .join(_groups, _groups.c.id == _group_tables.c.group_id)
        .where(_groups.c.database_id == database_id),
    ),
    (_notes, _scoped(_notes)),
)
_BY_NAME = {table.name: table for table, _ in _TRACKED}
_ORDER = {table.name: position for position, (table, _) in enumerate(_TRACKED)}


@dataclass(frozen=True, slots=True)
class HistoryState:
    undo_action: str | None
    redo_action: str | None


def to_json(table: Table, row: Any) -> Row:
    values: Row = {}
    for column in table.columns:
        value = row._mapping[column]
        if isinstance(value, UUID):
            value = str(value)
        elif isinstance(value, datetime):
            value = value.isoformat()
        values[column.name] = value
    return values


def from_json(table: Table, values: Row) -> Row:
    restored: Row = {}
    for column in table.columns:
        value = values[column.name]
        if value is not None and isinstance(column.type, Uuid):
            value = UUID(value)
        elif value is not None and isinstance(column.type, DateTime):
            value = datetime.fromisoformat(value)
        restored[column.name] = value
    return restored


def diff(before: dict[RowKey, Row], after: dict[RowKey, Row]) -> list[Row]:
    keys = sorted(before.keys() | after.keys(), key=lambda key: (_ORDER[key[0]], key[1]))
    return [
        {"table": key[0], "id": key[1], "before": before.get(key), "after": after.get(key)}
        for key in keys
        if before.get(key) != after.get(key)
    ]


class DiagramHistory:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def snapshot(self, database_id: UUID) -> dict[RowKey, Row]:
        rows: dict[RowKey, Row] = {}
        for table, query in _TRACKED:
            for row in (await self._session.execute(query(database_id))).all():
                values = to_json(table, row)
                rows[(table.name, values["id"])] = values
        return rows

    @asynccontextmanager
    async def record(
        self, database_id: UUID | None, actor_id: UUID, action: str
    ) -> AsyncIterator[None]:
        """Journal the rows changed inside the block as one undoable step."""
        if database_id is None:
            yield
            return
        await self._session.flush()
        before = await self.snapshot(database_id)
        yield
        await self._session.flush()
        changes = diff(before, await self.snapshot(database_id))
        if not changes:
            return
        await self._session.execute(
            delete(DiagramHistoryEntries).where(
                *self._owned(database_id, actor_id), DiagramHistoryEntries.is_undone.is_(True)
            )
        )
        self._session.add(
            DiagramHistoryEntries(
                id=uuid4(),
                database_id=database_id,
                actor_id=actor_id,
                action=action,
                changes=changes,
                is_undone=False,
            )
        )
        await self._session.flush()
        kept = (
            select(DiagramHistoryEntries.id)
            .where(*self._owned(database_id, actor_id))
            .order_by(DiagramHistoryEntries.created_at.desc())
            .limit(HISTORY_LIMIT)
        )
        await self._session.execute(
            delete(DiagramHistoryEntries).where(
                *self._owned(database_id, actor_id), DiagramHistoryEntries.id.not_in(kept)
            )
        )

    async def state(self, database_id: UUID, actor_id: UUID) -> HistoryState:
        undo = await self._top(database_id, actor_id, undone=False)
        redo = await self._top(database_id, actor_id, undone=True)
        return HistoryState(
            undo_action=None if undo is None else undo.action,
            redo_action=None if redo is None else redo.action,
        )

    async def undo(self, database_id: UUID, actor_id: UUID) -> HistoryState:
        entry = await self._top(database_id, actor_id, undone=False)
        if entry is None:
            raise HistoryConflictError("Nothing to undo")
        await self._apply(entry, expected="after", target="before", undone=True)
        return await self.state(database_id, actor_id)

    async def redo(self, database_id: UUID, actor_id: UUID) -> HistoryState:
        entry = await self._top(database_id, actor_id, undone=True)
        if entry is None:
            raise HistoryConflictError("Nothing to redo")
        await self._apply(entry, expected="before", target="after", undone=False)
        return await self.state(database_id, actor_id)

    async def database_of_table(self, table_id: UUID) -> UUID | None:
        database_id: UUID | None = await self._session.scalar(
            select(Tables.database_id).where(Tables.id == table_id)
        )
        return database_id

    async def database_of_column(self, column_id: UUID) -> UUID | None:
        database_id: UUID | None = await self._session.scalar(
            select(Tables.database_id)
            .join(Columns, Columns.table_id == Tables.id)
            .where(Columns.id == column_id)
        )
        return database_id

    async def database_of_index(self, index_id: UUID) -> UUID | None:
        database_id: UUID | None = await self._session.scalar(
            select(Tables.database_id)
            .join(DiagramIndexes, DiagramIndexes.table_id == Tables.id)
            .where(DiagramIndexes.id == index_id)
        )
        return database_id

    async def database_of_relationship(self, relationship_id: UUID) -> UUID | None:
        database_id: UUID | None = await self._session.scalar(
            select(Relationships.database_id).where(Relationships.id == relationship_id)
        )
        return database_id

    async def _apply(
        self, entry: DiagramHistoryEntries, *, expected: str, target: str, undone: bool
    ) -> None:
        entry_id, changes = entry.id, entry.changes
        current = await self.snapshot(entry.database_id)
        for change in changes:
            if current.get((change["table"], change["id"])) != change[expected]:
                raise HistoryConflictError(
                    "The diagram was changed by someone else after this step; "
                    "it can no longer be applied"
                )
        ordered = sorted(changes, key=lambda change: _ORDER[change["table"]])
        for change in reversed(ordered):
            if change[target] is None:
                table = _BY_NAME[change["table"]]
                await self._session.execute(delete(table).where(table.c.id == UUID(change["id"])))
        for change in ordered:
            table = _BY_NAME[change["table"]]
            if change[target] is None:
                continue
            values = from_json(table, change[target])
            if change[expected] is None:
                await self._session.execute(insert(table).values(values))
            else:
                await self._session.execute(
                    update(table).where(table.c.id == values["id"]).values(values)
                )
        await self._session.execute(
            update(DiagramHistoryEntries)
            .where(DiagramHistoryEntries.id == entry_id)
            .values(is_undone=undone)
        )
        # Core statements bypass the identity map; drop ORM copies loaded earlier.
        self._session.expire_all()

    async def _top(
        self, database_id: UUID, actor_id: UUID, *, undone: bool
    ) -> DiagramHistoryEntries | None:
        created_at = DiagramHistoryEntries.created_at
        entry: DiagramHistoryEntries | None = await self._session.scalar(
            select(DiagramHistoryEntries)
            .where(*self._owned(database_id, actor_id), DiagramHistoryEntries.is_undone.is_(undone))
            .order_by(created_at.asc() if undone else created_at.desc())
            .limit(1)
        )
        return entry

    @staticmethod
    def _owned(database_id: UUID, actor_id: UUID) -> tuple[Any, ...]:
        return (
            DiagramHistoryEntries.database_id == database_id,
            DiagramHistoryEntries.actor_id == actor_id,
        )
