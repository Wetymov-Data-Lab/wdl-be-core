"""Demo dataset for manual testing: one public realm, one project and several databases.

Run it with ``make seed-demo account=<identity account id>``. The realm is owned by
that account, so the data is visible through the API after signing in as it. A rerun
replaces only the demo realm (children are removed by cascade); other data is kept.
The models themselves are described in :mod:`demo_dataset`.
"""

import argparse
import asyncio
from dataclasses import dataclass
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy import delete
from wdl_shared.schemas.engine.enums.database import (
    IndexType,
    ReferentialAction,
    RelationshipCardinality,
    SortOrder,
)
from wdl_shared.schemas.engine.models.canvas import CanvasPosition, CanvasViewport

from context.application.services.canvas_state import (
    SaveCanvasState,
    SaveCanvasStateRequest,
)
from context.application.services.column import CreateColumn, CreateColumnRequest
from context.application.services.database import CreateDatabase, CreateDatabaseRequest
from context.application.services.group import CreateGroup, CreateGroupRequest
from context.application.services.index import CreateIndex, CreateIndexRequest
from context.application.services.note import CreateNote, CreateNoteRequest
from context.application.services.project import CreateProject, CreateProjectRequest
from context.application.services.realm import CreateRealm, CreateRealmRequest
from context.application.services.relationship import (
    CreateRelationship,
    CreateRelationshipRequest,
)
from context.application.services.table import CreateTable, CreateTableRequest
from context.domain.entities.canvas_state import CanvasPreferences
from context.domain.entities.column import Column, ColumnAttributes
from context.domain.entities.database import DatabaseAttributes
from context.domain.entities.index import IndexAttributes, IndexColumn
from context.domain.entities.note import NoteAttributes
from context.domain.entities.realm import RealmStatus, RealmVisibility
from context.domain.entities.relationship import ColumnPair, RelationshipAttributes
from context.domain.entities.table import Table, TableAttributes
from context.infrastructure.repositories.unit_of_work import SQLAlchemyUnitOfWork
from context.infrastructure.schemas.realm import RealmSchema
from context.infrastructure.seeders.demo_dataset import (
    DATABASES,
    ColumnSpec,
    DatabaseSpec,
    ForeignKeySpec,
    GroupSpec,
    IndexSpec,
    NoteSpec,
    TableSpec,
)
from context.infrastructure.services.authorization import AuthorizationService
from infrastructure.database.session import async_session_factory, engine
from observability.logger import setup_logging

DEMO_REALM_SLUG = "wdl-demo"

# Card sizes follow the client diagram: 290px wide cards, a header of about 60px and
# 35px column rows. Groups are framed with padding and placed on a coarse grid.
TABLE_WIDTH = 290
TABLE_HEADER = 64
TABLE_ROW = 35
TABLE_GAP = 40
GROUP_PADDING = 30
GROUP_HEADER = 56
CELL_GAP = 140
NOTE_GAP = 30
NOTE_HEIGHT = 140
ORIGIN = 80
UNGROUPED_PER_ROW = 3
UNGROUPED_COLOR = "#64748B"


@dataclass(frozen=True, slots=True)
class DemoSeed:
    realm_id: UUID
    project_id: UUID
    database_ids: dict[str, UUID]


@dataclass(frozen=True, slots=True)
class Box:
    x: float
    y: float
    width: float
    height: float

    def overlaps(self, other: "Box") -> bool:
        return (
            self.x < other.x + other.width
            and other.x < self.x + self.width
            and self.y < other.y + other.height
            and other.y < self.y + self.height
        )

    def contains(self, other: "Box") -> bool:
        return (
            self.x <= other.x
            and self.y <= other.y
            and other.x + other.width <= self.x + self.width
            and other.y + other.height <= self.y + self.height
        )


@dataclass(frozen=True, slots=True)
class Layout:
    tables: dict[str, Box]
    groups: dict[str, Box]
    notes: dict[NoteSpec, Box]
    colors: dict[str, str]


@dataclass(frozen=True, slots=True)
class _Block:
    group: GroupSpec | None
    tables: tuple[str, ...]
    cell: tuple[int, int]
    columns: int
    notes: tuple[NoteSpec, ...]


def card_height(table: TableSpec) -> float:
    return TABLE_HEADER + TABLE_ROW * len(table.columns)


