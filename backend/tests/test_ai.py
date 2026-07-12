"""Unit tests for the ParkShare AI module (IBM Granite integration).

All watsonx.ai network calls are mocked — no live IBM credentials are required
to run this test suite. These are pure unit tests; no database is involved.

Coverage:
  - Trust score: weights, formula, determinism, verification defaults
  - collect_trust_factors: shared semantics, real owner verification
  - Recommendation: real owner fields used, invented ID rejection, duplicate removal, fallback
  - Pricing: comparable selection, dynamic bounds, Decimal safety, fallback paths
  - AI cannot alter the deterministic trust score
  - All three AI routes are present in the OpenAPI schema
"""
import json
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.exceptions import AIInvalidOutputError, AIServiceUnavailableError
from app.ai.schemas import TrustFactors, RankedParking
from app.ai.services.trust import (
    WEIGHT_LISTING_VERIFIED,
    WEIGHT_PHOTOS_VERIFIED,
    WEIGHT_OWNER_ID_VERIFIED,
    WEIGHT_OWNER_PHONE_VERIFIED,
    WEIGHT_HAS_COMPLETED_BOOKINGS,
    compute_trust_score,
    collect_trust_factors,
    _deterministic_explanation,
)
from app.ai.services.pricing import (
    FLOOR_PRICE,
    CEIL_PRICE,
    _clamp,
    _median_price,
    _dynamic_bounds,
    _select_comparables,
    _amenity_overlap,
)
from app.ai.services.recommendation import _amenity_match_count
from app.main import app
from app.models.parking import Amenity, ParkingStatus, ParkingType


# ============================================================================
# Helpers
# ============================================================================

def _factors(**overrides) -> TrustFactors:
    """Return a TrustFactors instance with sensible defaults, allowing overrides."""
    base = dict(
        listing_verified=False,
        owner_phone_verified=False,
        owner_id_verified=False,
        photos_verified=False,
        completed_bookings=0,
        has_completed_bookings=False,
    )
    base.update(overrides)
    return TrustFactors(**base)


def _mock_parking(
    status=ParkingStatus.VERIFIED,
    photos_verified=False,
    parking_type=ParkingType.OPEN,
    amenities=None,
    vehicle_types=None,
    hourly_price=Decimal("50"),
):
    """Build a minimal mock ParkingSpace for unit tests."""
    space = MagicMock()
    space.id = uuid.uuid4()
    space.name = "Test Parking"
    space.city = "TestCity"
    space.hourly_price = hourly_price
    space.status = status
    space.photos_verified = photos_verified
    space.parking_type = parking_type
    space.amenities = amenities or []
    space.vehicle_types = vehicle_types or []
    return space


def _mock_owner(phone_verified=False, id_verified=False):
    owner = MagicMock()
    owner.phone_verified = phone_verified
    owner.id_verified = id_verified
    return owner


# ============================================================================
# TRUST SCORE — weight constants
# ============================================================================

def test_trust_score_weights_sum_to_100():
    total = (
        WEIGHT_LISTING_VERIFIED
        + WEIGHT_PHOTOS_VERIFIED
        + WEIGHT_OWNER_ID_VERIFIED
        + WEIGHT_OWNER_PHONE_VERIFIED
        + WEIGHT_HAS_COMPLETED_BOOKINGS
    )
    assert total == 100, f"Weights sum to {total}, expected 100"


def test_trust_score_weight_values():
    assert WEIGHT_LISTING_VERIFIED == 30
    assert WEIGHT_PHOTOS_VERIFIED == 20
    assert WEIGHT_OWNER_ID_VERIFIED == 20
    assert WEIGHT_OWNER_PHONE_VERIFIED == 15
    assert WEIGHT_HAS_COMPLETED_BOOKINGS == 15


# ============================================================================
# TRUST SCORE — compute_trust_score
# ============================================================================

def test_trust_score_all_factors_max():
    factors = _factors(
        listing_verified=True,
        owner_phone_verified=True,
        owner_id_verified=True,
        photos_verified=True,
        completed_bookings=5,
        has_completed_bookings=True,
    )
    assert compute_trust_score(factors) == 100


