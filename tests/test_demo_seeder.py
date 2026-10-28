import builtins
from types import TracebackType
from typing import cast
from uuid import UUID, uuid4

import pytest
from test_canvas_use_cases import FakeCanvasStateRepository, FakeNoteRepository
from test_database_schema_use_cases import FakeDatabaseRepository
from test_index_relationship_use_cases import (
    FakeColumnRepository,
    FakeIndexRepository,
    FakeRelationshipRepository,
    FakeTableRepository,
)
from test_project_use_cases import FakeProjectRepository
from test_realm_use_cases import FakeRealmRepository
from wdl_shared.schemas.engine.enums.database import DataBaseName

from common.exceptions.exceptions import SqlExportError
from context.domain.entities.group import DiagramGroup, GroupName
from context.domain.services.sql_export import SqlDiagram, generate_postgresql_sql
from context.infrastructure.repositories.canvas_state_contract import CanvasStateUnitOfWork
from context.infrastructure.repositories.group_contract import GroupRepository, GroupUnitOfWork
from context.infrastructure.repositories.note_contract import NoteUnitOfWork
from context.infrastructure.repositories.project_contract import ProjectUnitOfWork
from context.infrastructure.repositories.realm_contract import RealmUnitOfWork
from context.infrastructure.repositories.sql_export_contract import SqlExportUnitOfWork
from context.infrastructure.repositories.unit_of_work import SQLAlchemyUnitOfWork
from context.infrastructure.seeders.demo import (
    DEMO_REALM_SLUG,
    UNGROUPED_COLOR,
    Box,
    DemoSeed,
    DemoSeeder,
    cardinalities,
    plan_layout,
)
from context.infrastructure.seeders.demo_dataset import DATABASES, SHOP, DatabaseSpec
from context.infrastructure.services.authorization import AuthorizationService


class FakeGroupRepository(GroupRepository):
    def __init__(self, uow: "FakeDemoUnitOfWork") -> None:
        self._uow = uow
        self.items: dict[UUID, DiagramGroup] = {}

    async def get(self, entity_id: UUID) -> DiagramGroup | None:
        return self.items.get(entity_id)

    async def list(self, database_id: UUID) -> builtins.list[DiagramGroup]:
        return [group for group in self.items.values() if group.database_id == database_id]

    async def database_exists(self, database_id: UUID) -> bool:
        return database_id in self._uow.databases.items

    async def tables_belong_to_database(
        self, table_ids: tuple[UUID, ...], database_id: UUID
    ) -> bool:
        tables = self._uow.tables.items
        return all(
            table_id in tables and tables[table_id].database_id == database_id
            for table_id in table_ids
        )

    async def exists_by_name(
        self, database_id: UUID, name: GroupName, *, exclude_id: UUID | None = None
    ) -> bool:
        return any(
            group.database_id == database_id and group.name == name and group.id != exclude_id
            for group in self.items.values()
        )

    async def add(self, entity: DiagramGroup) -> None:
        self.items[entity.id] = entity

    async def save(self, group: DiagramGroup) -> None:
        self.items[group.id] = group

    async def remove(self, entity: DiagramGroup) -> None:
        del self.items[entity.id]


class FakeDemoUnitOfWork(
    RealmUnitOfWork,
    GroupUnitOfWork,
    ProjectUnitOfWork,
    SqlExportUnitOfWork,
    CanvasStateUnitOfWork,
    NoteUnitOfWork,
):
    def __init__(self) -> None:
        self.realms = FakeRealmRepository()
        self.projects = FakeProjectRepository()
        self.databases = FakeDatabaseRepository()
        self.tables = FakeTableRepository()
        self.columns = FakeColumnRepository()
        self.indexes = FakeIndexRepository()
        self.relationships = FakeRelationshipRepository()
        self.groups = FakeGroupRepository(self)
        self.canvas_states = FakeCanvasStateRepository()
        self.notes = FakeNoteRepository()

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None


class AllowAll:
    """Access is granted: the seeder owns every resource it creates."""

    async def require_realm(self, resource_id: UUID) -> None:
        return None

    require_project = require_database = require_table = require_realm
    require_column = require_index = require_relationship = require_realm


async def seed(account_id: UUID) -> tuple[FakeDemoUnitOfWork, DemoSeed]:
    uow = FakeDemoUnitOfWork()
    result = await DemoSeeder(
        cast(SQLAlchemyUnitOfWork, uow), cast(AuthorizationService, AllowAll()), account_id
    ).seed()
    return uow, result


