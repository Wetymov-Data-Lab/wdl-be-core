"""Add table-level CHECK constraints.

Revision ID: 20261029_0003
Revises: 20260909_0002
Create Date: 2026-10-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261029_0003"
down_revision: str | None = "20260909_0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tables",
        sa.Column("checks", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.alter_column("tables", "checks", server_default=None)


def downgrade() -> None:
    op.drop_column("tables", "checks")
