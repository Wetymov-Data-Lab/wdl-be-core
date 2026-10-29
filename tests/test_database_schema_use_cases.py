import builtins
from datetime import UTC, datetime
from types import TracebackType
from typing import cast
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from wdl_shared.schemas.engine.enums.database import ColumnType, DataBaseName
from wdl_shared.schemas.engine.models.canvas import CanvasPosition

from common.exceptions.exceptions import EntityAlreadyExistsError, EntityNotFoundError
from context.application.services.column import (
    CreateColumn,
    CreateColumnRequest,
    DeleteColumn,
    GetColumn,
    ListColumns,
    UpdateColumn,
    UpdateColumnRequest,
)
from context.application.services.database import (
    CreateDatabase,
    CreateDatabaseRequest,
    DeleteDatabase,
    GetDatabase,
    ListDatabases,
    ListDatabasesRequest,
    UpdateDatabase,
    UpdateDatabaseRequest,
)
from context.application.services.table import (
    CreateTable,
    CreateTableRequest,
    DeleteTable,
    GetTable,
    ListTables,
    UpdateTable,
    UpdateTableRequest,
)
from context.domain.entities.column import Column, ColumnAttributes
from context.domain.entities.database import Database, DatabaseAttributes
from context.domain.entities.table import Table, TableAttributes
from context.infrastructure.repositories.column import ColumnRepository as SqlColumnRepository
from context.infrastructure.repositories.column_contract import (
    ColumnRepository,
    ColumnUnitOfWork,
)
from context.infrastructure.repositories.database import (
    DatabaseRepository as SqlDatabaseRepository,
)
from context.infrastructure.repositories.database_contract import (
    DatabaseRepository,
    DatabaseUnitOfWork,
)
from context.infrastructure.repositories.table import TableRepository as SqlTableRepository
from context.infrastructure.repositories.table_contract import TableRepository, TableUnitOfWork
from context.infrastructure.schemas.database import Columns, Databases, Tables
from context.infrastructure.services.authorization import AuthorizationService


class FakeDatabaseRepository(DatabaseRepository):
    def __init__(self) -> None:
        self.items: dict[UUID, Database] = {}

    async def get(self, entity_id: UUID) -> Database | None:
        return self.items.get(entity_id)

    async def list_accessible(
        self, account_id: UUID, project_id: UUID | None = None
    ) -> list[Database]:
        return [
            item
            for item in self.items.values()
            if project_id is None or item.project_id == project_id
        ]

    async def add(self, entity: Database) -> None:
        self.items[entity.id] = entity

    async def save(self, database: Database) -> None:
        self.items[database.id] = database

    async def remove(self, entity: Database) -> None:
        del self.items[entity.id]


class FakeTableRepository(TableRepository):
    def __init__(self) -> None:
        self.items: dict[UUID, Table] = {}

    async def get(self, entity_id: UUID) -> Table | None:
        return self.items.get(entity_id)

    async def list(self, database_id: UUID) -> list[Table]:
        return [item for item in self.items.values() if item.database_id == database_id]

    async def add(self, entity: Table) -> None:
        self.items[entity.id] = entity

    async def save(self, table: Table) -> None:
        self.items[table.id] = table

    async def remove(self, entity: Table) -> None:
        del self.items[entity.id]


class FakeColumnRepository(ColumnRepository):
    def __init__(self) -> None:
        self.items: dict[UUID, Column] = {}

    async def get(self, entity_id: UUID) -> Column | None:
        return self.items.get(entity_id)

    async def list(self, table_id: UUID) -> list[Column]:
        return [item for item in self.items.values() if item.table_id == table_id]

    async def list_by_database(self, database_id: UUID) -> builtins.list[Column]:
        return list(self.items.values())

    async def add(self, entity: Column) -> None:
        self.items[entity.id] = entity

    async def save(self, column: Column) -> None:
        self.items[column.id] = column

    async def remove(self, entity: Column) -> None:
        del self.items[entity.id]


class FakeSchemaUnitOfWork(DatabaseUnitOfWork, TableUnitOfWork, ColumnUnitOfWork):
    def __init__(self) -> None:
        self.databases = FakeDatabaseRepository()
        self.tables = FakeTableRepository()
        self.columns = FakeColumnRepository()
        self.commits = 0
        self.conflict = False

    async def commit(self) -> None:
        if self.conflict:
            raise EntityAlreadyExistsError("Entity violates a uniqueness constraint")
        self.commits += 1

    async def rollback(self) -> None:
        return None

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None


