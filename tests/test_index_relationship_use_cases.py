import builtins
from datetime import UTC, datetime
from types import TracebackType
from typing import cast
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from wdl_shared.schemas.engine.enums.database import (
    ColumnType,
    IndexType,
    ReferentialAction,
    RelationshipCardinality,
    SortOrder,
)
from wdl_shared.schemas.engine.models.canvas import CanvasPosition

from common.exceptions.exceptions import EntityAlreadyExistsError, EntityNotFoundError
from context.application.services.index import (
    CreateIndex,
    CreateIndexRequest,
    DeleteIndex,
    GetIndex,
    ListIndexes,
    UpdateIndex,
    UpdateIndexRequest,
)
from context.application.services.relationship import (
    CreateRelationship,
    CreateRelationshipRequest,
    DeleteRelationship,
    GetRelationship,
    ListRelationships,
    UpdateRelationship,
    UpdateRelationshipRequest,
)
from context.domain.entities.column import Column, ColumnAttributes
from context.domain.entities.index import DiagramIndex, IndexAttributes, IndexColumn
from context.domain.entities.relationship import (
    ColumnPair,
    Relationship,
    RelationshipAttributes,
)
from context.domain.entities.table import Table, TableAttributes
from context.infrastructure.repositories.column_contract import ColumnRepository
from context.infrastructure.repositories.index import IndexRepository as SqlIndexRepository
from context.infrastructure.repositories.index_contract import IndexRepository, IndexUnitOfWork
from context.infrastructure.repositories.relationship import (
    RelationshipRepository as SqlRelationshipRepository,
)
from context.infrastructure.repositories.relationship_contract import (
    RelationshipRepository,
    RelationshipUnitOfWork,
)
from context.infrastructure.repositories.table_contract import TableRepository
from context.infrastructure.schemas.database import (
    DiagramIndexColumns,
    DiagramIndexes,
    RelationshipColumns,
    Relationships,
)
from context.infrastructure.services.authorization import AuthorizationService

NOW = datetime(2026, 1, 1, tzinfo=UTC)


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


class FakeIndexRepository(IndexRepository):
    def __init__(self) -> None:
        self.items: dict[UUID, DiagramIndex] = {}
        self.memberships: dict[UUID, tuple[IndexColumn, ...]] = {}

    async def get(self, entity_id: UUID) -> DiagramIndex | None:
        return self.items.get(entity_id)

    async def list(self, table_id: UUID) -> list[DiagramIndex]:
        return [item for item in self.items.values() if item.table_id == table_id]

    async def list_by_database(self, database_id: UUID) -> builtins.list[DiagramIndex]:
        return list(self.items.values())

    async def add(self, entity: DiagramIndex) -> None:
        self.items[entity.id] = entity

    async def add_columns(self, index: DiagramIndex) -> None:
        self.memberships[index.id] = index.columns

    async def save(self, index: DiagramIndex) -> None:
        self.items[index.id] = index

    async def replace_columns(self, index: DiagramIndex) -> None:
        self.memberships[index.id] = index.columns

    async def remove(self, entity: DiagramIndex) -> None:
        del self.items[entity.id]
        self.memberships.pop(entity.id, None)


class FakeRelationshipRepository(RelationshipRepository):
    def __init__(self) -> None:
        self.items: dict[UUID, Relationship] = {}
        self.mappings: dict[UUID, tuple[ColumnPair, ...]] = {}

    async def get(self, entity_id: UUID) -> Relationship | None:
        return self.items.get(entity_id)

    async def list(self, database_id: UUID) -> list[Relationship]:
        return [item for item in self.items.values() if item.database_id == database_id]

    async def add(self, entity: Relationship) -> None:
        self.items[entity.id] = entity

    async def add_columns(self, relationship: Relationship) -> None:
        self.mappings[relationship.id] = relationship.columns

    async def save(self, relationship: Relationship) -> None:
        self.items[relationship.id] = relationship

    async def replace_columns(self, relationship: Relationship) -> None:
        self.mappings[relationship.id] = relationship.columns

    async def remove(self, entity: Relationship) -> None:
        del self.items[entity.id]
        self.mappings.pop(entity.id, None)


