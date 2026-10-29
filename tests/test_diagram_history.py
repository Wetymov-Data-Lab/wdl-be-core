import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import context.infrastructure.schemas  # noqa: F401
from common.exceptions.exceptions import HistoryConflictError
from context.infrastructure.schemas.database import (
    Columns,
    Databases,
    DiagramIndexColumns,
    DiagramIndexes,
    Tables,
)
from context.infrastructure.schemas.history import DiagramHistoryEntries
from context.infrastructure.schemas.project import Projects
from context.infrastructure.schemas.realm import RealmSchema
from context.infrastructure.services.diagram_history import (
    HISTORY_LIMIT,
    DiagramHistory,
    diff,
    from_json,
    to_json,
)
from infrastructure.database.base import Base

ACTOR = UUID(int=1)
OTHER = UUID(int=2)
NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_diff_keeps_only_changed_rows_parents_first() -> None:
    table = {"id": "t", "name": "users"}
    column = {"id": "c", "name": "id"}
    before = {("tables", "t"): table, ("columns", "c"): column, ("tables", "u"): {"id": "u"}}
    after = {("tables", "u"): {"id": "u"}, ("tables", "t"): {**table, "name": "accounts"}}

    changes = diff(before, after)

    assert [(change["table"], change["id"]) for change in changes] == [
        ("tables", "t"),
        ("columns", "c"),
    ]
    assert changes[0]["after"]["name"] == "accounts"
    assert changes[1]["after"] is None


def test_row_json_round_trip_restores_uuid_and_datetime() -> None:
    table = Base.metadata.tables["tables"]
    values = {column.name: None for column in table.columns}
    values.update(id=uuid4(), database_id=uuid4(), author_id=ACTOR, created_at=NOW, checks=[])

    class Row:
        _mapping = {table.c[name]: value for name, value in values.items()}

    stored = to_json(table, Row())

    assert stored["id"] == str(values["id"])
    assert stored["created_at"] == NOW.isoformat()
    assert from_json(table, stored) == values


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    dsn = os.environ.get("WDL_HISTORY_TEST_DSN")
    if not dsn:
        pytest.skip("Set WDL_HISTORY_TEST_DSN to an isolated disposable PostgreSQL database")
    engine = create_async_engine(dsn)
    async with engine.begin() as connection:
        await connection.execute(text("DROP SCHEMA public CASCADE"))
        await connection.execute(text("CREATE SCHEMA public"))
        await connection.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        yield session
    await engine.dispose()


async def make_database(session: AsyncSession) -> UUID:
    realm_id, project_id, database_id = uuid4(), uuid4(), uuid4()
    session.add(
        RealmSchema(id=realm_id, name="r", slug="r", created_at=NOW, author_id=ACTOR)
    )
    await session.flush()
    session.add(Projects(id=project_id, name="p", realm_id=realm_id, author_id=ACTOR))
    await session.flush()
    session.add(
        Databases(id=database_id, name="d", project_id=project_id, type="psql", author_id=ACTOR)
    )
    await session.flush()
    return database_id


def new_table(database_id: UUID, name: str) -> Tables:
    return Tables(id=uuid4(), database_id=database_id, name=name, author_id=ACTOR, checks=[])


async def count(session: AsyncSession, model: type[Base]) -> int:
    return int(await session.scalar(select(func.count()).select_from(model)) or 0)


async def test_undo_restores_cascaded_rows_and_redo_reapplies(session: AsyncSession) -> None:
    history = DiagramHistory(session)
    database_id = await make_database(session)
    table = new_table(database_id, "users")
    async with history.record(database_id, ACTOR, "table.create"):
        session.add(table)
    async with history.record(database_id, ACTOR, "column.create"):
        session.add(Columns(id=uuid4(), table_id=table.id, name="id", type="uuid", author_id=ACTOR))
    async with history.record(database_id, ACTOR, "table.delete"):
        await session.execute(delete(Tables).where(Tables.id == table.id))
    assert await count(session, Columns) == 0

    state = await history.undo(database_id, ACTOR)

    assert (await count(session, Tables), await count(session, Columns)) == (1, 1)
    assert (state.undo_action, state.redo_action) == ("column.create", "table.delete")

    state = await history.redo(database_id, ACTOR)

    assert (await count(session, Tables), await count(session, Columns)) == (0, 0)
    assert (state.undo_action, state.redo_action) == ("table.delete", None)


