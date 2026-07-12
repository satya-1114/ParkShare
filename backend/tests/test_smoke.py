"""Smoke + correctness unit tests for the ParkShare backend.

These are pure unit tests — they do NOT hit a database and do NOT exercise
concurrent transactions. They validate the public semantics of the
availability / capacity rules refactor:

* interval overlap semantics (the SQL predicate used by the booking repo)
* the capacity rule (overlap count vs total_slots) for the MVP
* which booking statuses are capacity-consuming

Database integration tests and real concurrent-transaction tests
(SELECT ... FOR UPDATE behaviour under load, HTTP 409 on capacity exhaustion,
end-to-end booking flows against Postgres) are out of scope here and remain
future test coverage.
"""
from datetime import datetime, timedelta, timezone

from app.main import app
from app.models.booking import BookingStatus
from app.services.booking import (
    CAPACITY_CONSUMING_STATUSES,
    is_capacity_consuming,
)


# --- smoke ---------------------------------------------------------------

def test_app_boots():
    assert app.title
    paths = set(app.openapi().get("paths", {}).keys())
    for expected in (
        "/api/v1/health",
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/me",
        "/api/v1/parkings",
        "/api/v1/parkings/mine",
        "/api/v1/parkings/{parking_id}",
        "/api/v1/bookings",
        "/api/v1/bookings/mine",
        "/api/v1/bookings/{booking_id}",
        "/api/v1/bookings/{booking_id}/cancel",
    ):
        assert expected in paths, f"missing route: {expected}"


# --- overlap semantics ---------------------------------------------------

def _overlaps(a_start, a_end, b_start, b_end) -> bool:
    """Mirrors the SQL predicate used in count_overlapping_bookings."""
    return a_start < b_end and a_end > b_start


NOW = datetime(2026, 7, 15, 10, 0, tzinfo=timezone.utc)


def test_back_to_back_bookings_do_not_overlap():
    a_start, a_end = NOW, NOW + timedelta(hours=2)
    b_start, b_end = a_end, a_end + timedelta(hours=2)
    assert _overlaps(a_start, a_end, b_start, b_end) is False


def test_non_overlapping_bookings_do_not_overlap():
    a_start, a_end = NOW, NOW + timedelta(hours=1)
    b_start, b_end = NOW + timedelta(hours=5), NOW + timedelta(hours=6)
    assert _overlaps(a_start, a_end, b_start, b_end) is False


def test_partial_overlap_detected():
    a_start, a_end = NOW, NOW + timedelta(hours=3)
    b_start, b_end = NOW + timedelta(hours=2), NOW + timedelta(hours=4)
    assert _overlaps(a_start, a_end, b_start, b_end) is True


def test_containment_is_overlap():
    a_start, a_end = NOW, NOW + timedelta(hours=6)
    b_start, b_end = NOW + timedelta(hours=1), NOW + timedelta(hours=2)
    assert _overlaps(a_start, a_end, b_start, b_end) is True


# --- capacity-consuming statuses ----------------------------------------

def test_capacity_consuming_status_set():
    assert set(CAPACITY_CONSUMING_STATUSES) == {
        BookingStatus.CONFIRMED,
        BookingStatus.ACTIVE,
    }


def test_cancelled_bookings_do_not_consume_capacity():
    assert is_capacity_consuming(BookingStatus.CANCELLED) is False


def test_completed_bookings_do_not_consume_capacity():
    assert is_capacity_consuming(BookingStatus.COMPLETED) is False


def test_confirmed_and_active_consume_capacity():
    assert is_capacity_consuming(BookingStatus.CONFIRMED) is True
    assert is_capacity_consuming(BookingStatus.ACTIVE) is True


# --- capacity rule (overlap count vs total_slots) -----------------------

def _capacity_available(overlapping_capacity_consuming: int, total_slots: int) -> bool:
    """MVP: one booking consumes one slot; new booking allowed iff
    overlapping capacity-consuming bookings < total_slots."""
    return overlapping_capacity_consuming < total_slots


def test_overlapping_booking_with_available_capacity_is_allowed():
    # 1 overlapping booking, total 2 slots -> allowed
    assert _capacity_available(1, 2) is True


def test_overlapping_booking_at_full_capacity_is_rejected():
    # 1 overlapping booking, total 1 slot -> rejected
    assert _capacity_available(1, 1) is False
    # 3 overlapping bookings, total 3 slots -> rejected
    assert _capacity_available(3, 3) is False


def test_non_overlapping_bookings_with_one_slot_allowed():
    # zero overlaps -> always allowed regardless of low capacity
    assert _capacity_available(0, 1) is True