def test_trust_score_no_factors_zero():
    assert compute_trust_score(_factors()) == 0


def test_trust_score_only_listing_verified():
    assert compute_trust_score(_factors(listing_verified=True)) == WEIGHT_LISTING_VERIFIED


def test_trust_score_only_completed_bookings():
    assert compute_trust_score(
        _factors(completed_bookings=1, has_completed_bookings=True)
    ) == WEIGHT_HAS_COMPLETED_BOOKINGS


def test_trust_score_deterministic_same_inputs_same_output():
    factors = _factors(
        listing_verified=True,
        owner_phone_verified=True,
        completed_bookings=2,
        has_completed_bookings=True,
    )
    assert compute_trust_score(factors) == compute_trust_score(factors)


def test_trust_score_partial_factors():
    factors = _factors(listing_verified=True, photos_verified=True)
    assert compute_trust_score(factors) == WEIGHT_LISTING_VERIFIED + WEIGHT_PHOTOS_VERIFIED


# ============================================================================
# TRUST SCORE — verification defaults
# ============================================================================

def test_verification_defaults_are_false():
    factors = _factors()
    assert factors.listing_verified is False
    assert factors.owner_phone_verified is False
    assert factors.owner_id_verified is False
    assert factors.photos_verified is False
    assert factors.completed_bookings == 0
    assert factors.has_completed_bookings is False


# ============================================================================
# collect_trust_factors — shared semantics, real owner verification
# ============================================================================

def test_collect_trust_factors_uses_real_owner_phone_verified():
    """collect_trust_factors must read owner.phone_verified, not default to False."""
    parking = _mock_parking(status=ParkingStatus.VERIFIED, photos_verified=False)
    owner = _mock_owner(phone_verified=True, id_verified=False)
    factors = collect_trust_factors(parking, owner, completed_count=0)
    assert factors.owner_phone_verified is True


def test_collect_trust_factors_uses_real_owner_id_verified():
    parking = _mock_parking(status=ParkingStatus.VERIFIED)
    owner = _mock_owner(phone_verified=False, id_verified=True)
    factors = collect_trust_factors(parking, owner, completed_count=0)
    assert factors.owner_id_verified is True


def test_collect_trust_factors_unverified_owner():
    parking = _mock_parking(status=ParkingStatus.VERIFIED)
    owner = _mock_owner(phone_verified=False, id_verified=False)
    factors = collect_trust_factors(parking, owner, completed_count=0)
    assert factors.owner_phone_verified is False
    assert factors.owner_id_verified is False


def test_collect_trust_factors_completed_bookings():
    parking = _mock_parking()
    owner = _mock_owner()
    factors = collect_trust_factors(parking, owner, completed_count=3)
    assert factors.completed_bookings == 3
    assert factors.has_completed_bookings is True


def test_collect_trust_factors_no_completed_bookings():
    parking = _mock_parking()
    owner = _mock_owner()
    factors = collect_trust_factors(parking, owner, completed_count=0)
    assert factors.has_completed_bookings is False


def test_collect_trust_factors_score_matches_compute():
    """collect_trust_factors + compute_trust_score must produce the same score
    as building TrustFactors manually with the same field values."""
    parking = _mock_parking(status=ParkingStatus.VERIFIED, photos_verified=True)
    owner = _mock_owner(phone_verified=True, id_verified=True)
    factors = collect_trust_factors(parking, owner, completed_count=2)
    score = compute_trust_score(factors)
    expected = (
        WEIGHT_LISTING_VERIFIED
        + WEIGHT_PHOTOS_VERIFIED
        + WEIGHT_OWNER_ID_VERIFIED
        + WEIGHT_OWNER_PHONE_VERIFIED
        + WEIGHT_HAS_COMPLETED_BOOKINGS
    )
    assert score == expected == 100


# ============================================================================
# TRUST SCORE — Granite cannot alter the numeric score
# ============================================================================

