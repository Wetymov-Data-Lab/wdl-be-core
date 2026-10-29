"""Add per-user undo/redo journal of diagram changes.

Revision ID: 20261029_0004
Revises: 20261029_0003
Create Date: 2026-10-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261029_0004"
down_revision: str | None = "20261029_0003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "diagram_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("database_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("changes", sa.JSON(), nullable=False),
        sa.Column("is_undone", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["database_id"], ["databases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_diagram_history_database_actor",
        "diagram_history",
        ["database_id", "actor_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_diagram_history_database_actor", table_name="diagram_history")
    op.drop_table("diagram_history")
