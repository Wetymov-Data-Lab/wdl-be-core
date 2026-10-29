import asyncio
import os
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import asyncpg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from wdl_shared.schemas.engine.enums.database import (
    ColumnType,
    DataBaseName,
    IndexType,
    ReferentialAction,
    RelationshipCardinality,
    SortOrder,
)
from wdl_shared.schemas.engine.models.canvas import CanvasPosition

from common.exceptions.exceptions import SqlExportError
from common.services.identity import CurrentUser
from context.domain.entities.column import Column
from context.domain.entities.database import Database
from context.domain.entities.index import DiagramIndex, IndexColumn
from context.domain.entities.relationship import ColumnPair, Relationship
from context.domain.entities.table import Table, TableCheck
from context.domain.services.sql_export import SqlDiagram, generate_postgresql_sql
from context.infrastructure.guards.authentication import get_current_user
from context.infrastructure.repositories.column import ColumnRepository
from context.infrastructure.repositories.database import DatabaseRepository
from context.infrastructure.repositories.index import IndexRepository
from context.infrastructure.repositories.relationship import RelationshipRepository
from context.infrastructure.repositories.table import TableRepository
from context.infrastructure.schemas.database import Databases
from infrastructure.database.dependencies import get_database_session
from main import create_app

AUTHOR = UUID(int=999)
NOW = datetime(2026, 1, 1, tzinfo=UTC)


def database(**options: Any) -> Database:
    values: dict[str, Any] = dict(
        id=UUID(int=1),
        project_id=UUID(int=2),
        name="Test",
        type=DataBaseName.PSQL,
        notice=None,
        default_schema="wdl_export",
        charset=None,
        collation=None,
        author_id=AUTHOR,
        created_at=NOW,
    )
    values.update(options)
    return Database(**values)


def table(number: int, database_id: UUID, name: str, **options: Any) -> Table:
    values: dict[str, Any] = dict(
        id=UUID(int=number),
        database_id=database_id,
        name=name,
        schema_name=None,
        description=None,
        notice=None,
        color=None,
        position=CanvasPosition(x=0, y=0),
        width=None,
        is_collapsed=False,
        sort_order=0,
        checks=(),
        author_id=AUTHOR,
        created_at=NOW,
    )
    values.update(options)
    return Table(**values)


def column(table_id: UUID, number: int, name: str, **options: Any) -> Column:
    values: dict[str, Any] = dict(
        id=UUID(int=number),
        table_id=table_id,
        name=name,
        type=ColumnType.INTEGER,
        custom_type=None,
        length=None,
        precision=None,
        scale=None,
        array_dimensions=0,
        nullable=True,
        primary_key=False,
        unique=False,
        auto_increment=False,
        unsigned=False,
        default=None,
        check=None,
        enum_values=[],
        sort_order=number,
        notice=None,
        author_id=AUTHOR,
        created_at=NOW,
    )
    values.update(options)
    values["type"] = ColumnType(values["type"])
    return Column(**values)


def member(column_id: UUID, position: int, sort_order: str = "asc") -> IndexColumn:
    return IndexColumn(column_id=column_id, sort_order=SortOrder(sort_order), position=position)


def index(number: int, table_id: UUID, name: str | None, **options: Any) -> DiagramIndex:
    values: dict[str, Any] = dict(
        id=UUID(int=number),
        table_id=table_id,
        name=name,
        type=IndexType.INDEX,
        columns=(),
        method=None,
        where=None,
        author_id=AUTHOR,
        created_at=NOW,
    )
    values.update(options)
    values["type"] = IndexType(values["type"])
    return DiagramIndex(**values)


def relationship(
    number: int,
    database_id: UUID,
    name: str,
    source: Table,
    target: Table,
    pairs: list[tuple[Column, Column]],
    on_delete: str = "no_action",
    on_update: str = "no_action",
) -> Relationship:
    return Relationship(
        id=UUID(int=number),
        database_id=database_id,
        name=name,
        source_table_id=source.id,
        target_table_id=target.id,
        columns=tuple(ColumnPair(source_column_id=a.id, target_column_id=b.id) for a, b in pairs),
        source_cardinality=RelationshipCardinality.ZERO_OR_MANY,
        target_cardinality=RelationshipCardinality.EXACTLY_ONE,
        on_delete=ReferentialAction(on_delete),
        on_update=ReferentialAction(on_update),
        waypoints=(),
        author_id=AUTHOR,
        created_at=NOW,
    )