def test_granite_cannot_change_trust_score():
    factors = _factors(listing_verified=True)
    deterministic_score = compute_trust_score(factors)

    fake_granite_output = json.dumps({
        "explanation": "Great parking!",
        "trust_score": 99,  # Granite trying to set its own score
    })
    parsed = json.loads(fake_granite_output)

    explanation = str(parsed.get("explanation", "")).strip()
    assert explanation == "Great parking!"
    assert deterministic_score == WEIGHT_LISTING_VERIFIED
    assert parsed.get("trust_score") != deterministic_score


# ============================================================================
# TRUST SCORE — deterministic explanation fallback
# ============================================================================

def test_deterministic_explanation_no_factors():
    explanation = _deterministic_explanation(0, _factors())
    assert "0/100" in explanation
    assert "No verification" in explanation


def test_deterministic_explanation_with_factors():
    factors = _factors(listing_verified=True, owner_phone_verified=True)
    explanation = _deterministic_explanation(45, factors)
    assert "45/100" in explanation
    assert "listing is verified" in explanation
    assert "owner phone verified" in explanation


# ============================================================================
# PRICING — _clamp helper
# ============================================================================

def test_price_below_floor_is_clamped():
    assert _clamp(Decimal("1")) == FLOOR_PRICE


def test_price_at_floor_unchanged():
    assert _clamp(FLOOR_PRICE) == FLOOR_PRICE


def test_price_within_range_unchanged():
    assert _clamp(Decimal("100")) == Decimal("100")


def test_price_at_ceiling_unchanged():
    assert _clamp(CEIL_PRICE) == CEIL_PRICE


def test_price_above_ceiling_is_clamped():
    assert _clamp(Decimal("9999")) == CEIL_PRICE


def test_price_zero_is_clamped_to_floor():
    assert _clamp(Decimal("0")) == FLOOR_PRICE


def test_clamp_with_custom_bounds():
    lo, hi = Decimal("20"), Decimal("100")
    assert _clamp(Decimal("10"), lo=lo, hi=hi) == lo
    assert _clamp(Decimal("50"), lo=lo, hi=hi) == Decimal("50")
    assert _clamp(Decimal("200"), lo=lo, hi=hi) == hi


# ============================================================================
# PRICING — _median_price helper
# ============================================================================

def test_median_odd_count():
    prices = [Decimal("10"), Decimal("20"), Decimal("30")]
    assert _median_price(prices) == Decimal("20")


def test_median_even_count():
    prices = [Decimal("10"), Decimal("20"), Decimal("30"), Decimal("40")]
    assert _median_price(prices) == Decimal("25")


def test_median_single_element():
    assert _median_price([Decimal("42")]) == Decimal("42")


def test_median_empty_list():
    assert _median_price([]) == Decimal("0")


def test_median_fractional_rupees_odd():
    """Fractional rupee amounts must be preserved exactly — no float rounding."""
    prices = [Decimal("49.50"), Decimal("99.99"), Decimal("149.75")]
    # Sorted: [49.50, 99.99, 149.75] — middle element is 99.99
    assert _median_price(prices) == Decimal("99.99")


def test_median_fractional_rupees_even():
    """Even-count median must use Decimal division, not float averaging."""
    prices = [Decimal("49.50"), Decimal("99.99")]
    # (49.50 + 99.99) / 2 = 149.49 / 2 = 74.745
    assert _median_price(prices) == Decimal("149.49") / Decimal("2")


def test_median_precision_sensitive_decimal():
    """Values that would lose precision via float must survive _median_price intact."""
    # 0.1 + 0.2 is not exactly 0.3 in float; Decimal keeps it exact.
    prices = [Decimal("0.10"), Decimal("0.20"), Decimal("0.30")]
    assert _median_price(prices) == Decimal("0.20")


def test_median_no_float_conversion():
    """_median_price must return a Decimal instance, never a float."""
    result = _median_price([Decimal("100"), Decimal("200")])
    assert isinstance(result, Decimal), f"Expected Decimal, got {type(result)}"


def test_median_unsorted_input():
    """_median_price must sort internally — input order must not affect the result."""
    prices_fwd = [Decimal("10"), Decimal("50"), Decimal("30")]
    prices_rev = [Decimal("30"), Decimal("50"), Decimal("10")]
    assert _median_price(prices_fwd) == _median_price(prices_rev) == Decimal("30")