class FakeUnitOfWork(IndexUnitOfWork, RelationshipUnitOfWork):
    def __init__(self) -> None:
        self.indexes = FakeIndexRepository()
        self.relationships = FakeRelationshipRepository()
        self.tables = FakeTableRepository()
        self.columns = FakeColumnRepository()
        self.commits = 0
        self.conflict_on_commit: int | None = None

    async def commit(self) -> None:
        self.commits += 1
        if self.commits == self.conflict_on_commit:
            raise EntityAlreadyExistsError("Entity violates a uniqueness constraint")

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

    async def require_database(self, database_id: UUID) -> None:
        self._require("Database", database_id)

    async def require_table(self, table_id: UUID) -> None:
        self._require("Table", table_id)

    async def require_column(self, column_id: UUID) -> None:
        self._require("Column", column_id)

    async def require_index(self, index_id: UUID) -> None:
        self._require("Diagram index", index_id)

    async def require_relationship(self, relationship_id: UUID) -> None:
        self._require("Relationship", relationship_id)

    def _require(self, kind: str, resource_id: UUID) -> None:
        if resource_id in self.denied:
            raise EntityNotFoundError(f"{kind} {resource_id} was not found")


def authorization(fake: FakeAuthorization) -> AuthorizationService:
    return cast(AuthorizationService, fake)


def add_table(uow: FakeUnitOfWork, database_id: UUID, name: str) -> Table:
    table = Table.create(
        database_id=database_id,
        attributes=TableAttributes(
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
        ),
        author_id=uuid4(),
        created_at=NOW,
    )
    uow.tables.items[table.id] = table
    return table


def add_column(uow: FakeUnitOfWork, table: Table, name: str) -> Column:
    column = Column.create(
        table_id=table.id,
        attributes=ColumnAttributes(
            name=name,
            type=ColumnType.UUID,
            custom_type=None,
            length=None,
            precision=None,
            scale=None,
            array_dimensions=0,
            nullable=False,
            primary_key=False,
            unique=False,
            auto_increment=False,
            unsigned=False,
            default=None,
            check=None,
            enum_values=[],
            sort_order=0,
            notice=None,
        ),
        author_id=uuid4(),
        created_at=NOW,
    )
    uow.columns.items[column.id] = column
    return column


def index_attributes(*columns: tuple[Column, int], name: str | None = "ix") -> IndexAttributes:
    return IndexAttributes(
        name=name,
        type=IndexType.INDEX,
        columns=tuple(
            IndexColumn(column_id=column.id, sort_order=SortOrder.ASC, position=position)
            for column, position in columns
        ),
        method=None,
        where=None,
    )


def relationship_attributes(
    *pairs: tuple[Column, Column], name: str | None = "fk"
) -> RelationshipAttributes:
    return RelationshipAttributes(
        name=name,
        columns=tuple(
            ColumnPair(source_column_id=source.id, target_column_id=target.id)
            for source, target in pairs
        ),
        source_cardinality=RelationshipCardinality.ZERO_OR_MANY,
        target_cardinality=RelationshipCardinality.EXACTLY_ONE,
        on_delete=ReferentialAction.NO_ACTION,
        on_update=ReferentialAction.NO_ACTION,
        waypoints=(CanvasPosition(x=1, y=2),),
    )


async def test_index_lifecycle_orders_columns_by_position() -> None:
    uow = FakeUnitOfWork()
    access = authorization(FakeAuthorization())
    table = add_table(uow, uuid4(), "users")
    first, second = add_column(uow, table, "a"), add_column(uow, table, "b")

    index = await CreateIndex(uow, access).execute(
        CreateIndexRequest(
            table_id=table.id,
            attributes=index_attributes((second, 1), (first, 0)),
            author_id=uuid4(),
        )
    )
    assert [column.column_id for column in index.columns] == [first.id, second.id]
    assert uow.indexes.memberships[index.id] == index.columns
    assert uow.commits == 2
    assert await GetIndex(uow, access).execute(index.id) == index
    assert await ListIndexes(uow, access).execute(table.id) == [index]

    updated = await UpdateIndex(uow, access).execute(
        UpdateIndexRequest(index_id=index.id, attributes=index_attributes((second, 0), name="ux"))
    )
    assert updated.name == "ux"
    assert uow.indexes.memberships[index.id] == (
        IndexColumn(column_id=second.id, sort_order=SortOrder.ASC, position=0),
    )

    await DeleteIndex(uow, access).execute(index.id)
    assert uow.indexes.items == {}