class FakeAuthorization:
    def __init__(self) -> None:
        self.denied: set[UUID] = set()
        self.checked: list[tuple[str, UUID]] = []

    async def require_project(self, project_id: UUID) -> None:
        self._require("Project", project_id)

    async def require_database(self, database_id: UUID) -> None:
        self._require("Database", database_id)

    async def require_table(self, table_id: UUID) -> None:
        self._require("Table", table_id)

    async def require_column(self, column_id: UUID) -> None:
        self._require("Column", column_id)

    def _require(self, kind: str, resource_id: UUID) -> None:
        self.checked.append((kind, resource_id))
        if resource_id in self.denied:
            raise EntityNotFoundError(f"{kind} {resource_id} was not found")


def authorization(fake: FakeAuthorization) -> AuthorizationService:
    return cast(AuthorizationService, fake)


def database_attributes(name: str = "main") -> DatabaseAttributes:
    return DatabaseAttributes(
        name=name,
        type=DataBaseName.PSQL,
        notice=None,
        default_schema="public",
        charset=None,
        collation=None,
    )


def table_attributes(name: str = "users") -> TableAttributes:
    return TableAttributes(
        name=name,
        schema_name="public",
        description=None,
        notice=None,
        color="#112233",
        position=CanvasPosition(x=10, y=20),
        width=240,
        is_collapsed=False,
        sort_order=0,
        checks=(),
    )


def column_attributes(name: str = "id", enum_values: list[str] | None = None) -> ColumnAttributes:
    return ColumnAttributes(
        name=name,
        type=ColumnType.UUID,
        custom_type=None,
        length=None,
        precision=None,
        scale=None,
        array_dimensions=0,
        nullable=False,
        primary_key=True,
        unique=False,
        auto_increment=False,
        unsigned=False,
        default=None,
        check=None,
        enum_values=enum_values or [],
        sort_order=0,
        notice=None,
    )


async def test_database_table_column_lifecycle() -> None:
    uow = FakeSchemaUnitOfWork()
    access = FakeAuthorization()
    project_id = uuid4()
    author_id = uuid4()

    database = await CreateDatabase(uow, authorization(access)).execute(
        CreateDatabaseRequest(
            project_id=project_id, attributes=database_attributes(), author_id=author_id
        )
    )
    table = await CreateTable(uow, authorization(access)).execute(
        CreateTableRequest(
            database_id=database.id, attributes=table_attributes(), author_id=author_id
        )
    )
    column = await CreateColumn(uow, authorization(access)).execute(
        CreateColumnRequest(table_id=table.id, attributes=column_attributes(), author_id=author_id)
    )
    assert access.checked == [
        ("Project", project_id),
        ("Database", database.id),
        ("Table", table.id),
    ]

    assert await ListDatabases(uow).execute(
        ListDatabasesRequest(account_id=author_id, project_id=project_id)
    ) == [database]
    assert await ListTables(uow, authorization(access)).execute(database.id) == [table]
    assert await ListColumns(uow, authorization(access)).execute(table.id) == [column]
    assert await GetDatabase(uow, authorization(access)).execute(database.id) == database
    assert await GetTable(uow, authorization(access)).execute(table.id) == table
    assert await GetColumn(uow, authorization(access)).execute(column.id) == column

    renamed_database = await UpdateDatabase(uow, authorization(access)).execute(
        UpdateDatabaseRequest(database_id=database.id, attributes=database_attributes("crm"))
    )
    moved_table = await UpdateTable(uow, authorization(access)).execute(
        UpdateTableRequest(table_id=table.id, attributes=table_attributes("accounts"))
    )
    renamed_column = await UpdateColumn(uow, authorization(access)).execute(
        UpdateColumnRequest(column_id=column.id, attributes=column_attributes("uuid"))
    )
    assert renamed_database.name == "crm"
    assert moved_table.name == "accounts"
    assert renamed_column.name == "uuid"
    assert all(
        item.updated_at is not None for item in (renamed_database, moved_table, renamed_column)
    )

    await DeleteColumn(uow, authorization(access)).execute(column.id)
    await DeleteTable(uow, authorization(access)).execute(table.id)
    await DeleteDatabase(uow, authorization(access)).execute(database.id)
    assert (uow.databases.items, uow.tables.items, uow.columns.items) == ({}, {}, {})
    assert uow.commits == 9