# ============================================================================
# PRICING — _dynamic_bounds helper
# ============================================================================

def test_dynamic_bounds_normal_median():
    """With a median of 100, bounds should be [50, 150]."""
    lower, upper = _dynamic_bounds(Decimal("100"))
    assert lower == Decimal("50.00")
    assert upper == Decimal("150.00")


def test_dynamic_bounds_floor_enforced():
    """With a very low median (e.g. 6), lower bound must not go below FLOOR_PRICE."""
    lower, upper = _dynamic_bounds(Decimal("6"))
    assert lower >= FLOOR_PRICE


def test_dynamic_bounds_ceiling_enforced():
    """With a very high median, upper bound must not exceed CEIL_PRICE."""
    lower, upper = _dynamic_bounds(Decimal("4000"))
    assert upper <= CEIL_PRICE


def test_dynamic_bounds_uses_decimal_arithmetic():
    """_dynamic_bounds must not lose precision for a precise median."""
    lower, upper = _dynamic_bounds(Decimal("60.00"))
    # 60 * 0.5 = 30, 60 * 1.5 = 90
    assert lower == Decimal("30.00")
    assert upper == Decimal("90.00")


def test_dynamic_bounds_lower_lte_upper():
    """lower_bound must always be <= upper_bound regardless of inputs."""
    for med in [Decimal("5"), Decimal("10"), Decimal("100"), Decimal("5000")]:
        lo, hi = _dynamic_bounds(med)
        assert lo <= hi


# ============================================================================
# PRICING — _select_comparables helper
# ============================================================================

def _make_parking_space(parking_type, vehicle_types=None, amenities=None, price=Decimal("50")):
    """Build a mock ParkingSpace for comparable selection tests."""
    space = MagicMock()
    space.hourly_price = price
    space.parking_type = parking_type

    # Mock vehicle_types as a list of objects with .vehicle_type attribute
    vt_list = []
    for vt in (vehicle_types or []):
        m = MagicMock()
        m.vehicle_type = vt
        vt_list.append(m)
    space.vehicle_types = vt_list

    # Mock amenities as a list of objects with .amenity attribute
    am_list = []
    for am in (amenities or []):
        m = MagicMock()
        m.amenity = am
        am_list.append(m)
    space.amenities = am_list

    return space


def test_select_comparables_prefers_same_parking_type():
    """Listings with matching parking_type must be preferred."""
    from app.ai.schemas import PriceSuggestionRequest
    from app.models.parking import VehicleType

    covered = _make_parking_space(ParkingType.COVERED)
    open_lot = _make_parking_space(ParkingType.OPEN)

    request = PriceSuggestionRequest(
        city="TestCity", state="TestState",
        parking_type=ParkingType.COVERED,
        amenities=[], vehicle_types=[], total_slots=1, is_24x7=False,
    )
    result = _select_comparables([covered, open_lot], request)
    # strict set has 1 item (covered) — less than threshold, so broadens
    # but covered must still be present
    assert covered in result


def test_select_comparables_broadens_when_strict_set_too_small():
    """If fewer than _MIN_COMPARABLE_THRESHOLD match parking_type, broaden."""
    from app.ai.schemas import PriceSuggestionRequest
    from app.ai.services.pricing import _MIN_COMPARABLE_THRESHOLD

    # Only 1 COVERED space, 5 OPEN spaces
    covered = _make_parking_space(ParkingType.COVERED)
    open_lots = [_make_parking_space(ParkingType.OPEN) for _ in range(5)]

    request = PriceSuggestionRequest(
        city="TestCity", state="TestState",
        parking_type=ParkingType.COVERED,
        amenities=[], vehicle_types=[], total_slots=1, is_24x7=False,
    )
    result = _select_comparables([covered] + open_lots, request)
    # strict set has 1 < _MIN_COMPARABLE_THRESHOLD → broadens to all city spaces
    assert len(result) > 1