async def test_index_rejects_column_from_another_table() -> None:
    uow = FakeUnitOfWork()
    table = add_table(uow, uuid4(), "users")
    foreign = add_column(uow, add_table(uow, table.database_id, "orders"), "id")

    with pytest.raises(EntityNotFoundError, match=f"Column {foreign.id} does not belong"):
        await CreateIndex(uow, authorization(FakeAuthorization())).execute(
            CreateIndexRequest(
                table_id=table.id, attributes=index_attributes((foreign, 0)), author_id=uuid4()
            )
        )
    assert uow.indexes.items == {}


async def test_index_column_access_is_checked() -> None:
    uow = FakeUnitOfWork()
    table = add_table(uow, uuid4(), "users")
    column = add_column(uow, table, "id")
    access = FakeAuthorization()
    access.denied.add(column.id)

    with pytest.raises(EntityNotFoundError, match=f"Column {column.id} was not found"):
        await CreateIndex(uow, authorization(access)).execute(
            CreateIndexRequest(
                table_id=table.id, attributes=index_attributes((column, 0)), author_id=uuid4()
            )
        )


@pytest.mark.parametrize(
    ("conflict_on_commit", "expected"),
    [(1, "Index 'ix' already exists"), (2, "Index contains duplicate columns or positions")],
)
async def test_create_index_reports_conflict_stage(conflict_on_commit: int, expected: str) -> None:
    uow = FakeUnitOfWork()
    uow.conflict_on_commit = conflict_on_commit
    table = add_table(uow, uuid4(), "users")
    column = add_column(uow, table, "id")

    with pytest.raises(EntityAlreadyExistsError, match=expected):
        await CreateIndex(uow, authorization(FakeAuthorization())).execute(
            CreateIndexRequest(
                table_id=table.id, attributes=index_attributes((column, 0)), author_id=uuid4()
            )
        )


async def test_relationship_lifecycle() -> None:
    uow = FakeUnitOfWork()
    access = authorization(FakeAuthorization())
    database_id = uuid4()
    orders, users = add_table(uow, database_id, "orders"), add_table(uow, database_id, "users")
    user_id, id_column = add_column(uow, orders, "user_id"), add_column(uow, users, "id")

    relationship = await CreateRelationship(uow, access).execute(
        CreateRelationshipRequest(
            database_id=database_id,
            source_table_id=orders.id,
            target_table_id=users.id,
            attributes=relationship_attributes((user_id, id_column)),
            author_id=uuid4(),
        )
    )
    assert uow.relationships.mappings[relationship.id] == relationship.columns
    assert relationship.waypoints == (CanvasPosition(x=1, y=2),)
    assert await GetRelationship(uow, access).execute(relationship.id) == relationship
    assert await ListRelationships(uow, access).execute(database_id) == [relationship]

    updated = await UpdateRelationship(uow, access).execute(
        UpdateRelationshipRequest(
            relationship_id=relationship.id,
            attributes=relationship_attributes((user_id, id_column), name="fk_users"),
        )
    )
    assert updated.name == "fk_users"
    assert updated.updated_at is not None

    await DeleteRelationship(uow, access).execute(relationship.id)
    assert uow.relationships.items == {}


async def test_relationship_tables_must_share_database() -> None:
    uow = FakeUnitOfWork()
    orders = add_table(uow, uuid4(), "orders")
    users = add_table(uow, uuid4(), "users")

    with pytest.raises(EntityNotFoundError, match="must belong to the requested database"):
        await CreateRelationship(uow, authorization(FakeAuthorization())).execute(
            CreateRelationshipRequest(
                database_id=orders.database_id,
                source_table_id=orders.id,
                target_table_id=users.id,
                attributes=relationship_attributes(),
                author_id=uuid4(),
            )
        )


