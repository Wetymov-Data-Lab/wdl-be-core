"""Read an owned ER model and render PostgreSQL DDL without executing it."""

from collections import defaultdict
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from wdl_shared.schemas.engine.enums.database import ColumnType, DataBaseName, IndexType

from common.exceptions.exceptions import SqlExportError
from context.infrastructure.schemas.database import (
    Columns,
    Databases,
    DiagramIndexColumns,
    DiagramIndexes,
    RelationshipColumns,
    Relationships,
    Tables,
)


@dataclass(frozen=True)
class SqlDiagram:
    database: Databases
    tables: tuple[Tables, ...] = ()
    columns: tuple[Columns, ...] = ()
    indexes: tuple[DiagramIndexes, ...] = ()
    index_columns: tuple[DiagramIndexColumns, ...] = ()
    relationships: tuple[Relationships, ...] = ()
    relationship_columns: tuple[RelationshipColumns, ...] = ()


async def load_sql_diagram(session: AsyncSession, database: Databases) -> SqlDiagram:
    """Caller must authorize the database before loading any of its children."""
    tables = tuple(
        (await session.scalars(select(Tables).where(Tables.database_id == database.id))).all()
    )
    columns = tuple(
        (
            await session.scalars(
                select(Columns).join(Tables).where(Tables.database_id == database.id)
            )
        ).all()
    )
    indexes = tuple(
        (
            await session.scalars(
                select(DiagramIndexes).join(Tables).where(Tables.database_id == database.id)
            )
        ).all()
    )
    index_columns = tuple(
        (
            await session.scalars(
                select(DiagramIndexColumns)
                .join(DiagramIndexes)
                .join(Tables)
                .where(Tables.database_id == database.id)
            )
        ).all()
    )
    relationships = tuple(
        (
            await session.scalars(
                select(Relationships).where(Relationships.database_id == database.id)
            )
        ).all()
    )
    relationship_columns = tuple(
        (
            await session.scalars(
                select(RelationshipColumns)
                .join(Relationships)
                .where(Relationships.database_id == database.id)
            )
        ).all()
    )
    return SqlDiagram(
        database, tables, columns, indexes, index_columns, relationships, relationship_columns
    )


def identifier(value: str) -> str:
    if not value or "\x00" in value or len(value.encode("utf-8")) > 63:
        raise SqlExportError(f"Invalid PostgreSQL identifier: {value!r} (maximum 63 UTF-8 bytes)")
    return '"' + value.replace('"', '""') + '"'


def literal(value: str) -> str:
    if "\x00" in value:
        raise SqlExportError("SQL strings cannot contain a NUL character")
    return "'" + value.replace("'", "''") + "'"


def expression(value: str, location: str) -> str:
    """Keep SQL expressions, but reject statement separators/comments and bad quoting."""
    value = value.strip()
    if not value or "\x00" in value:
        raise SqlExportError(f"{location}: empty or invalid SQL expression")
    depth = 0
    i = 0
    while i < len(value):
        char = value[i]
        if char in ("'", '"'):
            quote = char
            i += 1
            while i < len(value):
                if value[i] == quote:
                    if i + 1 < len(value) and value[i + 1] == quote:
                        i += 2
                        continue
                    break
                # E-string escaping would require a separate PostgreSQL lexer.
                if value[i] == "\\" and quote == "'":
                    raise SqlExportError(f"{location}: use SQL literals without backslash escapes")
                i += 1
            else:
                raise SqlExportError(f"{location}: unterminated SQL quote")
        elif char == ";" or value[i : i + 2] in ("--", "/*", "*/") or char == "$":
            raise SqlExportError(f"{location}: expected one SQL expression without comments")
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                raise SqlExportError(f"{location}: unbalanced SQL parentheses")
        elif char == "," and depth == 0:
            raise SqlExportError(f"{location}: expected one SQL expression")
        i += 1
    if depth:
        raise SqlExportError(f"{location}: unbalanced SQL parentheses")
    return value


