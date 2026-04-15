"""add trip generation jobs

Revision ID: f1b2c3d4e5f6
Revises: e5d4d7c8a1b2
Create Date: 2026-04-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1b2c3d4e5f6"
down_revision: Union[str, None] = "e5d4d7c8a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trip_generation_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("trip_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_trip_generation_jobs_trip_id_status",
        "trip_generation_jobs",
        ["trip_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_trip_generation_jobs_user_id_created_at",
        "trip_generation_jobs",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_trip_generation_jobs_user_id_created_at", table_name="trip_generation_jobs")
    op.drop_index("ix_trip_generation_jobs_trip_id_status", table_name="trip_generation_jobs")
    op.drop_table("trip_generation_jobs")
