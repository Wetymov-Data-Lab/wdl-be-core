from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable
from wdl_shared.schemas.engine.models import TableResponseModel

import wdl_be_core.infrastructure.database.models  # noqa: F401
from wdl_be_core.infrastructure.database.base import Base
from wdl_be_core.infrastructure.database.models.database import Tables

EXPECTED_TABLES = {
    "canvas_states",
    "columns",
    "databases",
    "diagram_group_tables",
    "diagram_groups",
    "diagram_index_columns",
    "diagram_indexes",
    "diagram_notes",
    "projects",
    "realms",
    "relationship_columns",
    "relationships",
    "tables",
}


def test_all_database_models_are_registered() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_all_database_models_compile_for_postgresql() -> None:
    dialect = postgresql.dialect()

    for table in Base.metadata.sorted_tables:
        sql = str(CreateTable(table).compile(dialect=dialect))

        assert f"CREATE TABLE {table.name}" in sql


def test_database_collation_uses_safe_physical_column_name() -> None:
    database_table = Base.metadata.tables["databases"]

    assert "collation_name" in database_table.columns
    assert "collation" not in database_table.columns


def test_schema_hierarchy_uses_cascading_foreign_keys() -> None:
    expected_parents = {
        "projects":  {"realms"},
        "databases": {"projects"},
        "tables":    {"databases"},
        "columns":   {"tables"},
    }

    for table_name, parent_names in expected_parents.items():
        foreign_keys = Base.metadata.tables[table_name].foreign_keys

        assert {foreign_key.column.table.name for foreign_key in foreign_keys} == parent_names
        assert all(foreign_key.ondelete == "CASCADE" for foreign_key in foreign_keys)


def test_table_response_reads_persisted_canvas_position() -> None:
    identifier = uuid4()
    table      = Tables(
        id=identifier,
        name="users",
        database_id=uuid4(),
        position_x=125.5,
        position_y=-40,
        is_collapsed=False,
        sort_order=0,
        author_id=uuid4(),
        created_at=datetime.now(UTC),
    )

    response = TableResponseModel.model_validate(table)

    assert response.position.x == 125.5
    assert response.position.y == -40
