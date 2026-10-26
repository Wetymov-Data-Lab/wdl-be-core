"""Create the initial engine and diagram schema.

Revision ID: 20260723_0001
Revises:
Create Date: 2026-07-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str                       = "20260723_0001"
down_revision: str | None           = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None    = None


def audit_columns() -> list[sa.Column[object]]:
    """Return columns shared by audited entities."""

    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("author_id", sa.Uuid(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "realms",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("visibility", sa.String(length=32), nullable=False),
        sa.Column("settings", sa.JSON(), nullable=False),
        sa.Column("notice", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "status IN ('active', 'archived', 'disabled')",
            name="ck_realms_status",
        ),
        sa.CheckConstraint(
            "visibility IN ('private', 'internal', 'public')",
            name="ck_realms_visibility",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("notice", sa.String(length=255), nullable=True),
        sa.Column("realm_id", sa.Uuid(), nullable=False),
        *audit_columns(),
        sa.ForeignKeyConstraint(["realm_id"], ["realms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("realm_id", "name", name="uq_projects_realm_id_name"),
    )
    op.create_index("ix_projects_realm_id", "projects", ["realm_id"])

    op.create_table(
        "databases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("notice", sa.String(length=255), nullable=True),
        sa.Column("default_schema", sa.String(length=255), nullable=True),
        sa.Column("charset", sa.String(length=64), nullable=True),
        sa.Column("collation_name", sa.String(length=128), nullable=True),
        *audit_columns(),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "name", name="uq_databases_project_id_name"),
    )
    op.create_index("ix_databases_project_id", "databases", ["project_id"])

    op.create_table(
        "canvas_states",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("database_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("viewport_x", sa.Float(), nullable=False),
        sa.Column("viewport_y", sa.Float(), nullable=False),
        sa.Column("zoom", sa.Float(), nullable=False),
        sa.Column("grid_size", sa.Integer(), nullable=False),
        sa.Column("snap_to_grid", sa.Boolean(), nullable=False),
        sa.Column("show_relationship_labels", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "grid_size >= 1 AND grid_size <= 200",
            name="ck_canvas_states_grid_size",
        ),
        sa.CheckConstraint("zoom > 0 AND zoom <= 8", name="ck_canvas_states_zoom"),
        sa.ForeignKeyConstraint(["database_id"], ["databases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "database_id",
            "user_id",
            name="uq_canvas_states_database_user",
        ),
    )
    op.create_index("ix_canvas_states_database_id", "canvas_states", ["database_id"])

    op.create_table(
        "tables",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("database_id", sa.Uuid(), nullable=False),
        sa.Column("schema_name", sa.String(length=255), nullable=True),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("notice", sa.String(length=255), nullable=True),
        sa.Column("color", sa.String(length=7), nullable=True),
        sa.Column("position_x", sa.Float(), nullable=False),
        sa.Column("position_y", sa.Float(), nullable=False),
        sa.Column("width", sa.Float(), nullable=True),
        sa.Column("is_collapsed", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        *audit_columns(),
        sa.CheckConstraint(
            "color IS NULL OR color ~ '^#[0-9A-Fa-f]{6}$'",
            name="ck_tables_color",
        ),
        sa.CheckConstraint("sort_order >= 0", name="ck_tables_sort_order"),
        sa.CheckConstraint("width IS NULL OR width > 0", name="ck_tables_width"),
        sa.ForeignKeyConstraint(["database_id"], ["databases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "database_id",
            "schema_name",
            "name",
            name="uq_tables_database_schema_name",
        ),
    )
    op.create_index("ix_tables_database_id", "tables", ["database_id"])

    op.create_table(
        "columns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("table_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("custom_type", sa.String(length=255), nullable=True),
        sa.Column("length", sa.Integer(), nullable=True),
        sa.Column("precision", sa.Integer(), nullable=True),
        sa.Column("scale", sa.Integer(), nullable=True),
        sa.Column("array_dimensions", sa.Integer(), nullable=False),
        sa.Column("nullable", sa.Boolean(), nullable=False),
        sa.Column("primary_key", sa.Boolean(), nullable=False),
        sa.Column("unique", sa.Boolean(), nullable=False),
        sa.Column("auto_increment", sa.Boolean(), nullable=False),
        sa.Column("unsigned", sa.Boolean(), nullable=False),
        sa.Column("default", sa.String(length=2_000), nullable=True),
        sa.Column("check", sa.String(length=4_000), nullable=True),
        sa.Column("enum_values", sa.JSON(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("notice", sa.String(length=255), nullable=True),
        *audit_columns(),
        sa.CheckConstraint(
            "array_dimensions >= 0 AND array_dimensions <= 8",
            name="ck_columns_array_dimensions",
        ),
        sa.CheckConstraint("length IS NULL OR length > 0", name="ck_columns_length"),
        sa.CheckConstraint(
            "precision IS NULL OR precision > 0",
            name="ck_columns_precision",
        ),
        sa.CheckConstraint("scale IS NULL OR scale >= 0", name="ck_columns_scale"),
        sa.CheckConstraint(
            "precision IS NULL OR scale IS NULL OR scale <= precision",
            name="ck_columns_scale_precision",
        ),
        sa.CheckConstraint("sort_order >= 0", name="ck_columns_sort_order"),
        sa.ForeignKeyConstraint(["table_id"], ["tables.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("table_id", "name", name="uq_columns_table_id_name"),
    )
    op.create_index("ix_columns_table_id", "columns", ["table_id"])

    op.create_table(
        "diagram_groups",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("database_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("position_x", sa.Float(), nullable=False),
        sa.Column("position_y", sa.Float(), nullable=False),
        sa.Column("width", sa.Float(), nullable=False),
        sa.Column("height", sa.Float(), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=True),
        sa.Column("is_collapsed", sa.Boolean(), nullable=False),
        *audit_columns(),
        sa.CheckConstraint(
            "color IS NULL OR color ~ '^#[0-9A-Fa-f]{6}$'",
            name="ck_diagram_groups_color",
        ),
        sa.CheckConstraint("height > 0", name="ck_diagram_groups_height"),
        sa.CheckConstraint("width > 0", name="ck_diagram_groups_width"),
        sa.ForeignKeyConstraint(["database_id"], ["databases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "database_id",
            "name",
            name="uq_diagram_groups_database_name",
        ),
    )
    op.create_index("ix_diagram_groups_database_id", "diagram_groups", ["database_id"])

    op.create_table(
        "diagram_indexes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("table_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("method", sa.String(length=64), nullable=True),
        sa.Column("where", sa.String(length=4_000), nullable=True),
        *audit_columns(),
        sa.ForeignKeyConstraint(["table_id"], ["tables.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "table_id",
            "name",
            name="uq_diagram_indexes_table_id_name",
        ),
    )
    op.create_index("ix_diagram_indexes_table_id", "diagram_indexes", ["table_id"])

    op.create_table(
        "diagram_notes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("database_id", sa.Uuid(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("position_x", sa.Float(), nullable=False),
        sa.Column("position_y", sa.Float(), nullable=False),
        sa.Column("width", sa.Float(), nullable=False),
        sa.Column("height", sa.Float(), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=True),
        *audit_columns(),
        sa.CheckConstraint(
            "color IS NULL OR color ~ '^#[0-9A-Fa-f]{6}$'",
            name="ck_diagram_notes_color",
        ),
        sa.CheckConstraint("height > 0", name="ck_diagram_notes_height"),
        sa.CheckConstraint("width > 0", name="ck_diagram_notes_width"),
        sa.ForeignKeyConstraint(["database_id"], ["databases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_diagram_notes_database_id", "diagram_notes", ["database_id"])

    op.create_table(
        "relationships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("database_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("source_table_id", sa.Uuid(), nullable=False),
        sa.Column("target_table_id", sa.Uuid(), nullable=False),
        sa.Column("source_cardinality", sa.String(length=32), nullable=False),
        sa.Column("target_cardinality", sa.String(length=32), nullable=False),
        sa.Column("on_delete", sa.String(length=32), nullable=False),
        sa.Column("on_update", sa.String(length=32), nullable=False),
        sa.Column("waypoints", sa.JSON(), nullable=False),
        *audit_columns(),
        sa.ForeignKeyConstraint(["database_id"], ["databases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_table_id"], ["tables.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_table_id"], ["tables.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "database_id",
            "name",
            name="uq_relationships_database_id_name",
        ),
    )
    op.create_index("ix_relationships_database_id", "relationships", ["database_id"])
    op.create_index(
        "ix_relationships_source_table_id",
        "relationships",
        ["source_table_id"],
    )
    op.create_index(
        "ix_relationships_target_table_id",
        "relationships",
        ["target_table_id"],
    )

    op.create_table(
        "diagram_group_tables",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("table_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["diagram_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["table_id"], ["tables.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("table_id", name="uq_diagram_group_tables_table_id"),
    )
    op.create_index(
        "ix_diagram_group_tables_group_id",
        "diagram_group_tables",
        ["group_id"],
    )
    op.create_index(
        "ix_diagram_group_tables_table_id",
        "diagram_group_tables",
        ["table_id"],
    )

    op.create_table(
        "diagram_index_columns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("index_id", sa.Uuid(), nullable=False),
        sa.Column("column_id", sa.Uuid(), nullable=False),
        sa.Column("sort_order", sa.String(length=8), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint("position >= 0", name="ck_index_columns_position"),
        sa.ForeignKeyConstraint(
            ["column_id"],
            ["columns.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["index_id"],
            ["diagram_indexes.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "index_id",
            "column_id",
            name="uq_index_columns_index_column",
        ),
        sa.UniqueConstraint(
            "index_id",
            "position",
            name="uq_index_columns_index_position",
        ),
    )
    op.create_index(
        "ix_diagram_index_columns_column_id",
        "diagram_index_columns",
        ["column_id"],
    )
    op.create_index(
        "ix_diagram_index_columns_index_id",
        "diagram_index_columns",
        ["index_id"],
    )

    op.create_table(
        "relationship_columns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("relationship_id", sa.Uuid(), nullable=False),
        sa.Column("source_column_id", sa.Uuid(), nullable=False),
        sa.Column("target_column_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["relationship_id"],
            ["relationships.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_column_id"],
            ["columns.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_column_id"],
            ["columns.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "relationship_id",
            "source_column_id",
            "target_column_id",
            name="uq_relationship_columns_mapping",
        ),
    )
    op.create_index(
        "ix_relationship_columns_relationship_id",
        "relationship_columns",
        ["relationship_id"],
    )
    op.create_index(
        "ix_relationship_columns_source_column_id",
        "relationship_columns",
        ["source_column_id"],
    )
    op.create_index(
        "ix_relationship_columns_target_column_id",
        "relationship_columns",
        ["target_column_id"],
    )


def downgrade() -> None:
    op.drop_table("relationship_columns")
    op.drop_table("diagram_index_columns")
    op.drop_table("diagram_group_tables")
    op.drop_table("relationships")
    op.drop_table("diagram_notes")
    op.drop_table("diagram_indexes")
    op.drop_table("diagram_groups")
    op.drop_table("columns")
    op.drop_table("tables")
    op.drop_table("canvas_states")
    op.drop_table("databases")
    op.drop_table("projects")
    op.drop_table("realms")