async def test_schema_access_is_checked_before_loading() -> None:
    uow = FakeSchemaUnitOfWork()
    access = FakeAuthorization()
    resource_id = uuid4()
    access.denied.add(resource_id)

    cases = (
        (GetDatabase, "Database"),
        (DeleteDatabase, "Database"),
        (ListTables, "Database"),
        (GetTable, "Table"),
        (DeleteTable, "Table"),
        (ListColumns, "Table"),
        (GetColumn, "Column"),
        (DeleteColumn, "Column"),
    )
    for use_case, kind in cases:
        with pytest.raises(EntityNotFoundError, match=kind):
            await use_case(uow, authorization(access)).execute(resource_id)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("factory", "expected"),
    [
        (
            lambda: CreateDatabaseRequest(
                project_id=uuid4(), attributes=database_attributes(), author_id=uuid4()
            ),
            "Database 'main' already exists in this project",
        ),
        (
            lambda: CreateTableRequest(
                database_id=uuid4(), attributes=table_attributes(), author_id=uuid4()
            ),
            "Table 'users' already exists in this database",
        ),
        (
            lambda: CreateColumnRequest(
                table_id=uuid4(), attributes=column_attributes(), author_id=uuid4()
            ),
            "Column 'id' already exists in this table",
        ),
    ],
)
async def test_create_reports_resource_conflict(factory: object, expected: str) -> None:
    uow = FakeSchemaUnitOfWork()
    uow.conflict = True
    request = factory()  # type: ignore[operator]
    use_case = {
        CreateDatabaseRequest: CreateDatabase,
        CreateTableRequest: CreateTable,
        CreateColumnRequest: CreateColumn,
    }[type(request)]

    with pytest.raises(EntityAlreadyExistsError, match=expected):
        await use_case(uow, authorization(FakeAuthorization())).execute(request)


def test_column_entity_does_not_share_enum_values_with_attributes() -> None:
    values = ["draft"]
    column = Column.create(
        table_id=uuid4(),
        attributes=column_attributes(enum_values=values),
        author_id=uuid4(),
        created_at=datetime.now(UTC),
    )

    values.append("published")

    assert column.enum_values == ["draft"]


async def test_sql_repositories_map_entities_to_schemas() -> None:
    session = Mock(spec=AsyncSession)
    session.execute = AsyncMock()
    now = datetime.now(UTC)
    database = Database.create(
        project_id=uuid4(), attributes=database_attributes(), author_id=uuid4(), created_at=now
    )
    table = Table.create(
        database_id=database.id, attributes=table_attributes(), author_id=uuid4(), created_at=now
    )
    column = Column.create(
        table_id=table.id,
        attributes=column_attributes(enum_values=["a"]),
        author_id=uuid4(),
        created_at=now,
    )

    await SqlDatabaseRepository(cast(AsyncSession, session)).add(database)
    await SqlTableRepository(cast(AsyncSession, session)).add(table)
    await SqlColumnRepository(cast(AsyncSession, session)).add(column)

    database_model, table_model, column_model = (
        call.args[0] for call in session.add.call_args_list
    )
    assert isinstance(database_model, Databases)
    assert isinstance(table_model, Tables)
    assert isinstance(column_model, Columns)
    assert (table_model.position_x, table_model.position_y) == (10, 20)
    assert SqlDatabaseRepository._to_domain(database_model).name == database.name
    assert SqlTableRepository._to_domain(table_model).position == table.position
    assert SqlColumnRepository._to_domain(column_model).enum_values == ["a"]

    database.update(attributes=database_attributes("crm"), updated_at=now)
    table.update(attributes=table_attributes("accounts"), updated_at=now)
    column.update(attributes=column_attributes("uuid", enum_values=["b"]), updated_at=now)
    session.get_one = AsyncMock(side_effect=[database_model, table_model, column_model])
    await SqlDatabaseRepository(cast(AsyncSession, session)).save(database)
    await SqlTableRepository(cast(AsyncSession, session)).save(table)
    await SqlColumnRepository(cast(AsyncSession, session)).save(column)

    # Changes stay pending until the unit of work flushes, so conflicts reach commit().
    session.execute.assert_not_awaited()
    assert (database_model.name, table_model.name, column_model.name) == ("crm", "accounts", "uuid")
    assert column_model.enum_values == ["b"]
    assert database_model.updated_at == table_model.updated_at == column_model.updated_at == now