_TYPES = {
    ColumnType.STRING: "VARCHAR",
    ColumnType.VARCHAR: "VARCHAR",
    ColumnType.CHAR: "CHAR",
    ColumnType.INTEGER: "INTEGER",
    ColumnType.SMALLINT: "SMALLINT",
    ColumnType.BIGINT: "BIGINT",
    ColumnType.FLOAT: "REAL",
    ColumnType.DOUBLE: "DOUBLE PRECISION",
    ColumnType.BOOLEAN: "BOOLEAN",
    ColumnType.DATE: "DATE",
    ColumnType.DATETIME: "TIMESTAMP",
    ColumnType.TIMESTAMP: "TIMESTAMP",
    ColumnType.TIME: "TIME",
    ColumnType.UUID: "UUID",
    ColumnType.TEXT: "TEXT",
    ColumnType.DECIMAL: "NUMERIC",
    ColumnType.NUMERIC: "NUMERIC",
    ColumnType.JSON: "JSON",
    ColumnType.JSONB: "JSONB",
    ColumnType.BINARY: "BYTEA",
    ColumnType.BLOB: "BYTEA",
}
_INTEGER_TYPES = {ColumnType.INTEGER, ColumnType.SMALLINT, ColumnType.BIGINT}
_TEXT_TYPES = {ColumnType.STRING, ColumnType.VARCHAR, ColumnType.CHAR, ColumnType.TEXT}
_METHODS = {"btree", "hash", "gin", "gist", "spgist", "brin"}
_ACTIONS = {
    "no_action": "NO ACTION",
    "restrict": "RESTRICT",
    "cascade": "CASCADE",
    "set_null": "SET NULL",
    "set_default": "SET DEFAULT",
}


def column_type(column: Columns, schema: str) -> tuple[str, str | None]:
    location = f"Column {column.name!r}"
    if column.unsigned:
        raise SqlExportError(f"{location}: PostgreSQL does not support unsigned types")
    if column.type == ColumnType.ENUM:
        labels = column.enum_values
        if not labels or len(set(labels)) != len(labels):
            raise SqlExportError(f"{location}: enum values must be nonempty and distinct")
        if any(len(label.encode("utf-8")) > 63 for label in labels):
            raise SqlExportError(f"{location}: enum label exceeds 63 UTF-8 bytes")
        name = f"wdl_enum_{column.id.hex}"
        sql_type = f"{identifier(schema)}.{identifier(name)}"
        enum_sql = f"CREATE TYPE {sql_type} AS ENUM ({', '.join(literal(v) for v in labels)});"
    else:
        if column.type not in _TYPES:
            raise SqlExportError(f"{location}: type {column.type!r} is not supported by SQL export")
        sql_type = _TYPES[column.type]
        enum_sql = None
    if column.custom_type:
        raise SqlExportError(f"{location}: custom types require definitions and are not supported")
    if column.length is not None:
        if column.type not in {ColumnType.STRING, ColumnType.VARCHAR, ColumnType.CHAR}:
            raise SqlExportError(f"{location}: length is only supported for character types")
        if column.length <= 0:
            raise SqlExportError(f"{location}: length must be positive")
        sql_type += f"({column.length})"
    if column.precision is not None or column.scale is not None:
        if column.type not in {ColumnType.DECIMAL, ColumnType.NUMERIC}:
            raise SqlExportError(f"{location}: precision/scale require a numeric type")
        if column.precision is None or not 1 <= column.precision <= 1000:
            raise SqlExportError(f"{location}: numeric precision must be between 1 and 1000")
        if column.scale is not None and not 0 <= column.scale <= column.precision:
            raise SqlExportError(f"{location}: invalid numeric scale")
        options = str(column.precision)
        if column.scale is not None:
            options += f", {column.scale}"
        sql_type += f"({options})"
    if column.type != ColumnType.ENUM and column.enum_values:
        raise SqlExportError(f"{location}: enum values require an enum type")
    if not 0 <= column.array_dimensions <= 8:
        raise SqlExportError(f"{location}: invalid array dimensions")
    if column.auto_increment and (
        column.type not in _INTEGER_TYPES or column.array_dimensions or column.default is not None
    ):
        raise SqlExportError(f"{location}: identity requires an integer without array/default")
    return sql_type + "[]" * column.array_dimensions, enum_sql


