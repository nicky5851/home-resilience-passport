"""studio damp answers (S11)

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-28 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "studio_damp_answers",
        sa.Column("home_id", sa.UUID(), nullable=False),
        sa.Column("occupants", sa.Integer(), nullable=False),
        sa.Column("dries_clothes_indoors", sa.Boolean(), nullable=False),
        sa.Column("kitchen_extractor", sa.Boolean(), nullable=False),
        sa.Column("bathroom_extractor", sa.Boolean(), nullable=False),
        sa.Column("trickle_vents", sa.Boolean(), nullable=False),
        sa.Column("heating_setpoint_c", sa.Float(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["home_id"], ["homes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("home_id"),
    )


def downgrade() -> None:
    op.drop_table("studio_damp_answers")
