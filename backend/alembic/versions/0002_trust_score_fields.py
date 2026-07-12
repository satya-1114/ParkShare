"""add trust score fields

Adds phone_verified and id_verified to users table, and photos_verified to
parking_spaces table. All new columns are non-nullable with a default of false.

Revision ID: 0002_trust_score_fields
Revises: 0001_initial
Create Date: 2026-07-15
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_trust_score_fields"
down_revision: Union[str, None] = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("phone_verified", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "users",
        sa.Column("id_verified", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "parking_spaces",
        sa.Column("photos_verified", sa.Boolean, nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("parking_spaces", "photos_verified")
    op.drop_column("users", "id_verified")
    op.drop_column("users", "phone_verified")