def generate_postgresql_sql(diagram: SqlDiagram) -> str:
    if diagram.database.type != DataBaseName.PSQL:
        raise SqlExportError("SQL export currently supports PostgreSQL (psql) databases only")
    charset = (diagram.database.charset or "UTF8").strip().replace("-", "").upper()
    if charset != "UTF8":
        raise SqlExportError("SQL export currently requires a UTF-8 database charset")
    if diagram.database.collation:
        raise SqlExportError("Database collation export is not supported")
    default_schema = diagram.database.default_schema or "public"
    tables = sorted(
        diagram.tables,
        key=lambda t: (t.schema_name or default_schema, t.sort_order, t.name, str(t.id)),
    )
    by_table = {table.id: table for table in tables}
    by_column = {column.id: column for column in diagram.columns}
    columns: dict[UUID, list[Columns]] = defaultdict(list)
    indexes: dict[UUID, list[DiagramIndexes]] = defaultdict(list)
    members: dict[UUID, list[DiagramIndexColumns]] = defaultdict(list)
    pairs: dict[UUID, list[RelationshipColumns]] = defaultdict(list)
    relation_names: set[tuple[str, str]] = set()
    unique_keys: dict[UUID, set[frozenset[UUID]]] = defaultdict(set)
    primary_keys: dict[UUID, set[UUID]] = defaultdict(set)
    constraints: dict[UUID, set[str]] = defaultdict(set)
    names: dict[UUID, str] = {}
    types: dict[UUID, str] = {}
    enum_types: dict[tuple[str, ...], str] = {}
    enums: list[str] = []
    create_tables: list[str] = []
    create_indexes: list[str] = []
    foreign_keys: list[str] = []
    comments: list[str] = []

    def reserve_relation(schema: str, name: str) -> None:
        identifier(name)
        key = (schema, name)
        if key in relation_names:
            raise SqlExportError(f"Duplicate PostgreSQL relation name: {schema}.{name}")
        relation_names.add(key)

    def constraint(table_id: UUID, name: str) -> str:
        if name in constraints[table_id]:
            raise SqlExportError(f"Duplicate constraint name: {name}")
        constraints[table_id].add(name)
        return identifier(name)

    for table in tables:
        if table.database_id != diagram.database.id:
            raise SqlExportError("Table does not belong to the exported database")
        schema = table.schema_name or default_schema
        names[table.id] = f"{identifier(schema)}.{identifier(table.name)}"
        reserve_relation(schema, table.name)
    for column in diagram.columns:
        if column.table_id not in by_table:
            raise SqlExportError("Column refers to a table outside the exported database")
        columns[column.table_id].append(column)
    for index in diagram.indexes:
        if index.table_id not in by_table:
            raise SqlExportError("Index refers to a table outside the exported database")
        indexes[index.table_id].append(index)
    for member in diagram.index_columns:
        members[member.index_id].append(member)
    for pair in diagram.relationship_columns:
        pairs[pair.relationship_id].append(pair)

    for table in tables:
        schema = table.schema_name or default_schema
        table_columns = sorted(columns[table.id], key=lambda c: (c.sort_order, c.name, str(c.id)))
        column_names: set[str] = set()
        definitions: list[str] = []
        flags = [c.id for c in table_columns if c.primary_key]
        primary_indexes = [i for i in indexes[table.id] if i.type == IndexType.PRIMARY]
        if len(primary_indexes) > 1:
            raise SqlExportError(f"Table {table.name!r}: multiple primary keys")
        primary = flags
        primary_name = f"wdl_pk_{table.id.hex}"
        if primary_indexes:
            index = primary_indexes[0]
            primary = [m.column_id for m in sorted(members[index.id], key=lambda m: m.position)]
            primary_name = index.name or primary_name
            if flags and set(flags) != set(primary):
                raise SqlExportError(f"Table {table.name!r}: conflicting primary key definitions")
        primary_keys[table.id] = set(primary)
        for column in table_columns:
            if column.name in column_names:
                raise SqlExportError(f"Table {table.name!r}: duplicate column {column.name!r}")
            column_names.add(column.name)
            sql_type, enum = column_type(column, schema)
            types[column.id] = sql_type
            if enum:
                enum_key = tuple(column.enum_values)
                if enum_key not in enum_types:
                    enum_types[enum_key] = (
                        f"{identifier(schema)}.{identifier(f'wdl_enum_{column.id.hex}')}"
                    )
                    reserve_relation(schema, f"wdl_enum_{column.id.hex}")
                    enums.append(enum)
                sql_type = enum_types[enum_key] + "[]" * column.array_dimensions
                types[column.id] = sql_type
            if column.type == ColumnType.JSON and (column.unique or column.id in primary):
                raise SqlExportError(f"Column {column.name!r}: JSON keys require jsonb")
            definition = f"{identifier(column.name)} {sql_type}"
            if column.auto_increment:
                definition += " GENERATED BY DEFAULT AS IDENTITY"
            if not column.nullable or column.id in primary or column.auto_increment:
                definition += " NOT NULL"
            if column.default is not None:
                definition += " DEFAULT " + expression(
                    column.default, f"{table.name}.{column.name} default"
                )
            if column.unique:
                unique_name = f"wdl_uq_{column.id.hex}"
                reserve_relation(schema, unique_name)
                definition += f" CONSTRAINT {constraint(table.id, unique_name)} UNIQUE"
                unique_keys[table.id].add(frozenset([column.id]))
            if column.check:
                definition += (
                    " CHECK (" + expression(column.check, f"{table.name}.{column.name} check") + ")"
                )
            definitions.append(definition)
            if column.notice:
                comments.append(
                    f"COMMENT ON COLUMN {names[table.id]}.{identifier(column.name)} "
                    f"IS {literal(column.notice)};"
                )
        for index in sorted(indexes[table.id], key=lambda i: (i.name or "", str(i.id))):
            entries = sorted(members[index.id], key=lambda m: m.position)
            ids = [m.column_id for m in entries]
            if (
                not ids
                or len(set(ids)) != len(ids)
                or len({m.position for m in entries}) != len(entries)
            ):
                raise SqlExportError(f"Index {index.name or index.id}: invalid column list")
            if any(i not in by_column or by_column[i].table_id != table.id for i in ids):
                raise SqlExportError(
                    f"Index {index.name or index.id}: column belongs to another table"
                )
            if any(by_column[i].type == ColumnType.JSON for i in ids):
                raise SqlExportError(
                    f"Index {index.name or index.id}: JSON indexing requires jsonb"
                )
            method = (index.method or "btree").lower()
            if method not in _METHODS or index.type == IndexType.FULLTEXT:
                raise SqlExportError(
                    f"Index {index.name or index.id}: unsupported index type/method"
                )
            if index.type not in {IndexType.PRIMARY, IndexType.UNIQUE, IndexType.INDEX}:
                raise SqlExportError(f"Index {index.id}: unsupported index type")
            if index.type in {IndexType.PRIMARY, IndexType.UNIQUE} and method != "btree":
                raise SqlExportError(
                    f"Index {index.name or index.id}: unique/primary requires btree"
                )
            if index.type == IndexType.PRIMARY:
                if index.where or any(m.sort_order != "asc" for m in entries):
                    raise SqlExportError(
                        "Primary keys do not support predicates or descending columns"
                    )
                continue
            name = index.name or f"wdl_idx_{index.id.hex}"
            reserve_relation(schema, name)
            rendered = []
            for member in entries:
                if member.sort_order not in {"asc", "desc"}:
                    raise SqlExportError(f"Index {name}: invalid sort order")
                if method != "btree" and member.sort_order == "desc":
                    raise SqlExportError(f"Index {name}: sort order requires btree")
                rendered.append(
                    identifier(by_column[member.column_id].name)
                    + (" DESC" if member.sort_order == "desc" else "")
                )
            unique = "UNIQUE " if index.type == IndexType.UNIQUE else ""
            sql = (
                f"CREATE {unique}INDEX {identifier(name)} ON {names[table.id]} "
                f"USING {method} ({', '.join(rendered)})"
            )
            if index.where:
                sql += " WHERE " + expression(index.where, f"Index {name} predicate")
            elif index.type == IndexType.UNIQUE:
                unique_keys[table.id].add(frozenset(ids))
            create_indexes.append(sql + ";")
        if primary:
            if any(i not in by_column or by_column[i].table_id != table.id for i in primary):
                raise SqlExportError(f"Table {table.name!r}: invalid primary key columns")
            reserve_relation(schema, primary_name)
            definitions.append(
                f"CONSTRAINT {constraint(table.id, primary_name)} PRIMARY KEY "
                f"({', '.join(identifier(by_column[i].name) for i in primary)})"
            )
            unique_keys[table.id].add(frozenset(primary))
        create_tables.append(
            f"CREATE TABLE {names[table.id]} (\n    " + ",\n    ".join(definitions) + "\n);"
        )
        table_comment = "\n\n".join(v for v in [table.description, table.notice] if v)
        if table_comment:
            comments.append(f"COMMENT ON TABLE {names[table.id]} IS {literal(table_comment)};")

    for relationship in sorted(diagram.relationships, key=lambda r: (r.name or "", str(r.id))):
        source, target = relationship.source_table_id, relationship.target_table_id
        if (
            relationship.database_id != diagram.database.id
            or source not in by_table
            or target not in by_table
        ):
            raise SqlExportError("Relationship refers to a table outside the exported database")
        mappings = sorted(
            pairs[relationship.id],
            key=lambda p: (
                by_column[p.source_column_id].sort_order if p.source_column_id in by_column else 0,
                str(p.source_column_id),
                str(p.target_column_id),
            ),
        )
        source_ids = [p.source_column_id for p in mappings]
        target_ids = [p.target_column_id for p in mappings]
        if (
            not mappings
            or len(set(source_ids)) != len(source_ids)
            or len(set(target_ids)) != len(target_ids)
        ):
            raise SqlExportError(
                f"Relationship {relationship.name or relationship.id}: invalid column pairs"
            )
        for mapping in mappings:
            a, b = by_column.get(mapping.source_column_id), by_column.get(mapping.target_column_id)
            if a is None or b is None or a.table_id != source or b.table_id != target:
                raise SqlExportError("Relationship columns do not belong to their endpoint tables")
            same_family = (
                a.type in _INTEGER_TYPES
                and b.type in _INTEGER_TYPES
                or a.type in _TEXT_TYPES
                and b.type in _TEXT_TYPES
                or a.type in {ColumnType.NUMERIC, ColumnType.DECIMAL}
                and b.type in {ColumnType.NUMERIC, ColumnType.DECIMAL}
            )
            if types[a.id] != types[b.id] and not (
                same_family and a.array_dimensions == b.array_dimensions
            ):
                raise SqlExportError(
                    f"Relationship {relationship.name or relationship.id}: "
                    "incompatible column types"
                )
            if relationship.on_delete == "set_null" or relationship.on_update == "set_null":
                if not a.nullable or a.id in primary_keys[source] or a.auto_increment:
                    raise SqlExportError(
                        f"Relationship {relationship.name or relationship.id}: "
                        "SET NULL requires nullable source columns"
                    )
        if frozenset(target_ids) not in unique_keys[target]:
            raise SqlExportError(
                f"Relationship {relationship.name or relationship.id}: "
                "target columns require a primary or nonpartial unique key"
            )
        if relationship.on_delete not in _ACTIONS or relationship.on_update not in _ACTIONS:
            raise SqlExportError("Unsupported foreign key action")
        name = relationship.name or f"wdl_fk_{relationship.id.hex}"
        foreign_keys.append(
            f"ALTER TABLE {names[source]} ADD CONSTRAINT {constraint(source, name)} "
            f"FOREIGN KEY ({', '.join(identifier(by_column[i].name) for i in source_ids)}) "
            f"REFERENCES {names[target]} "
            f"({', '.join(identifier(by_column[i].name) for i in target_ids)}) "
            f"ON DELETE {_ACTIONS[relationship.on_delete]} "
            f"ON UPDATE {_ACTIONS[relationship.on_update]};"
        )

    schemas = sorted({t.schema_name or default_schema for t in tables})
    statements = [
        "-- Generated by WDL. PostgreSQL schema only; run in an empty target database.",
        "BEGIN;",
        "SET LOCAL standard_conforming_strings = on;",
        "SET LOCAL client_encoding = 'UTF8';",
    ]
    statements += [f"CREATE SCHEMA IF NOT EXISTS {identifier(s)};" for s in schemas]
    statements += enums + create_tables + create_indexes + foreign_keys + comments
    statements += ["COMMIT;"]
    return "\n\n".join(statements) + "\n"