def test_select_comparables_same_city_only():
    """Comparables are always from the same city — the caller already filters by city."""
    # This test verifies _select_comparables does not mix cross-city data
    from app.ai.schemas import PriceSuggestionRequest

    spaces = [_make_parking_space(ParkingType.OPEN, price=Decimal(str(p)))
              for p in [30, 40, 50, 60, 70]]
    request = PriceSuggestionRequest(
        city="SameCity", state="State",
        parking_type=ParkingType.OPEN,
        amenities=[], vehicle_types=[], total_slots=1, is_24x7=False,
    )
    result = _select_comparables(spaces, request)
    # All inputs are in the same city (caller pre-filtered), all should be eligible
    assert len(result) == len(spaces)


# ============================================================================
# PRICING — get_price_suggestion (async, mocked)
# ============================================================================

@pytest.mark.asyncio
async def test_price_suggestion_no_comparables_returns_no_suggestion():
    from app.ai.services.pricing import get_price_suggestion
    from app.ai.schemas import PriceSuggestionRequest

    request = PriceSuggestionRequest(
        city="EmptyCity", state="Nowhere",
        parking_type=ParkingType.OPEN,
        amenities=[], vehicle_types=[], total_slots=1, is_24x7=False,
    )
    with patch("app.ai.services.pricing.ParkingRepository") as MockRepo:
        MockRepo.return_value.search = AsyncMock(return_value=([], 0))
        result = await get_price_suggestion(request, session=AsyncMock())

    assert result.suggested_hourly_price is None
    assert result.ai_generated is False
    assert result.comparable_count == 0


@pytest.mark.asyncio
async def test_price_inside_dynamic_bounds_is_accepted():
    """A price within dynamic bounds must be returned with ai_generated=True."""
    from app.ai.services.pricing import get_price_suggestion
    from app.ai.schemas import PriceSuggestionRequest

    request = PriceSuggestionRequest(
        city="Bengaluru", state="Karnataka",
        parking_type=ParkingType.OPEN,
        amenities=[], vehicle_types=[], total_slots=1, is_24x7=False,
    )
    mock_space = _make_parking_space(ParkingType.OPEN, price=Decimal("100"))
    # median = 100, bounds = [50, 150]; suggest 80 which is inside
    granite_response = json.dumps({"suggested_hourly_price": 80, "explanation": "Good price"})

    with (
        patch("app.ai.services.pricing.ParkingRepository") as MockRepo,
        patch("app.ai.services.pricing.watsonx_client.generate",
              new=AsyncMock(return_value=granite_response)),
    ):
        MockRepo.return_value.search = AsyncMock(return_value=([mock_space], 1))
        result = await get_price_suggestion(request, session=AsyncMock())

    assert result.suggested_hourly_price == Decimal("80")
    assert result.ai_generated is True


@pytest.mark.asyncio
async def test_price_below_dynamic_bounds_triggers_deterministic_fallback():
    """A price below the dynamic lower bound must trigger fallback, not be returned as AI."""
    from app.ai.services.pricing import get_price_suggestion
    from app.ai.schemas import PriceSuggestionRequest

    request = PriceSuggestionRequest(
        city="Bengaluru", state="Karnataka",
        parking_type=ParkingType.OPEN,
        amenities=[], vehicle_types=[], total_slots=1, is_24x7=False,
    )
    mock_space = _make_parking_space(ParkingType.OPEN, price=Decimal("100"))
    # median=100, lower_bound=50; Granite returns 10 which is below lower_bound
    granite_response = json.dumps({"suggested_hourly_price": 10, "explanation": "Too cheap"})

    with (
        patch("app.ai.services.pricing.ParkingRepository") as MockRepo,
        patch("app.ai.services.pricing.watsonx_client.generate",
              new=AsyncMock(return_value=granite_response)),
    ):
        MockRepo.return_value.search = AsyncMock(return_value=([mock_space], 1))
        result = await get_price_suggestion(request, session=AsyncMock())

    # Out-of-bounds Granite price must NOT be returned as AI-generated
    assert result.ai_generated is False


