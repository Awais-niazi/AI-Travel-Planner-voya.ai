"""add trip and itinerary indexes

Revision ID: e5d4d7c8a1b2
Revises: 926229ea96c6
Create Date: 2026-04-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e5d4d7c8a1b2"
down_revision: Union[str, None] = "926229ea96c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_trips_user_id_created_at",
        "trips",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_itineraries_trip_id",
        "itineraries",
        ["trip_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_itineraries_trip_id_day_number",
        "itineraries",
        ["trip_id", "day_number"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_itineraries_trip_id_day_number",
        "itineraries",
        type_="unique",
    )
    op.drop_index("ix_itineraries_trip_id", table_name="itineraries")
    op.drop_index("ix_trips_user_id_created_at", table_name="trips")