@pytest.fixture
def diagram() -> SqlDiagram:
    owner = database()
    parent = table(10, owner.id, 'parent"quoted', sort_order=0, description="Owner's table")
    child = table(20, owner.id, "child", sort_order=1)
    parent_id = column(parent.id, 101, "id", primary_key=True, auto_increment=True)
    parent_region = column(parent.id, 102, "region", primary_key=True)
    child_id = column(child.id, 201, "id", primary_key=True)
    child_parent = column(child.id, 202, "parent_id")
    child_region = column(child.id, 203, "region")
    status = column(
        parent.id,
        103,
        "status",
        type="enum",
        enum_values=["draft", "it's ready", "x;--y"],
        default="'draft'",
        notice="Status's explanation",
    )
    amount = column(
        child.id,
        204,
        "amount",
        type="numeric",
        precision=12,
        scale=2,
        default="0",
        check='"amount" >= 0',
    )
    tags = column(child.id, 205, "tags", type="varchar", length=40, array_dimensions=2)
    amount_index = index(
        30,
        child.id,
        "child_amount_idx",
        method="btree",
        where='"amount" > 0',
        columns=(member(amount.id, 0, "desc"),),
    )
    fk = relationship(
        40,
        owner.id,
        "child_parent_fk",
        child,
        parent,
        [(child_parent, parent_id), (child_region, parent_region)],
        on_delete="set_null",
        on_update="cascade",
    )
    return SqlDiagram(
        owner,
        (child, parent),
        (parent_id, parent_region, status, child_id, child_parent, child_region, amount, tags),
        (amount_index,),
        (fk,),
    )


def test_sql_preserves_composite_keys_options_and_quoted_names(diagram: SqlDiagram) -> None:
    sql = generate_postgresql_sql(diagram)
    assert 'CREATE TABLE "wdl_export"."parent""quoted"' in sql
    assert 'PRIMARY KEY ("id", "region")' in sql
    assert 'FOREIGN KEY ("parent_id", "region")' in sql
    assert 'REFERENCES "wdl_export"."parent""quoted" ("id", "region")' in sql
    assert "ON DELETE SET NULL ON UPDATE CASCADE" in sql
    assert "GENERATED BY DEFAULT AS IDENTITY NOT NULL" in sql
    assert '"amount" NUMERIC(12, 2) DEFAULT 0 CHECK ("amount" >= 0)' in sql
    assert '"tags" VARCHAR(40)[][]' in sql
    assert '("amount" DESC) WHERE "amount" > 0' in sql
    assert "'it''s ready'" in sql
    assert "'Owner''s table'" in sql
    assert (
        sql.index("CREATE TYPE")
        < sql.index("CREATE TABLE")
        < sql.index("CREATE INDEX")
        < sql.index("ALTER TABLE")
    )
    assert sql.endswith("COMMIT;\n")
    assert sql == generate_postgresql_sql(
        replace(
            diagram,
            tables=tuple(reversed(diagram.tables)),
            columns=tuple(reversed(diagram.columns)),
        )
    )


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("string", "VARCHAR"),
        ("integer", "INTEGER"),
        ("float", "REAL"),
        ("boolean", "BOOLEAN"),
        ("date", "DATE"),
        ("datetime", "TIMESTAMP"),
        ("time", "TIME"),
        ("timestamp", "TIMESTAMP"),
        ("uuid", "UUID"),
        ("text", "TEXT"),
        ("char", "CHAR"),
        ("varchar", "VARCHAR"),
        ("smallint", "SMALLINT"),
        ("bigint", "BIGINT"),
        ("decimal", "NUMERIC"),
        ("numeric", "NUMERIC"),
        ("double", "DOUBLE PRECISION"),
        ("json", "JSON"),
        ("jsonb", "JSONB"),
        ("binary", "BYTEA"),
        ("blob", "BYTEA"),
    ],
)
def test_builtin_types(diagram: SqlDiagram, kind: str, expected: str) -> None:
    item = column(diagram.tables[0].id, 900, "value", type=kind)
    sql = generate_postgresql_sql(
        replace(
            diagram,
            columns=(item,),
            indexes=(),
            relationships=(),
        )
    )
    assert f'"value" {expected}' in sql