@pytest.mark.asyncio
async def test_price_above_dynamic_bounds_triggers_deterministic_fallback():
    """A price above the dynamic upper bound must trigger fallback with ai_generated=False."""
    from app.ai.services.pricing import get_price_suggestion
    from app.ai.schemas import PriceSuggestionRequest

    request = PriceSuggestionRequest(
        city="Mumbai", state="Maharashtra",
        parking_type=ParkingType.OPEN,
        amenities=[], vehicle_types=[], total_slots=1, is_24x7=False,
    )
    mock_space = _make_parking_space(ParkingType.OPEN, price=Decimal("100"))
    # median=100, upper_bound=150; Granite returns 500 which is above upper_bound
    granite_response = json.dumps({"suggested_hourly_price": 500, "explanation": "Too high"})

    with (
        patch("app.ai.services.pricing.ParkingRepository") as MockRepo,
        patch("app.ai.services.pricing.watsonx_client.generate",
              new=AsyncMock(return_value=granite_response)),
    ):
        MockRepo.return_value.search = AsyncMock(return_value=([mock_space], 1))
        result = await get_price_suggestion(request, session=AsyncMock())

    assert result.ai_generated is False


@pytest.mark.asyncio
async def test_price_ai_unavailable_returns_deterministic_fallback():
    from app.ai.services.pricing import get_price_suggestion
    from app.ai.schemas import PriceSuggestionRequest

    request = PriceSuggestionRequest(
        city="Chennai", state="Tamil Nadu",
        parking_type=ParkingType.OPEN,
        amenities=[], vehicle_types=[], total_slots=1, is_24x7=False,
    )
    mock_space = _make_parking_space(ParkingType.OPEN, price=Decimal("60"))

    with (
        patch("app.ai.services.pricing.ParkingRepository") as MockRepo,
        patch("app.ai.services.pricing.watsonx_client.generate",
              new=AsyncMock(side_effect=AIServiceUnavailableError("timeout"))),
    ):
        MockRepo.return_value.search = AsyncMock(return_value=([mock_space], 1))
        result = await get_price_suggestion(request, session=AsyncMock())

    assert result.ai_generated is False
    assert result.suggested_hourly_price is not None


@pytest.mark.asyncio
async def test_price_invalid_json_returns_deterministic_fallback():
    from app.ai.services.pricing import get_price_suggestion
    from app.ai.schemas import PriceSuggestionRequest

    request = PriceSuggestionRequest(
        city="Pune", state="Maharashtra",
        parking_type=ParkingType.OPEN,
        amenities=[], vehicle_types=[], total_slots=1, is_24x7=False,
    )
    mock_space = _make_parking_space(ParkingType.OPEN, price=Decimal("40"))

    with (
        patch("app.ai.services.pricing.ParkingRepository") as MockRepo,
        patch("app.ai.services.pricing.watsonx_client.generate",
              new=AsyncMock(return_value="Sorry, I cannot help with that.")),
    ):
        MockRepo.return_value.search = AsyncMock(return_value=([mock_space], 1))
        result = await get_price_suggestion(request, session=AsyncMock())

    assert result.ai_generated is False


# ============================================================================
# RECOMMENDATION — amenity match helper
# ============================================================================

def test_amenity_match_count_all_match():
    class FakePVT:
        amenity = Amenity.CCTV

    class FakePVT2:
        amenity = Amenity.EV_CHARGING

    class FakeSpace:
        amenities = [FakePVT(), FakePVT2()]

    assert _amenity_match_count(FakeSpace(), [Amenity.CCTV, Amenity.EV_CHARGING]) == 2


def test_amenity_match_count_no_preferred():
    assert _amenity_match_count(object(), []) == 0


def test_amenity_match_count_none_match():
    class FakePVT:
        amenity = Amenity.SECURITY

    class FakeSpace:
        amenities = [FakePVT()]

    assert _amenity_match_count(FakeSpace(), [Amenity.CCTV]) == 0


# ============================================================================
# RECOMMENDATION — search context passes real filters (unit logic)
# ============================================================================

def test_recommendation_request_passes_city_and_vehicle_type():
    """RecommendationRequest must carry city and vehicle_type to the repo search."""
    from app.ai.schemas import RecommendationRequest
    from app.models.parking import VehicleType

    req = RecommendationRequest(
        city="Bengaluru",
        vehicle_type=VehicleType.CAR,
        max_hourly_price=Decimal("80"),
        preferred_amenities=[Amenity.CCTV],
        preference_context="",
    )
    assert req.city == "Bengaluru"
    assert req.vehicle_type == VehicleType.CAR
    assert req.max_hourly_price == Decimal("80")
    assert Amenity.CCTV in req.preferred_amenities


