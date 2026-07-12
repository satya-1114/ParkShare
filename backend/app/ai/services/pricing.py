"""Pricing suggestion service.

Comparable selection (PART 3)
-----------------------------
1. Fetch all VERIFIED listings in the same city (up to 40, no extra filters so
   we get a broad pool first).
2. Keep only listings whose parking_type matches the request.
3. Of those, prefer listings that support at least one requested vehicle_type.
4. Rank remaining comparables by amenity overlap with the request.
5. Take the top _MAX_COMPARABLES most relevant.
6. If the strict set (steps 2–5) is too small (< _MIN_COMPARABLE_THRESHOLD),
   broaden back to all city listings — still within the same city.

Dynamic bounds (PART 4)
-----------------------
After selecting comparables, calculate:

    lower_bound = max(FLOOR_PRICE, comparable_median * Decimal("0.5"))
    upper_bound = min(CEIL_PRICE, comparable_median * Decimal("1.5"))

These bounds are passed to the Granite prompt and used to validate the model
output.  If Granite returns a price outside [lower_bound, upper_bound], the
response is treated as invalid and the deterministic median fallback is used
with ai_generated=False.

Exception boundaries (PART 5)
------------------------------
Only AI-boundary failures (AIServiceUnavailableError, AIInvalidOutputError,
json.JSONDecodeError, InvalidOperation, ValueError) trigger the deterministic
fallback.  Database errors and programming mistakes propagate normally.
"""
import json
import logging
from decimal import Decimal, InvalidOperation
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import client as watsonx_client
from app.ai.exceptions import AIInvalidOutputError, AIServiceUnavailableError
from app.ai.logging import log_ai_fallback
from app.ai.prompts import build_pricing_prompt
from app.ai.schemas import PriceSuggestionRequest, PriceSuggestionResponse
from app.core.config import settings
from app.models.parking import ParkingSpace
from app.repositories.parking import ParkingRepository

log = logging.getLogger(__name__)

FLOOR_PRICE = Decimal("5")
CEIL_PRICE = Decimal("5000")
_MAX_COMPARABLES = 15
_MIN_COMPARABLE_THRESHOLD = 3


def _clamp(value: Decimal, lo: Decimal = FLOOR_PRICE, hi: Decimal = CEIL_PRICE) -> Decimal:
    return max(lo, min(hi, value))


def _median_price(prices: list[Decimal]) -> Decimal:
    """Return the median of a list of Decimal prices using only Decimal arithmetic.

    Never converts to float — preserves exact monetary precision.
    """
    if not prices:
        return Decimal("0")
    sorted_prices = sorted(prices)
    n = len(sorted_prices)
    mid = n // 2
    if n % 2 == 1:
        return sorted_prices[mid]
    return (sorted_prices[mid - 1] + sorted_prices[mid]) / Decimal("2")


def _dynamic_bounds(med: Decimal) -> tuple[Decimal, Decimal]:
    """Return (lower_bound, upper_bound) derived from the comparable median.

    Uses only Decimal arithmetic — no float monetary calculations.
    """
    lower = _clamp(
        (med * Decimal("0.5")).quantize(Decimal("0.01")),
        lo=FLOOR_PRICE, hi=CEIL_PRICE,
    )
    upper = _clamp(
        (med * Decimal("1.5")).quantize(Decimal("0.01")),
        lo=FLOOR_PRICE, hi=CEIL_PRICE,
    )
    # Ensure lower <= upper in degenerate cases (e.g. very low median)
    if lower > upper:
        lower, upper = upper, lower
    return lower, upper


def _amenity_overlap(space: ParkingSpace, request_amenities: list) -> int:
    """Count how many request amenities the space supports."""
    if not request_amenities:
        return 0
    space_set = {a.amenity for a in space.amenities}
    return sum(1 for a in request_amenities if a in space_set)