@pytest.mark.parametrize("kind", ["array", "custom", "geometry"])
def test_ambiguous_or_external_types_are_rejected(diagram: SqlDiagram, kind: str) -> None:
    item = column(diagram.tables[0].id, 900, "value", type=kind)
    with pytest.raises(SqlExportError, match="not supported"):
        generate_postgresql_sql(replace(diagram, columns=(item,)))


@pytest.mark.parametrize(
    "engine",
    ["mysql", "sqlite", "mongodb", "redis", "maria_db", "oracle", "sql_server", "cockroachdb"],
)
def test_other_dialects_do_not_receive_postgresql_sql(diagram: SqlDiagram, engine: str) -> None:
    diagram.database.type = DataBaseName(engine)
    with pytest.raises(SqlExportError, match="PostgreSQL"):
        generate_postgresql_sql(diagram)


@pytest.mark.parametrize(
    "bad",
    [
        "0; DROP TABLE users",
        "0 -- comment",
        "0 /* comment */",
        "0)",
        "(0",
        "'unterminated",
        "0, injected integer",
    ],
)
def test_statement_injection_and_invalid_expressions_are_rejected(
    diagram: SqlDiagram, bad: str
) -> None:
    diagram.columns[6].default = bad
    with pytest.raises(SqlExportError, match="expression|parentheses|quote"):
        generate_postgresql_sql(diagram)


def test_quoted_expression_literals_can_contain_separators(diagram: SqlDiagram) -> None:
    diagram.columns[2].default = "'x;--y'"
    assert "DEFAULT 'x;--y'" in generate_postgresql_sql(diagram)


def test_table_checks_are_exported_as_named_constraints(diagram: SqlDiagram) -> None:
    child = diagram.tables[0]
    child.checks = (
        TableCheck(name="child_range", expression="id > 0 AND id < 1000"),
        TableCheck(name=None, expression="id <> 5"),
    )
    sql = generate_postgresql_sql(diagram)
    assert 'CONSTRAINT "child_range" CHECK (id > 0 AND id < 1000)' in sql
    assert f'CONSTRAINT "wdl_ck_{child.id.hex}_1" CHECK (id <> 5)' in sql
    child.checks = (TableCheck(name=None, expression="0; DROP TABLE users"),)
    with pytest.raises(SqlExportError, match="expression"):
        generate_postgresql_sql(diagram)


def test_composite_primary_index_is_exported_and_set_null_respects_it(diagram: SqlDiagram) -> None:
    child = diagram.tables[0]
    pk = index(
        80, child.id, "child_pk", type="primary", columns=(member(diagram.columns[3].id, 0),)
    )
    updated = replace(diagram, indexes=(*diagram.indexes, pk))
    assert 'CONSTRAINT "child_pk" PRIMARY KEY ("id")' in generate_postgresql_sql(updated)
    diagram.columns[3].primary_key = False
    pk.columns = (member(diagram.columns[4].id, 0),)
    with pytest.raises(SqlExportError, match="SET NULL"):
        generate_postgresql_sql(updated)


def test_cycles_and_self_references_are_added_after_all_tables(diagram: SqlDiagram) -> None:
    parent, child = diagram.tables[1], diagram.tables[0]
    columns = diagram.columns
    self_fk = relationship(
        60, diagram.database.id, "self_fk", child, child, [(columns[4], columns[3])]
    )
    back_fk = relationship(
        70, diagram.database.id, "back_fk", parent, child, [(columns[0], columns[3])]
    )
    sql = generate_postgresql_sql(
        replace(diagram, relationships=(*diagram.relationships, self_fk, back_fk))
    )
    assert sql.count("ALTER TABLE") == 3
    assert sql.rindex("CREATE TABLE") < sql.index("ALTER TABLE")


def test_partial_unique_index_cannot_back_a_foreign_key(diagram: SqlDiagram) -> None:
    diagram.columns[0].primary_key = False
    diagram.columns[1].primary_key = False
    with pytest.raises(SqlExportError, match="unique key"):
        generate_postgresql_sql(diagram)