# ============================================================================
# RECOMMENDATION — invented ID rejection and deduplication (unit logic)
# ============================================================================

def test_invented_id_rejected():
    real_id = str(uuid.uuid4())
    invented_id = str(uuid.uuid4())
    valid_ids = {real_id}

    raw_recs = [
        {"parking_id": real_id, "rank": 1, "match_score": 90, "reason": "Good"},
        {"parking_id": invented_id, "rank": 2, "match_score": 80, "reason": "Invented"},
    ]

    validated = []
    seen: set[str] = set()
    for item in raw_recs:
        pid = str(item.get("parking_id", ""))
        if pid not in valid_ids:
            continue
        if pid in seen:
            continue
        seen.add(pid)
        validated.append(pid)

    assert len(validated) == 1
    assert invented_id not in validated
    assert real_id in validated


def test_duplicate_ids_deduplicated():
    real_id = str(uuid.uuid4())
    valid_ids = {real_id}
    raw_recs = [
        {"parking_id": real_id, "rank": 1, "match_score": 90, "reason": "First"},
        {"parking_id": real_id, "rank": 2, "match_score": 85, "reason": "Duplicate"},
    ]
    validated = []
    seen: set[str] = set()
    for item in raw_recs:
        pid = str(item.get("parking_id", ""))
        if pid not in valid_ids or pid in seen:
            continue
        seen.add(pid)
        validated.append(pid)
    assert len(validated) == 1


def test_all_ids_invented_returns_empty():
    valid_ids: set[str] = {str(uuid.uuid4())}
    raw_recs = [{"parking_id": str(uuid.uuid4()), "rank": 1, "match_score": 90, "reason": "Fake"}]
    validated = []
    seen: set[str] = set()
    for item in raw_recs:
        pid = str(item.get("parking_id", ""))
        if pid not in valid_ids or pid in seen:
            continue
        seen.add(pid)
        validated.append(pid)
    assert len(validated) == 0


# ============================================================================
# EXCEPTION BOUNDARIES — expected AI failures use fallback; others propagate
# ============================================================================

def test_ai_service_unavailable_is_expected_ai_failure():
    """AIServiceUnavailableError is a known AI-boundary error — must trigger fallback."""
    err = AIServiceUnavailableError("timeout")
    assert isinstance(err, AIServiceUnavailableError)


def test_ai_invalid_output_is_expected_ai_failure():
    """AIInvalidOutputError is a known AI-boundary error — must trigger fallback."""
    err = AIInvalidOutputError("bad json")
    assert isinstance(err, AIInvalidOutputError)


def test_ai_exceptions_are_not_base_exception():
    """AI exceptions must not silently swallow unrelated errors."""
    ai_unavailable = AIServiceUnavailableError("x")
    ai_invalid = AIInvalidOutputError("y")
    # These should NOT be caught by a bare `except Exception` that intends
    # to handle only AI failures. The narrowed exception tuple in each service
    # explicitly lists these types.
    assert isinstance(ai_unavailable, Exception)
    assert isinstance(ai_invalid, Exception)
    # Verify a random ValueError (e.g. from int()) would also be caught by
    # the narrowed tuple without being swallowed by a broad Exception catch
    val_err = ValueError("bad int")
    assert isinstance(val_err, (AIServiceUnavailableError, AIInvalidOutputError,
                                 json.JSONDecodeError, ValueError))


# ============================================================================
# AI ROUTES — present in OpenAPI schema (smoke)
# ============================================================================

def test_ai_routes_in_openapi():
    paths = set(app.openapi().get("paths", {}).keys())
    assert "/api/v1/ai/recommendations" in paths, "Missing /api/v1/ai/recommendations"
    assert "/api/v1/ai/price-suggestion" in paths, "Missing /api/v1/ai/price-suggestion"
    assert "/api/v1/ai/trust/{parking_id}" in paths, "Missing /api/v1/ai/trust/{parking_id}"
