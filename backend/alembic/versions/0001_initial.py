"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# WHY postgresql.ENUM IS USED INSTEAD OF sa.Enum
# ---------------------------------------------------------------------------
# sa.Enum(name="x", create_type=False) does NOT work in SQLAlchemy 2.x.
#
# When sa.Enum is used as a column type, _on_table_create() calls
# dialect_impl(bind.dialect) to obtain the PostgreSQL-specific implementation.
# That impl is a fresh postgresql.ENUM constructed from the sa.Enum's enums
# list (which is EMPTY for name-only declarations) and with create_type=True
# (the default), discarding the create_type=False flag entirely.
# This causes op.create_table() to emit:
#
#     CREATE TYPE user_role AS ENUM ()
#
# even though the type was already created, producing:
#
#     asyncpg.exceptions.DuplicateObjectError: type "user_role" already exists
#
# postgresql.ENUM has its own create_type attribute that survives through
# dialect_impl() — verified by checking that:
#
#     postgresql.ENUM(..., create_type=False)._check_for_name_in_memos(...)
#
# returns True (= "skip CREATE TYPE") regardless of _ddl_runner presence,
# while sa.Enum(name=..., create_type=False) dispatches to an impl whose
# create_type is True because sa.Enum itself has no create_type attribute.
#
# STRATEGY:
# 1. Two postgresql.ENUM objects per enum type — sharing the same name:
#    a. A "creator" with full values and create_type=True (default).
#       Used only in the explicit e.create(bind, checkfirst=True) loop.
#    b. A "reference" with full values and create_type=False.
#       Used for every column definition inside op.create_table().
#
#    Both objects carry the canonical enum values so that DROP TYPE works
#    correctly on the creator objects in the downgrade loop.
#    The reference objects carry values too (no functional difference, but
#    makes the declaration self-documenting and avoids surprises).
# ---------------------------------------------------------------------------

# "Creator" objects — used in the explicit create/drop loop only.
_user_role_c       = postgresql.ENUM("DRIVER", "OWNER", "ADMIN",
                                     name="user_role")
_property_type_c   = postgresql.ENUM("INDIVIDUAL_HOUSE", "APARTMENT",
                                     "COMMERCIAL_BUILDING", "HOTEL",
                                     "OFFICE", "EMPTY_LAND",
                                     name="property_type")
_parking_type_c    = postgresql.ENUM("COVERED", "OPEN",
                                     name="parking_type")
_parking_status_c  = postgresql.ENUM("PENDING", "VERIFIED", "REJECTED",
                                     "INACTIVE",
                                     name="parking_status")
_vehicle_type_c    = postgresql.ENUM("BIKE", "CAR", "EV", "TRUCK",
                                     "BICYCLE",
                                     name="vehicle_type")
_amenity_c         = postgresql.ENUM("CCTV", "COVERED", "SECURITY",
                                     "EV_CHARGING", "ACCESS_24X7",
                                     name="amenity")
_booking_status_c  = postgresql.ENUM("PENDING", "CONFIRMED", "ACTIVE",
                                     "COMPLETED", "CANCELLED",
                                     name="booking_status")

# Ordered tuple used in the upgrade create loop and (reversed) in downgrade.
_ALL_CREATORS = (
    _user_role_c, _property_type_c, _parking_type_c, _parking_status_c,
    _vehicle_type_c, _amenity_c, _booking_status_c,
)

# "Reference" objects — create_type=False so op.create_table() never emits
# CREATE TYPE.  _check_for_name_in_memos() returns True immediately because
# postgresql.ENUM.create_type is False, suppressing the DDL event entirely.
_user_role       = postgresql.ENUM("DRIVER", "OWNER", "ADMIN",
                                   name="user_role",       create_type=False)
_property_type   = postgresql.ENUM("INDIVIDUAL_HOUSE", "APARTMENT",
                                   "COMMERCIAL_BUILDING", "HOTEL",
                                   "OFFICE", "EMPTY_LAND",
                                   name="property_type",   create_type=False)
_parking_type    = postgresql.ENUM("COVERED", "OPEN",
                                   name="parking_type",    create_type=False)
_parking_status  = postgresql.ENUM("PENDING", "VERIFIED", "REJECTED",
                                   "INACTIVE",
                                   name="parking_status",  create_type=False)
_vehicle_type    = postgresql.ENUM("BIKE", "CAR", "EV", "TRUCK",
                                   "BICYCLE",
                                   name="vehicle_type",    create_type=False)