def test_foreign_key_cannot_export_columns_from_another_model(diagram: SqlDiagram) -> None:
    fk = diagram.relationships[0]
    fk.columns = (replace(fk.columns[0], target_column_id=uuid4()), *fk.columns[1:])
    with pytest.raises(SqlExportError, match="endpoint tables"):
        generate_postgresql_sql(diagram)


def test_long_identifiers_are_rejected_instead_of_truncated(diagram: SqlDiagram) -> None:
    diagram.tables[0].name = "я" * 32
    with pytest.raises(SqlExportError, match="63 UTF-8 bytes"):
        generate_postgresql_sql(diagram)


@pytest.mark.parametrize(("field", "value"), [("unsigned", True), ("auto_increment", True)])
def test_invalid_postgresql_column_options_are_rejected(
    diagram: SqlDiagram, field: str, value: bool
) -> None:
    setattr(diagram.columns[6], field, value)
    with pytest.raises(SqlExportError):
        generate_postgresql_sql(diagram)


def test_schema_wide_index_name_collision_is_rejected(diagram: SqlDiagram) -> None:
    diagram.indexes[0].name = diagram.tables[1].name
    with pytest.raises(SqlExportError, match="Duplicate PostgreSQL relation"):
        generate_postgresql_sql(diagram)


def test_empty_diagram_is_a_valid_empty_transaction(diagram: SqlDiagram) -> None:
    sql = generate_postgresql_sql(SqlDiagram(diagram.database))
    assert "CREATE TABLE" not in sql
    assert "BEGIN;" in sql and "COMMIT;" in sql


@pytest.fixture
def api(diagram: SqlDiagram):
    app = create_app()
    session = AsyncMock()
    mock_session_rows(session, orm_rows(diagram))

    async def database_session():
        yield session

    app.dependency_overrides[get_database_session] = database_session
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        account_id=UUID(int=500), session_id=UUID(int=501)
    )
    yield TestClient(app), session, app
    app.dependency_overrides.clear()


async def orm_rows_async(diagram: SqlDiagram) -> dict[str, Any]:
    session = Mock(spec=AsyncSession)
    for repository, entities in (
        (DatabaseRepository, (diagram.database,)),
        (TableRepository, diagram.tables),
        (ColumnRepository, diagram.columns),
        (IndexRepository, diagram.indexes),
        (RelationshipRepository, diagram.relationships),
    ):
        for entity in entities:
            await repository(session).add(entity)  # type: ignore[arg-type]
    for entity in diagram.indexes:
        await IndexRepository(session).add_columns(entity)
    for entity in diagram.relationships:
        await RelationshipRepository(session).add_columns(entity)
    added = [call.args[0] for call in session.add.call_args_list]
    children = [list(call.args[0]) for call in session.add_all.call_args_list]
    tables = len(diagram.tables)
    columns = tables + len(diagram.columns)
    indexes = columns + len(diagram.indexes)
    return {
        "database": added[0],
        "tables": tuple(added[1 : tables + 1]),
        "columns": tuple(added[tables + 1 : columns + 1]),
        "indexes": tuple(added[columns + 1 : indexes + 1]),
        "relationships": tuple(added[indexes + 1 :]),
        "index_columns": tuple(row for rows in children[: len(diagram.indexes)] for row in rows),
        "relationship_columns": tuple(
            row for rows in children[len(diagram.indexes) :] for row in rows
        ),
    }


def orm_rows(diagram: SqlDiagram) -> dict[str, Any]:
    """Store the domain model through the real repository mapping, as the database would."""
    return asyncio.run(orm_rows_async(diagram))


def mock_session_rows(session: AsyncMock, rows: dict[str, Any]) -> None:
    session.scalar.return_value = rows["database"]
    session.get.return_value = rows["database"]
    session.scalars.side_effect = [
        Mock(all=Mock(return_value=rows[key]))
        for key in (
            "tables",
            "columns",
            "indexes",
            "index_columns",
            "relationships",
            "relationship_columns",
        )
    ]