def plan_layout(spec: DatabaseSpec) -> Layout:
    """Place groups on their grid cells, stack tables inside them, notes under them.

    Ungrouped tables get their own frameless cells after the grouped rows.
    """
    by_name = {table.name: table for table in spec.tables}
    grouped = {name for group in spec.groups for name in group.tables}
    blocks = [
        _Block(
            group=group,
            tables=group.tables,
            cell=group.cell,
            columns=group.columns,
            notes=tuple(note for note in spec.notes if note.group == group.name),
        )
        for group in spec.groups
    ]
    first_free_row = max((group.cell[1] for group in spec.groups), default=-1) + 1
    ungrouped = [table.name for table in spec.tables if table.name not in grouped]
    blocks += [
        _Block(
            group=None,
            tables=(name,),
            cell=(index % UNGROUPED_PER_ROW, first_free_row + index // UNGROUPED_PER_ROW),
            columns=1,
            notes=(),
        )
        for index, name in enumerate(ungrouped)
    ]

    offsets: list[dict[str, tuple[float, float]]] = []
    sizes: list[tuple[float, float]] = []
    for block in blocks:
        padding = GROUP_PADDING if block.group else 0
        header = GROUP_HEADER if block.group else 0
        heights = [0.0] * block.columns
        placed: dict[str, tuple[float, float]] = {}
        for name in block.tables:
            column = min(range(block.columns), key=heights.__getitem__)
            placed[name] = (padding + column * (TABLE_WIDTH + TABLE_GAP), header + heights[column])
            heights[column] += card_height(by_name[name]) + TABLE_GAP
        width = float(2 * padding + block.columns * TABLE_WIDTH + (block.columns - 1) * TABLE_GAP)
        height = header + max(heights) - TABLE_GAP + padding
        offsets.append(placed)
        sizes.append((width, height))

    column_widths: dict[int, float] = {}
    row_heights: dict[int, float] = {}
    for block, (width, height) in zip(blocks, sizes, strict=True):
        column, row = block.cell
        cell_height = height + len(block.notes) * (NOTE_GAP + NOTE_HEIGHT)
        column_widths[column] = max(column_widths.get(column, 0), width)
        row_heights[row] = max(row_heights.get(row, 0), cell_height)
    xs = _starts(column_widths)
    ys = _starts(row_heights)

    layout = Layout(tables={}, groups={}, notes={}, colors={})
    for block, placed, (width, height) in zip(blocks, offsets, sizes, strict=True):
        x, y = xs[block.cell[0]], ys[block.cell[1]]
        color = block.group.color if block.group else UNGROUPED_COLOR
        for name, (dx, dy) in placed.items():
            layout.tables[name] = Box(x + dx, y + dy, TABLE_WIDTH, card_height(by_name[name]))
            layout.colors[name] = color
        if block.group is not None:
            layout.groups[block.group.name] = Box(x, y, width, height)
        for number, note in enumerate(block.notes):
            top = y + height + NOTE_GAP + number * (NOTE_HEIGHT + NOTE_GAP)
            layout.notes[note] = Box(x, top, width, NOTE_HEIGHT)
    return layout


def _starts(lengths: dict[int, float]) -> dict[int, float]:
    starts: dict[int, float] = {}
    position = float(ORIGIN)
    for index in range(max(lengths, default=-1) + 1):
        starts[index] = position
        position += lengths.get(index, 0) + CELL_GAP
    return starts


def cardinalities(
    spec: DatabaseSpec, foreign_key: ForeignKeySpec
) -> tuple[RelationshipCardinality, RelationshipCardinality]:
    """Derive the crow's foot ends from the source columns.

    A source that is unique or the whole primary key is one-to-one; a nullable source
    makes the referenced row optional.
    """
    table_name, names = column_refs(foreign_key.source)
    table = next(table for table in spec.tables if table.name == table_name)
    source = [column for column in table.columns if column.name in names]
    primary_key = {column.name for column in table.columns if column.primary_key}
    unique_indexes = [
        set(index.columns) for index in table.indexes if index.type == IndexType.UNIQUE
    ]
    is_unique = (
        (len(source) == 1 and source[0].unique)
        or set(names) == primary_key
        or set(names) in unique_indexes
    )
    return (
        RelationshipCardinality.ZERO_OR_ONE if is_unique else RelationshipCardinality.ZERO_OR_MANY,
        RelationshipCardinality.ZERO_OR_ONE
        if any(column.nullable for column in source)
        else RelationshipCardinality.EXACTLY_ONE,
    )


def column_refs(reference: str) -> tuple[str, tuple[str, ...]]:
    table, names = reference.split(".")
    return table, tuple(names.split(","))


class DemoSeeder:
    """Create the demo models through application use cases, so every rule still applies."""

    def __init__(
        self,
        uow: SQLAlchemyUnitOfWork,
        authorization: AuthorizationService,
        account_id: UUID,
        databases: tuple[DatabaseSpec, ...] = DATABASES,
    ) -> None:
        self._uow = uow
        self._authorization = authorization
        self._account_id = account_id
        self._databases = databases

    async def seed(self) -> DemoSeed:
        realm = await CreateRealm(self._uow).execute(
            CreateRealmRequest(
                name="WDL demo",
                slug=DEMO_REALM_SLUG,
                status=RealmStatus.ACTIVE,
                visibility=RealmVisibility.PUBLIC,
                settings={},
                notice="Demo data for manual testing",
                author_id=self._account_id,
            )
        )
        project = await CreateProject(self._uow, self._authorization).execute(
            CreateProjectRequest(
                name="Demo shop",
                notice="Online store with analytics, CRM and a legacy billing system",
                realm_id=realm.id,
                author_id=self._account_id,
            )
        )
        database_ids = {
            spec.name: await self._seed_database(project.id, spec) for spec in self._databases
        }
        return DemoSeed(realm_id=realm.id, project_id=project.id, database_ids=database_ids)

    async def _seed_database(self, project_id: UUID, spec: DatabaseSpec) -> UUID:
        database = await CreateDatabase(self._uow, self._authorization).execute(
            CreateDatabaseRequest(
                project_id=project_id,
                attributes=DatabaseAttributes(
                    name=spec.name,
                    type=spec.type,
                    notice=spec.notice,
                    default_schema=spec.default_schema,
                    charset=None,
                    collation=None,
                ),
                author_id=self._account_id,
            )
        )
        layout = plan_layout(spec)
        tables: dict[str, Table] = {}
        columns: dict[tuple[str, str], Column] = {}
        for order, table_spec in enumerate(spec.tables):
            table = await self._table(database.id, table_spec, order, layout)
            tables[table_spec.name] = table
            for position, column_spec in enumerate(table_spec.columns):
                column = await self._column(table, column_spec, position)
                columns[(table_spec.name, column_spec.name)] = column
        for table_spec in spec.tables:
            for index_spec in table_spec.indexes:
                await self._index(tables[table_spec.name], index_spec, columns)
        for foreign_key in spec.foreign_keys:
            await self._relationship(database.id, spec, foreign_key, tables, columns)
        for group in spec.groups:
            await self._group(database.id, group, layout.groups[group.name], tables)
        for note in spec.notes:
            await self._note(database.id, note, layout.notes[note])
        await self._canvas(database.id)
        return database.id

    async def _table(self, database_id: UUID, spec: TableSpec, order: int, layout: Layout) -> Table:
        box = layout.tables[spec.name]
        return await CreateTable(self._uow, self._authorization).execute(
            CreateTableRequest(
                database_id=database_id,
                attributes=TableAttributes(
                    name=spec.name,
                    schema_name=spec.schema,
                    description=spec.description,
                    notice=None,
                    color=layout.colors[spec.name],
                    position=CanvasPosition(x=box.x, y=box.y),
                    width=box.width,
                    is_collapsed=False,
                    sort_order=order,
                ),
                author_id=self._account_id,
            )
        )

    async def _column(self, table: Table, spec: ColumnSpec, position: int) -> Column:
        return await CreateColumn(self._uow, self._authorization).execute(
            CreateColumnRequest(
                table_id=table.id,
                attributes=ColumnAttributes(
                    name=spec.name,
                    type=spec.type,
                    custom_type=None,
                    length=spec.length,
                    precision=spec.precision,
                    scale=spec.scale,
                    array_dimensions=spec.array_dimensions,
                    nullable=spec.nullable,
                    primary_key=spec.primary_key,
                    unique=spec.unique,
                    auto_increment=spec.auto_increment,
                    unsigned=spec.unsigned,
                    default=spec.default,
                    check=spec.check,
                    enum_values=list(spec.enum_values),
                    sort_order=position,
                    notice=spec.notice,
                ),
                author_id=self._account_id,
            )
        )

    async def _index(
        self, table: Table, spec: IndexSpec, columns: dict[tuple[str, str], Column]
    ) -> None:
        members = tuple(
            IndexColumn(
                column_id=columns[(table.name, name.removeprefix("-"))].id,
                sort_order=SortOrder.DESC if name.startswith("-") else SortOrder.ASC,
                position=position,
            )
            for position, name in enumerate(spec.columns)
        )
        await CreateIndex(self._uow, self._authorization).execute(
            CreateIndexRequest(
                table_id=table.id,
                attributes=IndexAttributes(
                    name=spec.name,
                    type=spec.type,
                    columns=members,
                    method=spec.method,
                    where=spec.where,
                ),
                author_id=self._account_id,
            )
        )

    async def _relationship(
        self,
        database_id: UUID,
        database: DatabaseSpec,
        spec: ForeignKeySpec,
        tables: dict[str, Table],
        columns: dict[tuple[str, str], Column],
    ) -> None:
        source, source_names = column_refs(spec.source)
        target, target_names = column_refs(spec.target)
        source_cardinality, target_cardinality = cardinalities(database, spec)
        await CreateRelationship(self._uow, self._authorization).execute(
            CreateRelationshipRequest(
                database_id=database_id,
                source_table_id=tables[source].id,
                target_table_id=tables[target].id,
                attributes=RelationshipAttributes(
                    name=spec.name,
                    columns=tuple(
                        ColumnPair(
                            source_column_id=columns[(source, source_name)].id,
                            target_column_id=columns[(target, target_name)].id,
                        )
                        for source_name, target_name in zip(source_names, target_names, strict=True)
                    ),
                    source_cardinality=source_cardinality,
                    target_cardinality=target_cardinality,
                    on_delete=spec.on_delete,
                    on_update=ReferentialAction.NO_ACTION,
                    waypoints=(),
                ),
                author_id=self._account_id,
            )
        )

    async def _group(
        self, database_id: UUID, spec: GroupSpec, box: Box, tables: dict[str, Table]
    ) -> None:
        await CreateGroup(self._uow).execute(
            CreateGroupRequest(
                database_id=database_id,
                name=spec.name,
                x=box.x,
                y=box.y,
                width=box.width,
                height=box.height,
                color=spec.color,
                is_collapsed=False,
                table_ids=[tables[name].id for name in spec.tables],
                author_id=self._account_id,
            )
        )

    async def _note(self, database_id: UUID, spec: NoteSpec, box: Box) -> None:
        await CreateNote(self._uow, self._authorization).execute(
            CreateNoteRequest(
                database_id=database_id,
                note_id=uuid4(),
                attributes=NoteAttributes(
                    text=spec.text,
                    position=CanvasPosition(x=box.x, y=box.y),
                    width=box.width,
                    height=box.height,
                    color=spec.color,
                ),
                author_id=self._account_id,
            )
        )

    async def _canvas(self, database_id: UUID) -> None:
        await SaveCanvasState(self._uow, self._authorization).execute(
            SaveCanvasStateRequest(
                database_id=database_id,
                account_id=self._account_id,
                requested_user_id=None,
                preferences=CanvasPreferences(
                    viewport=CanvasViewport(x=0, y=0, zoom=0.6),
                    grid_size=20,
                    snap_to_grid=True,
                    show_relationship_labels=True,
                ),
            )
        )


async def run(account_id: UUID) -> DemoSeed:
    """Replace the demo realm in one transaction."""
    async with async_session_factory() as session, session.begin():
        await session.execute(delete(RealmSchema).where(RealmSchema.slug == DEMO_REALM_SLUG))
        uow = SQLAlchemyUnitOfWork(async_session_factory, managed_session=session)
        authorization = AuthorizationService(session, account_id)
        return await DemoSeeder(uow, authorization, account_id).seed()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the WDL demo realm, project and databases")
    parser.add_argument(
        "--account-id",
        type=UUID,
        required=True,
        help="Identity account that owns the demo realm",
    )
    arguments = parser.parse_args()
    setup_logging()

    async def seed() -> DemoSeed:
        try:
            return await run(arguments.account_id)
        finally:
            await engine.dispose()

    result = asyncio.run(seed())
    logger.info("Demo realm {} with project {} created", result.realm_id, result.project_id)
    for spec in DATABASES:
        logger.info(
            "Database {} ({}, {} tables, {} relationships): {}",
            spec.name,
            spec.type.value,
            len(spec.tables),
            len(spec.foreign_keys),
            result.database_ids[spec.name],
        )


if __name__ == "__main__":
    main()
