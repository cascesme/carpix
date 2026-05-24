"""create vehicle_images table

Revision ID: 0001
Revises:
Create Date: 2026-05-23

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vehicle_images",
        sa.Column("brand_key", sa.String(), nullable=False),
        sa.Column("model_key", sa.String(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("local_path", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("file_title", sa.Text(), nullable=False),
        sa.Column(
            "cached_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("brand_key", "model_key", "year"),
    )


def downgrade() -> None:
    op.drop_table("vehicle_images")
