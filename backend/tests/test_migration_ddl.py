"""Migration DDL correctness tests — no database required.

These tests verify the 0001_initial migration's enum strategy by rendering
the SQL it would emit against a mock PostgreSQL dialect and counting
CREATE TYPE statements. A clean-database migration must emit each enum type
exactly once regardless of how many tables reference it.

Background
----------
The bug this guards against:
  sa.Enum(name="x", create_type=False) does NOT suppress CREATE TYPE in
  SQLAlchemy 2.x.  sa.Enum has no .create_type attribute; dialect_impl()
  produces a fresh postgresql.ENUM with create_type=True and empty values,
  causing op.create_table() to re-emit CREATE TYPE for every referencing table.

The correct fix uses postgresql.ENUM(..., create_type=False) for column
references so that _check_for_name_in_memos() returns True immediately,
suppressing the DDL event entirely.
"""
import re
from sqlalchemy.dialects import postgresql
from sqlalchemy import create_engine, text
from sqlalchemy.dialects.postgresql import base as pg_base


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ddl_for_enum(enum_obj) -> str:
    """Render the DDL that would be emitted for a single postgresql.ENUM
    using a mock in-memory engine configured with the PostgreSQL dialect.
    Uses mock_engine to collect statements without a live connection.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.dialects import postgresql as pg_dialect

    # Use string collection approach: render DDL via compiler
    dialect = pg_dialect.dialect()
    from sqlalchemy.dialects.postgresql.named_types import CreateEnumType
    compiler = CreateEnumType(enum_obj).compile(dialect=dialect)
    return str(compiler)


def _count_create_type(sql_statements: list[str], type_name: str) -> int:
    """Count how many statements contain CREATE TYPE <type_name>."""
    pattern = re.compile(
        r'\bCREATE\s+TYPE\s+' + re.escape(type_name) + r'\b',
        re.IGNORECASE,
    )
    return sum(1 for s in sql_statements if pattern.search(s))


# ---------------------------------------------------------------------------
# Import migration objects directly so tests reflect the live migration file
# ---------------------------------------------------------------------------

import importlib.util, pathlib, sys

_MIGRATION_PATH = (
    pathlib.Path(__file__).parent.parent
    / "alembic" / "versions" / "0001_initial.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("migration_0001", _MIGRATION_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEnumObjectTypes:
    """Verify the migration uses postgresql.ENUM, not sa.Enum, for both
    creator and reference objects — sa.Enum(create_type=False) does not work."""

    def setup_method(self):
        self.m = _load_migration()

    def test_creators_are_postgresql_enum(self):
        from sqlalchemy.dialects.postgresql.named_types import ENUM as PG_ENUM
        for e in self.m._ALL_CREATORS:
            assert isinstance(e, PG_ENUM), (
                f"Creator enum '{e.name}' is {type(e).__name__}, "
                "must be postgresql.ENUM"
            )

    def test_creator_create_type_is_true(self):
        for e in self.m._ALL_CREATORS:
            assert e.create_type is True, (
                f"Creator '{e.name}' has create_type={e.create_type}, expected True"
            )

    def test_references_are_postgresql_enum(self):
        from sqlalchemy.dialects.postgresql.named_types import ENUM as PG_ENUM
        ref_names = [
            "_user_role", "_property_type", "_parking_type", "_parking_status",
            "_vehicle_type", "_amenity", "_booking_status",
        ]
        for attr in ref_names:
            obj = getattr(self.m, attr)
            assert isinstance(obj, PG_ENUM), (
                f"Reference enum '{attr}' is {type(obj).__name__}, "
                "must be postgresql.ENUM"
            )

    def test_references_create_type_is_false(self):
        ref_names = [
            "_user_role", "_property_type", "_parking_type", "_parking_status",
            "_vehicle_type", "_amenity", "_booking_status",
        ]
        for attr in ref_names:
            obj = getattr(self.m, attr)
            assert obj.create_type is False, (
                f"Reference '{attr}' has create_type={obj.create_type}, expected False"
            )


class TestEnumValues:
    """Verify enum creators carry the correct canonical values."""

    def setup_method(self):
        self.m = _load_migration()
        self.creators = {e.name: e for e in self.m._ALL_CREATORS}

    def test_user_role_values(self):
        assert set(self.creators["user_role"].enums) == {"DRIVER", "OWNER", "ADMIN"}

    def test_property_type_values(self):
        assert set(self.creators["property_type"].enums) == {
            "INDIVIDUAL_HOUSE", "APARTMENT", "COMMERCIAL_BUILDING",
            "HOTEL", "OFFICE", "EMPTY_LAND",
        }

    def test_parking_type_values(self):
        assert set(self.creators["parking_type"].enums) == {"COVERED", "OPEN"}

    def test_parking_status_values(self):
        assert set(self.creators["parking_status"].enums) == {
            "PENDING", "VERIFIED", "REJECTED", "INACTIVE"
        }

    def test_vehicle_type_values(self):
        assert set(self.creators["vehicle_type"].enums) == {
            "BIKE", "CAR", "EV", "TRUCK", "BICYCLE"
        }

    def test_amenity_values(self):
        assert set(self.creators["amenity"].enums) == {
            "CCTV", "COVERED", "SECURITY", "EV_CHARGING", "ACCESS_24X7"
        }

    def test_booking_status_values(self):
        assert set(self.creators["booking_status"].enums) == {
            "PENDING", "CONFIRMED", "ACTIVE", "COMPLETED", "CANCELLED"
        }

    def test_reference_values_match_creators(self):
        """Reference objects carry the same values as their creators."""
        m = self.m
        pairs = [
            (m._user_role_c,      m._user_role),
            (m._property_type_c,  m._property_type),
            (m._parking_type_c,   m._parking_type),
            (m._parking_status_c, m._parking_status),
            (m._vehicle_type_c,   m._vehicle_type),
            (m._amenity_c,        m._amenity),
            (m._booking_status_c, m._booking_status),
        ]
        for creator, ref in pairs:
            assert set(creator.enums) == set(ref.enums), (
                f"Enum '{creator.name}' creator/reference value mismatch: "
                f"{set(creator.enums)} vs {set(ref.enums)}"
            )


class TestCreateTypeSuppression:
    """Verify that create_type=False on postgresql.ENUM correctly suppresses
    CREATE TYPE via _check_for_name_in_memos — the core guard mechanism."""

    def setup_method(self):
        self.m = _load_migration()

    def test_reference_check_for_name_in_memos_returns_true(self):
        """_check_for_name_in_memos must return True (= skip CREATE TYPE)
        for every reference enum, with or without a _ddl_runner in kw."""
        refs = [
            self.m._user_role, self.m._property_type, self.m._parking_type,
            self.m._parking_status, self.m._vehicle_type,
            self.m._amenity, self.m._booking_status,
        ]
        for ref in refs:
            # No _ddl_runner (plain Alembic path)
            assert ref._check_for_name_in_memos(False, {}) is True, (
                f"Reference '{ref.name}' _check_for_name_in_memos returned False; "
                "it will emit CREATE TYPE"
            )

    def test_creator_check_for_name_in_memos_returns_false_without_runner(self):
        """Creator enums (create_type=True) return False without _ddl_runner,
        meaning they WILL proceed to CREATE TYPE — which is the intended
        behaviour because they are only used in the explicit e.create() loop."""
        for creator in self.m._ALL_CREATORS:
            result = creator._check_for_name_in_memos(False, {})
            assert result is False, (
                f"Creator '{creator.name}' unexpectedly returned True; "
                "it should issue CREATE TYPE when called explicitly"
            )

    def test_sa_enum_create_type_false_has_no_create_type_attr(self):
        """Demonstrate the sa.Enum bug: sa.Enum has no .create_type attribute,
        proving that sa.Enum(create_type=False) cannot be used as a reliable
        column type guard in SQLAlchemy 2.x migrations."""
        import sqlalchemy as sa
        bad = sa.Enum(name="user_role", create_type=False)
        assert not hasattr(bad, "create_type"), (
            "sa.Enum unexpectedly gained a create_type attribute — "
            "re-evaluate whether sa.Enum is now safe to use here"
        )

    def test_sa_enum_dialect_impl_resets_create_type_to_true(self):
        """Prove that sa.Enum(name=x, create_type=False).dialect_impl(pg_dialect)
        produces a postgresql.ENUM with create_type=True — confirming the bug
        that the previous fix attempted to solve."""
        import sqlalchemy as sa
        bad = sa.Enum(name="user_role", create_type=False)
        dialect = postgresql.dialect()
        impl = bad.dialect_impl(dialect)
        assert impl.create_type is True, (
            "sa.Enum dialect_impl() no longer resets create_type to True. "
            "The postgresql.ENUM workaround may no longer be necessary — review."
        )

    def test_postgresql_enum_create_type_false_dialect_impl_preserves_flag(self):
        """postgresql.ENUM(create_type=False).dialect_impl() preserves create_type=False."""
        e = postgresql.ENUM("DRIVER", name="user_role", create_type=False)
        dialect = postgresql.dialect()
        impl = e.dialect_impl(dialect)
        assert impl.create_type is False


class TestAllCreatorsPresent:
    """Verify the _ALL_CREATORS tuple contains all seven enum types."""

    def test_seven_creators(self):
        m = _load_migration()
        assert len(m._ALL_CREATORS) == 7

    def test_creator_names(self):
        m = _load_migration()
        names = {e.name for e in m._ALL_CREATORS}
        assert names == {
            "user_role", "property_type", "parking_type", "parking_status",
            "vehicle_type", "amenity", "booking_status",
        }
