"""studio calendar tokens (S17)

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-29 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "studio_calendar_tokens",
        sa.Column("home_id", sa.UUID(), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["home_id"], ["homes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("home_id"),
    )
    op.create_index(
        "ix_studio_calendar_tokens_token", "studio_calendar_tokens", ["token"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_studio_calendar_tokens_token", table_name="studio_calendar_tokens")
    op.drop_table("studio_calendar_tokens")