async def test_new_change_clears_redo_and_history_is_per_user(session: AsyncSession) -> None:
    history = DiagramHistory(session)
    database_id = await make_database(session)
    async with history.record(database_id, ACTOR, "table.create"):
        session.add(new_table(database_id, "users"))
    await history.undo(database_id, ACTOR)
    async with history.record(database_id, ACTOR, "table.create"):
        session.add(new_table(database_id, "orders"))
    async with history.record(database_id, OTHER, "table.create"):
        session.add(new_table(database_id, "audit"))

    mine = await history.state(database_id, ACTOR)
    theirs = await history.state(database_id, OTHER)

    assert (mine.undo_action, mine.redo_action) == ("table.create", None)
    assert (theirs.undo_action, theirs.redo_action) == ("table.create", None)
    with pytest.raises(HistoryConflictError):
        await history.redo(database_id, ACTOR)


async def test_undo_is_refused_after_someone_else_changed_the_rows(session: AsyncSession) -> None:
    history = DiagramHistory(session)
    database_id = await make_database(session)
    table = new_table(database_id, "users")
    async with history.record(database_id, ACTOR, "table.create"):
        session.add(table)
    async with history.record(database_id, OTHER, "table.update"):
        await session.execute(update(Tables).where(Tables.id == table.id).values(name="accounts"))

    with pytest.raises(HistoryConflictError):
        await history.undo(database_id, ACTOR)
    assert await count(session, Tables) == 1


async def test_only_the_latest_steps_are_kept(session: AsyncSession) -> None:
    history = DiagramHistory(session)
    database_id = await make_database(session)
    table = new_table(database_id, "users")
    async with history.record(database_id, ACTOR, "table.create"):
        session.add(table)
    for step in range(HISTORY_LIMIT + 5):
        async with history.record(database_id, ACTOR, "table.update"):
            await session.execute(
                update(Tables).where(Tables.id == table.id).values(sort_order=step + 1)
            )

    assert await count(session, DiagramHistoryEntries) == HISTORY_LIMIT


async def test_change_without_effect_is_not_recorded(session: AsyncSession) -> None:
    history = DiagramHistory(session)
    database_id = await make_database(session)
    async with history.record(database_id, ACTOR, "table.update"):
        pass

    assert await count(session, DiagramHistoryEntries) == 0


async def test_undo_of_reordered_index_columns_respects_unique_positions(
    session: AsyncSession,
) -> None:
    history = DiagramHistory(session)
    database_id = await make_database(session)
    table = new_table(database_id, "users")
    session.add(table)
    await session.flush()
    first, second = (
        Columns(id=uuid4(), table_id=table.id, name=name, type="uuid", author_id=ACTOR)
        for name in ("a", "b")
    )
    index_id = uuid4()
    session.add_all([first, second])
    await session.flush()
    session.add(DiagramIndexes(id=index_id, table_id=table.id, type="index", author_id=ACTOR))
    await session.flush()

    def members(order: tuple[Columns, ...]) -> list[DiagramIndexColumns]:
        return [
            DiagramIndexColumns(
                id=uuid4(), index_id=index_id, column_id=column.id, sort_order="asc", position=i
            )
            for i, column in enumerate(order)
        ]

    session.add_all(members((first, second)))
    await session.flush()
    expected = [first.id, second.id]
    async with history.record(database_id, ACTOR, "index.update"):
        await session.execute(
            delete(DiagramIndexColumns).where(DiagramIndexColumns.index_id == index_id)
        )
        await session.flush()
        session.add_all(members((second, first)))

    await history.undo(database_id, ACTOR)

    order = (
        await session.scalars(
            select(DiagramIndexColumns.column_id).order_by(DiagramIndexColumns.position)
        )
    ).all()
    assert order == expected