def diagram(uow: FakeDemoUnitOfWork, database_id: UUID) -> SqlDiagram:
    owned = {t.id for t in uow.tables.items.values() if t.database_id == database_id}
    return SqlDiagram(
        database=uow.databases.items[database_id],
        tables=tuple(uow.tables.items[t] for t in owned),
        columns=tuple(c for c in uow.columns.items.values() if c.table_id in owned),
        indexes=tuple(i for i in uow.indexes.items.values() if i.table_id in owned),
        relationships=tuple(
            r for r in uow.relationships.items.values() if r.database_id == database_id
        ),
    )


async def test_demo_seed_owns_realm_project_and_databases() -> None:
    account_id = uuid4()
    uow, result = await seed(account_id)

    realm = uow.realms.items[result.realm_id]
    assert (realm.slug.value, realm.author_id) == (DEMO_REALM_SLUG, account_id)
    assert realm.is_published
    assert uow.projects.items[result.project_id].realm_id == realm.id
    assert list(result.database_ids) == [spec.name for spec in DATABASES]
    for spec in DATABASES:
        database_id = result.database_ids[spec.name]
        assert uow.databases.items[database_id].project_id == result.project_id
        assert len(await uow.tables.list(database_id)) == len(spec.tables)
        assert len(await uow.relationships.list(database_id)) == len(spec.foreign_keys)
        assert len(await uow.groups.list(database_id)) == len(spec.groups)
        assert len(await uow.notes.list(database_id)) == len(spec.notes)
        assert await uow.canvas_states.find(database_id, account_id) is not None


def test_demo_dataset_is_substantial_and_groups_do_not_overlap() -> None:
    assert sum(len(spec.tables) for spec in DATABASES) >= 40
    for spec in DATABASES:
        grouped = [name for group in spec.groups for name in group.tables]
        assert len(grouped) == len(set(grouped)), spec.name
        assert set(grouped) <= {table.name for table in spec.tables}, spec.name


@pytest.mark.parametrize("spec", DATABASES, ids=lambda spec: spec.name)
def test_demo_layout_has_no_overlaps_and_colors_follow_groups(spec: DatabaseSpec) -> None:
    layout = plan_layout(spec)
    assert set(layout.tables) == {table.name for table in spec.tables}
    owner = {name: group for group in spec.groups for name in group.tables}

    for name, box in layout.tables.items():
        group = owner.get(name)
        assert layout.colors[name] == (group.color if group else UNGROUPED_COLOR)
        for group_name, frame in layout.groups.items():
            if group is not None and group.name == group_name:
                assert frame.contains(box), (name, group_name)
            else:
                assert not frame.overlaps(box), (name, group_name)

    def pairs(boxes: list[Box]) -> list[tuple[Box, Box]]:
        return [(a, b) for i, a in enumerate(boxes) for b in boxes[i + 1 :]]

    for a, b in pairs(list(layout.tables.values())):
        assert not a.overlaps(b)
    for a, b in pairs(list(layout.groups.values())):
        assert not a.overlaps(b)
    obstacles = [*layout.groups.values(), *layout.tables.values()]
    for note in layout.notes.values():
        assert not any(note.overlaps(other) for other in obstacles)
    for a, b in pairs(list(layout.notes.values())):
        assert not a.overlaps(b)


def test_demo_relationship_cardinalities_follow_source_columns() -> None:
    def ends(name: str) -> tuple[str, str]:
        foreign_key = next(fk for fk in SHOP.foreign_keys if fk.name == name)
        source, target = cardinalities(SHOP, foreign_key)
        return source.value, target.value

    assert ends("fk_orders_user") == ("zero_or_many", "exactly_one")
    assert ends("fk_orders_coupon") == ("zero_or_many", "zero_or_one")
    assert ends("fk_invoices_order") == ("zero_or_one", "exactly_one")


async def test_demo_postgresql_databases_export_and_mysql_is_rejected() -> None:
    uow, result = await seed(uuid4())

    for spec in DATABASES:
        model = diagram(uow, result.database_ids[spec.name])
        if spec.type != DataBaseName.PSQL:
            with pytest.raises(SqlExportError, match="PostgreSQL"):
                generate_postgresql_sql(model)
            continue
        sql = generate_postgresql_sql(model)
        assert sql.count("CREATE TABLE") == len(spec.tables), spec.name
        assert sql.count("FOREIGN KEY") == len(spec.foreign_keys), spec.name

    shop = generate_postgresql_sql(diagram(uow, result.database_ids["shop"]))
    assert 'CREATE SCHEMA IF NOT EXISTS "billing"' in shop
    assert 'PRIMARY KEY ("warehouse_id", "product_id")' in shop
    assert 'USING gin ("attributes")' in shop
    assert "ON DELETE SET NULL" in shop
    analytics = generate_postgresql_sql(diagram(uow, result.database_ids["analytics"]))
    assert 'FOREIGN KEY ("experiment_id", "variant")' in analytics