def test_api_returns_sql_attachment_and_scopes_all_queries(api, diagram: SqlDiagram) -> None:
    client, session, _ = api
    response = client.get(f"/databases/{diagram.database.id}/export/sql")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/sql; charset=utf-8"
    assert (
        response.headers["content-disposition"]
        == f'attachment; filename="wdl-{diagram.database.id}.sql"'
    )
    assert response.headers["cache-control"] == "no-store"
    assert response.text == generate_postgresql_sql(diagram)
    ownership = session.scalar.await_args.args[0].compile()
    assert UUID(int=500) in ownership.params.values()
    session.get.assert_awaited_once_with(Databases, diagram.database.id)
    assert session.scalars.await_count == 6
    for call in session.scalars.await_args_list:
        assert diagram.database.id in call.args[0].compile().params.values()
    session.execute.assert_not_awaited()
    session.commit.assert_not_awaited()


def test_export_requires_authentication(api, diagram: SqlDiagram) -> None:
    client, session, app = api
    app.dependency_overrides.pop(get_current_user)
    response = client.get(f"/databases/{diagram.database.id}/export/sql")
    assert response.status_code == 401
    session.scalars.assert_not_awaited()


def test_export_hides_inaccessible_database_before_loading_children(
    api, diagram: SqlDiagram
) -> None:
    client, session, _ = api
    session.scalar.return_value = None
    response = client.get(f"/databases/{diagram.database.id}/export/sql")
    assert response.status_code == 404
    session.scalars.assert_not_awaited()


def test_api_reports_unsupported_dialect_without_partial_file(api, diagram: SqlDiagram) -> None:
    client, session, _ = api
    session.get.return_value.type = "mysql"
    response = client.get(f"/databases/{diagram.database.id}/export/sql")
    assert response.status_code == 422
    assert "PostgreSQL" in response.json()["detail"]
    assert "content-disposition" not in response.headers


async def test_generated_file_executes_on_isolated_postgresql(diagram: SqlDiagram) -> None:
    dsn = os.environ.get("WDL_SQL_EXPORT_TEST_DSN")
    if not dsn:
        pytest.skip("Set WDL_SQL_EXPORT_TEST_DSN to an isolated disposable PostgreSQL database")
    connection = await asyncpg.connect(dsn)
    try:
        await connection.execute(generate_postgresql_sql(diagram))
        await connection.execute("""INSERT INTO wdl_export."parent""quoted" (region) VALUES (1)""")
        await connection.execute(
            """INSERT INTO wdl_export.child (id,parent_id,region,amount) VALUES (1,1,1,2.50)"""
        )
        with pytest.raises(asyncpg.ForeignKeyViolationError):
            await connection.execute(
                "INSERT INTO wdl_export.child (id,parent_id,region) VALUES (2,999,1)"
            )
        await connection.execute("""DELETE FROM wdl_export."parent""quoted" WHERE id=1""")
        row = await connection.fetchrow("SELECT parent_id,region FROM wdl_export.child WHERE id=1")
        assert row["parent_id"] is None and row["region"] is None
        with pytest.raises(asyncpg.CheckViolationError):
            await connection.execute("INSERT INTO wdl_export.child (id,amount) VALUES (3,-1)")
        assert (
            await connection.fetchval(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_schema='wdl_export' AND table_name='child' AND column_name='tags'"
            )
            == "ARRAY"
        )
    finally:
        await connection.execute("DROP SCHEMA IF EXISTS wdl_export CASCADE")
        await connection.close()


def test_identical_enums_share_a_type_even_across_schemas(diagram: SqlDiagram) -> None:
    other = column(
        diagram.tables[0].id,
        1000,
        "other_status",
        type="enum",
        enum_values=diagram.columns[2].enum_values,
        array_dimensions=1,
    )
    diagram.tables[0].schema_name = "other_schema"
    sql = generate_postgresql_sql(replace(diagram, columns=(*diagram.columns, other)))
    assert sql.count("CREATE TYPE") == 1
    assert '"other_status" "other_schema"."wdl_enum_000000000000000000000000000003e8"[]' in sql


@pytest.mark.parametrize(
    "option", ["fulltext", "invalid_method", "duplicate_position", "cross_table"]
)
def test_invalid_indexes_return_diagnostics(diagram: SqlDiagram, option: str) -> None:
    amount_index = diagram.indexes[0]
    if option == "fulltext":
        amount_index.type = IndexType.FULLTEXT
    elif option == "invalid_method":
        amount_index.method = "btree); DROP SCHEMA public"
    elif option == "duplicate_position":
        amount_index.columns = (*amount_index.columns, member(diagram.columns[3].id, 0))
    else:
        amount_index.columns = (replace(amount_index.columns[0], column_id=diagram.columns[0].id),)
    with pytest.raises(SqlExportError, match="Index"):
        generate_postgresql_sql(diagram)


