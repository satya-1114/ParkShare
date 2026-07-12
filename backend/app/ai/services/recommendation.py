"""Recommendation service.

Flow:
1. Query ParkingRepository.search() with the user's filters (up to 15 candidates),
   eagerly loading each space's owner so we have real verification data without
   an N+1 query.
2. If no candidates → return empty list with ai_generated=False.
3. Deterministic pre-rank: sort by (amenity match count DESC, hourly_price ASC).
4. Compute deterministic trust score for each candidate using the shared
   collect_trust_factors helper from the trust service (same semantics as the
   trust-explanation endpoint).
5. Build candidate payload for the Granite prompt.
6. Call Granite, parse JSON.
7. Validate every returned parking_id is in the candidate set → reject invented IDs.
8. Deduplicate by parking_id.
9. If < 1 valid result after filtering → return deterministic ranking with
   ai_generated=False.
10. Return ranked list with ai_generated=True.

Exception boundaries
--------------------
Only AI-boundary failures (AIServiceUnavailableError, AIInvalidOutputError,
json.JSONDecodeError, ValueError from int() / match_score coercion) trigger the
deterministic fallback.  Database errors and programming mistakes are **not**
caught here and will propagate normally.
"""
import json
import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import client as watsonx_client
from app.ai.exceptions import AIInvalidOutputError, AIServiceUnavailableError
from app.ai.logging import log_ai_fallback
from app.ai.prompts import build_recommendation_prompt
from app.ai.schemas import (
    RankedParking,
    RecommendationRequest,
    RecommendationResponse,
)
from app.ai.services.trust import collect_trust_factors, compute_trust_score
from app.core.config import settings
from app.models.booking import Booking, BookingStatus
from app.models.parking import Amenity, ParkingSpace, ParkingStatus
from app.repositories.parking import ParkingRepository

log = logging.getLogger(__name__)

_MAX_CANDIDATES = 15


async def _completed_booking_count(session: AsyncSession, parking_id: UUID) -> int:
    stmt = (
        select(func.count(Booking.id))
        .where(Booking.parking_id == parking_id)
        .where(Booking.status == BookingStatus.COMPLETED)
    )
    return int((await session.execute(stmt)).scalar_one())


def _amenity_match_count(space: ParkingSpace, preferred: list[Amenity]) -> int:
    if not preferred:
        return 0
    space_amenities = {pa.amenity for pa in space.amenities}
    return sum(1 for a in preferred if a in space_amenities)


async def get_recommendations(
    request: RecommendationRequest,
    session: AsyncSession,
) -> RecommendationResponse:
    repo = ParkingRepository(session)

    # include_owner=True eagerly loads ParkingSpace.owner in the same query,
    # avoiding N+1 lookups when building real trust factors below.
    items, _total = await repo.search(
        city=request.city,
        vehicle_type=request.vehicle_type,
        max_price=request.max_hourly_price,
        page=1,
        page_size=_MAX_CANDIDATES,
        include_owner=True,
    )

    if not items:
        return RecommendationResponse(
            recommendations=[],
            total_candidates=0,
            ai_generated=False,
            model_id=None,
        )

    # Deterministic pre-rank
    preferred = request.preferred_amenities or []
    items.sort(
        key=lambda s: (-_amenity_match_count(s, preferred), float(s.hourly_price))
    )

    # Build candidate dicts using real owner verification data.
    # collect_trust_factors is the shared helper from trust.py — same semantics
    # as the trust-explanation endpoint so ranking cannot drift.
    candidates = []
    for space in items:
        completed = await _completed_booking_count(session, space.id)
        # space.owner is eagerly loaded; owner is always present for VERIFIED spaces
        owner = space.owner
        factors = collect_trust_factors(space, owner, completed)
        trust_score = compute_trust_score(factors)
        candidates.append({
            "parking_id": str(space.id),
            "name": space.name,
            "city": space.city,
            "hourly_price": str(space.hourly_price),
            "amenities": [pa.amenity.value for pa in space.amenities],
            "vehicle_types": [pvt.vehicle_type.value for pvt in space.vehicle_types],
            "trust_score": trust_score,
        })

    valid_ids: set[str] = {c["parking_id"] for c in candidates}

    # Deterministic fallback rankings (used if AI fails or returns < 1 valid result)
    deterministic = [
        RankedParking(
            parking_id=UUID(c["parking_id"]),
            rank=idx + 1,
            reason="Best match based on amenities and price",
            match_score=max(0, 100 - idx * 10),
        )
        for idx, c in enumerate(candidates)
    ]

    # Only AI-boundary failures trigger the fallback.
    # Database errors and programming mistakes are not caught here.
    try:
        prompt = build_recommendation_prompt(request, candidates)
        raw = await watsonx_client.generate(prompt)
        parsed = json.loads(raw)
        recs_raw = parsed.get("recommendations", [])
        if not isinstance(recs_raw, list):
            raise AIInvalidOutputError("recommendations is not a list")

        # Validate: reject invented IDs, deduplicate
        seen: set[str] = set()
        validated: list[RankedParking] = []
        for item in recs_raw:
            pid = str(item.get("parking_id", ""))
            if pid not in valid_ids:
                log.debug("Rejected invented parking_id from Granite: %s", pid)
                continue
            if pid in seen:
                continue
            seen.add(pid)
            validated.append(
                RankedParking(
                    parking_id=UUID(pid),
                    rank=int(item.get("rank", len(validated) + 1)),
                    reason=str(item.get("reason", ""))[:150],
                    match_score=max(0, min(100, int(item.get("match_score", 50)))),
                )
            )

        if not validated:
            log.debug("All Granite parking_ids were invalid; falling back to deterministic")
            return RecommendationResponse(
                recommendations=deterministic,
                total_candidates=len(items),
                ai_generated=False,
                model_id=None,
            )

        return RecommendationResponse(
            recommendations=validated,
            total_candidates=len(items),
            ai_generated=True,
            model_id=settings.WATSONX_MODEL_ID,
        )

    except (AIServiceUnavailableError, AIInvalidOutputError, json.JSONDecodeError, ValueError) as exc:
        log_ai_fallback(log, "recommendations", exc)
        return RecommendationResponse(
            recommendations=deterministic,
            total_candidates=len(items),
            ai_generated=False,
            model_id=None,
        )