def _select_comparables(
    all_city_spaces: list[ParkingSpace],
    request: PriceSuggestionRequest,
) -> list[ParkingSpace]:
    """Choose the most relevant comparables from the city pool.

    Strategy (deterministic, backend-controlled):
    1. Same parking_type — strict filter.
    2. Of those, prefer spaces supporting at least one requested vehicle_type.
    3. Rank by amenity overlap descending.
    4. Take top _MAX_COMPARABLES.
    5. If strict set < _MIN_COMPARABLE_THRESHOLD, broaden back to all city spaces.
    """
    requested_vehicles = set(request.vehicle_types)

    def _vehicle_match(space: ParkingSpace) -> bool:
        if not requested_vehicles:
            return True
        space_vehicles = {pvt.vehicle_type for pvt in space.vehicle_types}
        return bool(space_vehicles & requested_vehicles)

    # Step 1: filter by parking type
    type_matched = [s for s in all_city_spaces if s.parking_type == request.parking_type]

    # Step 2+3: prefer vehicle match, rank by amenity overlap
    def _sort_key(s: ParkingSpace) -> tuple[int, int]:
        return (
            0 if _vehicle_match(s) else 1,           # vehicle-matched first
            -_amenity_overlap(s, request.amenities),  # more overlap first
        )

    type_matched.sort(key=_sort_key)
    strict = type_matched[:_MAX_COMPARABLES]

    if len(strict) >= _MIN_COMPARABLE_THRESHOLD:
        return strict

    # Step 5: broaden — fall back to all city spaces when strict set is too small
    log.debug(
        "Pricing comparable strict set has %d items (< %d); broadening to all city listings",
        len(strict), _MIN_COMPARABLE_THRESHOLD,
    )
    all_city_spaces.sort(key=_sort_key)
    return all_city_spaces[:_MAX_COMPARABLES]


async def get_price_suggestion(
    request: PriceSuggestionRequest,
    session: AsyncSession,
) -> PriceSuggestionResponse:
    repo = ParkingRepository(session)
    # Fetch a broad city pool (no extra filters) and select comparables in Python.
    all_city_spaces, _ = await repo.search(city=request.city, page=1, page_size=40)

    if not all_city_spaces:
        return PriceSuggestionResponse(
            suggested_hourly_price=None,
            price_range=None,
            explanation=(
                f"No comparable listings found in {request.city}. "
                "Set a price based on your expected demand."
            ),
            comparable_count=0,
            ai_generated=False,
            model_id=None,
        )

    comparables = _select_comparables(all_city_spaces, request)
    prices = [space.hourly_price for space in comparables]
    min_price = min(prices)
    max_price = max(prices)
    med_price = _median_price(prices)
    price_range: dict[str, Decimal] = {
        "min": Decimal(str(min_price)),
        "max": Decimal(str(max_price)),
        "median": med_price,
    }

    lower_bound, upper_bound = _dynamic_bounds(med_price)

    # Only AI-boundary failures trigger the fallback; DB/programming errors propagate.
    try:
        prompt = build_pricing_prompt(
            request,
            min_price=Decimal(str(min_price)),
            max_price=Decimal(str(max_price)),
            median_price=med_price,
            comparable_count=len(comparables),
            lower_bound=lower_bound,
            upper_bound=upper_bound,
        )
        raw = await watsonx_client.generate(prompt)
        parsed = json.loads(raw)

        raw_price = parsed.get("suggested_hourly_price")
        if raw_price is None:
            raise AIInvalidOutputError("suggested_hourly_price missing from response")

        model_price = Decimal(str(raw_price))

        # Validate against dynamic bounds — out-of-range means Granite ignored
        # the constraint, so fall back to deterministic rather than silently clamp.
        if model_price < lower_bound or model_price > upper_bound:
            log.debug(
                "Granite price %s outside dynamic bounds [%s, %s]; using deterministic fallback",
                model_price, lower_bound, upper_bound,
            )
            raise AIInvalidOutputError(
                f"Suggested price {model_price} is outside allowed range "
                f"[{lower_bound}, {upper_bound}]"
            )

        explanation = str(parsed.get("explanation", "")).strip()
        if not explanation:
            explanation = (
                f"Suggested ₹{model_price}/hr based on {len(comparables)} comparable "
                f"listings in {request.city} (range: ₹{min_price}–₹{max_price})."
            )

        return PriceSuggestionResponse(
            suggested_hourly_price=model_price,
            price_range=price_range,
            explanation=explanation[:300],
            comparable_count=len(comparables),
            ai_generated=True,
            model_id=settings.WATSONX_MODEL_ID,
        )

    except (AIServiceUnavailableError, AIInvalidOutputError, json.JSONDecodeError, InvalidOperation, ValueError) as exc:
        log_ai_fallback(log, "price-suggestion", exc)
        fallback_price = _clamp(med_price)
        return PriceSuggestionResponse(
            suggested_hourly_price=fallback_price,
            price_range=price_range,
            explanation=(
                f"Based on {len(comparables)} comparable listing(s) in {request.city}, "
                f"the median hourly price is ₹{med_price}. "
                f"Prices range from ₹{min_price} to ₹{max_price}."
            ),
            comparable_count=len(comparables),
            ai_generated=False,
            model_id=None,
        )