async def test_relationship_columns_must_match_endpoint_tables() -> None:
    uow = FakeUnitOfWork()
    database_id = uuid4()
    orders, users = add_table(uow, database_id, "orders"), add_table(uow, database_id, "users")
    user_id, id_column = add_column(uow, orders, "user_id"), add_column(uow, users, "id")

    with pytest.raises(EntityNotFoundError, match="must belong to their endpoint tables"):
        await CreateRelationship(uow, authorization(FakeAuthorization())).execute(
            CreateRelationshipRequest(
                database_id=database_id,
                source_table_id=orders.id,
                target_table_id=users.id,
                attributes=relationship_attributes((id_column, user_id)),
                author_id=uuid4(),
            )
        )
    assert uow.relationships.items == {}


@pytest.mark.parametrize(
    ("conflict_on_commit", "expected"),
    [
        (1, "Relationship 'fk' already exists"),
        (2, "Relationship contains duplicate column mappings"),
    ],
)
async def test_create_relationship_reports_conflict_stage(
    conflict_on_commit: int, expected: str
) -> None:
    uow = FakeUnitOfWork()
    uow.conflict_on_commit = conflict_on_commit
    database_id = uuid4()
    orders, users = add_table(uow, database_id, "orders"), add_table(uow, database_id, "users")
    user_id, id_column = add_column(uow, orders, "user_id"), add_column(uow, users, "id")

    with pytest.raises(EntityAlreadyExistsError, match=expected):
        await CreateRelationship(uow, authorization(FakeAuthorization())).execute(
            CreateRelationshipRequest(
                database_id=database_id,
                source_table_id=orders.id,
                target_table_id=users.id,
                attributes=relationship_attributes((user_id, id_column)),
                author_id=uuid4(),
            )
        )


async def test_sql_repositories_split_rows_and_children() -> None:
    session = Mock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    table_id, database_id = uuid4(), uuid4()
    index = DiagramIndex.create(
        table_id=table_id,
        attributes=IndexAttributes(
            name="ix",
            type=IndexType.UNIQUE,
            columns=(IndexColumn(column_id=uuid4(), sort_order=SortOrder.DESC, position=0),),
            method=None,
            where=None,
        ),
        author_id=uuid4(),
        created_at=NOW,
    )
    relationship = Relationship.create(
        database_id=database_id,
        source_table_id=uuid4(),
        target_table_id=uuid4(),
        attributes=RelationshipAttributes(
            name="fk",
            columns=(ColumnPair(source_column_id=uuid4(), target_column_id=uuid4()),),
            source_cardinality=RelationshipCardinality.ZERO_OR_MANY,
            target_cardinality=RelationshipCardinality.EXACTLY_ONE,
            on_delete=ReferentialAction.NO_ACTION,
            on_update=ReferentialAction.NO_ACTION,
            waypoints=(CanvasPosition(x=1, y=2),),
        ),
        author_id=uuid4(),
        created_at=NOW,
    )
    indexes = SqlIndexRepository(cast(AsyncSession, session))
    relationships = SqlRelationshipRepository(cast(AsyncSession, session))

    await indexes.add(index)
    await relationships.add(relationship)
    index_model, relationship_model = (call.args[0] for call in session.add.call_args_list)
    assert isinstance(index_model, DiagramIndexes)
    assert isinstance(relationship_model, Relationships)
    assert relationship_model.waypoints == [{"x": 1, "y": 2}]

    await indexes.add_columns(index)
    await relationships.add_columns(relationship)
    (index_member,), (mapping,) = (list(call.args[0]) for call in session.add_all.call_args_list)
    assert isinstance(index_member, DiagramIndexColumns)
    assert isinstance(mapping, RelationshipColumns)
    assert (index_member.index_id, mapping.relationship_id) == (index.id, relationship.id)

    session.get_one = AsyncMock(side_effect=[index_model, relationship_model])
    index.update(
        attributes=IndexAttributes(
            name="ux", type=IndexType.INDEX, columns=index.columns, method=None, where=None
        ),
        updated_at=NOW,
    )
    await indexes.save(index)
    await relationships.save(relationship)
    session.execute.assert_not_awaited()
    assert index_model.name == "ux"

    await indexes.replace_columns(index)
    assert session.execute.await_count == 1
    session.flush.assert_awaited_once()