_amenity         = postgresql.ENUM("CCTV", "COVERED", "SECURITY",
                                   "EV_CHARGING", "ACCESS_24X7",
                                   name="amenity",         create_type=False)
_booking_status  = postgresql.ENUM("PENDING", "CONFIRMED", "ACTIVE",
                                   "COMPLETED", "CANCELLED",
                                   name="booking_status",  create_type=False)


def upgrade() -> None:
    bind = op.get_bind()

    # Step 1 — create each PostgreSQL enum type exactly once.
    # checkfirst=True is idempotent against partially-applied databases.
    for e in _ALL_CREATORS:
        e.create(bind, checkfirst=True)

    # Step 2 — create tables.
    # Every column that holds an enum uses the _reference_ postgresql.ENUM
    # (create_type=False), so op.create_table() emits no CREATE TYPE.

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", _user_role, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "parking_spaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("property_type", _property_type, nullable=False),
        sa.Column("address", sa.String(500), nullable=False),
        sa.Column("city", sa.String(120), nullable=False),
        sa.Column("state", sa.String(120), nullable=False),
        sa.Column("pin_code", sa.String(10), nullable=False),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("total_slots", sa.Integer, nullable=False),
        sa.Column("available_slots", sa.Integer, nullable=False),
        sa.Column("parking_type", _parking_type, nullable=False),
        sa.Column("hourly_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("daily_price", sa.Numeric(10, 2)),
        sa.Column("is_24x7", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("opening_time", sa.Time),
        sa.Column("closing_time", sa.Time),
        sa.Column("status", _parking_status, nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_parking_spaces_owner_id", "parking_spaces", ["owner_id"])
    op.create_index("ix_parking_spaces_city",     "parking_spaces", ["city"])
    op.create_index("ix_parking_spaces_status",   "parking_spaces", ["status"])
    op.create_index("ix_parking_status_city",     "parking_spaces", ["status", "city"])

    op.create_table(
        "parking_vehicle_types",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("parking_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("parking_spaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vehicle_type", _vehicle_type, nullable=False),
        sa.UniqueConstraint("parking_id", "vehicle_type", name="uq_parking_vehicle"),
    )

    op.create_table(
        "parking_amenities",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("parking_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("parking_spaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amenity", _amenity, nullable=False),
        sa.UniqueConstraint("parking_id", "amenity", name="uq_parking_amenity"),
    )

    op.create_table(
        "parking_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("parking_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("parking_spaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("image_url", sa.String(1000), nullable=False),
        sa.Column("display_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_parking_images_parking_id", "parking_images", ["parking_id"])

    op.create_table(
        "bookings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("driver_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parking_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("parking_spaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("booking_reference", sa.String(32), nullable=False, unique=True),
        sa.Column("booking_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer, nullable=False),
        sa.Column("total_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", _booking_status, nullable=False, server_default="CONFIRMED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_bookings_driver_id",         "bookings", ["driver_id"])
    op.create_index("ix_bookings_parking_id",        "bookings", ["parking_id"])
    op.create_index("ix_bookings_status",            "bookings", ["status"])
    op.create_index("ix_bookings_booking_reference", "bookings", ["booking_reference"],
                    unique=True)


def downgrade() -> None:
    # Drop tables first (leaf → root), then enum types.
    # PostgreSQL refuses DROP TYPE while any column still references the type.
    op.drop_index("ix_bookings_booking_reference", table_name="bookings")
    op.drop_index("ix_bookings_status",            table_name="bookings")
    op.drop_index("ix_bookings_parking_id",        table_name="bookings")
    op.drop_index("ix_bookings_driver_id",         table_name="bookings")
    op.drop_table("bookings")

    op.drop_index("ix_parking_images_parking_id", table_name="parking_images")
    op.drop_table("parking_images")
    op.drop_table("parking_amenities")
    op.drop_table("parking_vehicle_types")

    op.drop_index("ix_parking_status_city",       table_name="parking_spaces")
    op.drop_index("ix_parking_spaces_status",     table_name="parking_spaces")
    op.drop_index("ix_parking_spaces_city",       table_name="parking_spaces")
    op.drop_index("ix_parking_spaces_owner_id",   table_name="parking_spaces")
    op.drop_table("parking_spaces")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    # Drop enum types after all referencing tables are gone.
    # Use the creator objects (they carry the full value list required for
    # correct postgresql.ENUM.drop() behaviour).
    bind = op.get_bind()
    for e in reversed(_ALL_CREATORS):
        e.drop(bind, checkfirst=True)