def test_composite_unique_index_can_back_a_foreign_key(diagram: SqlDiagram) -> None:
    for item in diagram.columns[:2]:
        item.primary_key = False
    unique = index(
        80,
        diagram.tables[1].id,
        "parent_unique",
        type="unique",
        method="btree",
        columns=tuple(member(c.id, i) for i, c in enumerate(diagram.columns[:2])),
    )
    updated = replace(diagram, indexes=(*diagram.indexes, unique))
    assert 'CREATE UNIQUE INDEX "parent_unique"' in generate_postgresql_sql(updated)
    unique.where = '"id" > 0'
    with pytest.raises(SqlExportError, match="nonpartial unique key"):
        generate_postgresql_sql(updated)


async def test_cyclic_sql_executes_on_isolated_postgresql(diagram: SqlDiagram) -> None:
    dsn = os.environ.get("WDL_SQL_EXPORT_TEST_DSN")
    if not dsn:
        pytest.skip("Set WDL_SQL_EXPORT_TEST_DSN to an isolated disposable PostgreSQL database")
    parent, child = diagram.tables[1], diagram.tables[0]
    fk = relationship(
        60,
        diagram.database.id,
        "back_reference",
        parent,
        child,
        [(diagram.columns[0], diagram.columns[3])],
    )
    diagram = replace(diagram, relationships=(*diagram.relationships, fk))
    connection = await asyncpg.connect(dsn)
    try:
        await connection.execute(generate_postgresql_sql(diagram))
        assert (
            await connection.fetchval(
                "SELECT count(*) FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace "
                "WHERE n.nspname='wdl_export' AND c.contype='f'"
            )
            == 2
        )
    finally:
        await connection.execute("DROP SCHEMA IF EXISTS wdl_export CASCADE")
        await connection.close()


@pytest.fixture
def minimal_client_diagram() -> SqlDiagram:
    owner = database(name="Simple", default_schema="public", charset="UTF8")
    items = table(10, owner.id, "items")
    field = column(items.id, 101, "name", type="varchar")
    return SqlDiagram(owner, (items,), (field,))


@pytest.mark.parametrize("charset", ["UTF8", "utf8", "UTF-8"])
def test_client_default_utf8_exports_one_table_and_one_field(
    minimal_client_diagram: SqlDiagram, charset: str
) -> None:
    minimal_client_diagram.database.charset = charset
    sql = generate_postgresql_sql(minimal_client_diagram)
    assert sql.count("CREATE TABLE") == 1
    assert '"name" VARCHAR' in sql
    assert "SET LOCAL client_encoding = 'UTF8';" in sql


def test_non_utf8_charset_is_not_silently_dropped(minimal_client_diagram: SqlDiagram) -> None:
    minimal_client_diagram.database.charset = "LATIN1"
    with pytest.raises(SqlExportError, match="UTF-8"):
        generate_postgresql_sql(minimal_client_diagram)


def test_api_exports_minimal_client_model(api, minimal_client_diagram: SqlDiagram) -> None:
    client, session, _ = api
    mock_session_rows(session, orm_rows(minimal_client_diagram))
    response = client.get(f"/databases/{minimal_client_diagram.database.id}/export/sql")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/sql; charset=utf-8"
    assert response.text.count("CREATE TABLE") == 1
    assert '"name" VARCHAR' in response.text


async def test_minimal_client_sql_executes_on_postgresql(
    minimal_client_diagram: SqlDiagram,
) -> None:
    dsn = os.environ.get("WDL_SQL_EXPORT_TEST_DSN")
    if not dsn:
        pytest.skip("Set WDL_SQL_EXPORT_TEST_DSN to an isolated disposable PostgreSQL database")
    connection = await asyncpg.connect(dsn)
    try:
        await connection.execute(generate_postgresql_sql(minimal_client_diagram))
        await connection.execute("INSERT INTO public.items (name) VALUES ('works')")
        assert await connection.fetchval("SELECT name FROM public.items") == "works"
    finally:
        await connection.execute("DROP TABLE IF EXISTS public.items")
        await connection.close()
