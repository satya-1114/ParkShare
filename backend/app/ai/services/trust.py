"""Trust score service.

The trust score is always deterministic — computed from verifiable facts in the
database. IBM Granite is only invoked to produce a human-readable explanation
of the score that was already calculated.

Scoring weights (sum = 100):
    LISTING_VERIFIED          30   parking.status == VERIFIED
    PHOTOS_VERIFIED           20   parking.photos_verified
    OWNER_ID_VERIFIED         20   owner.id_verified
    OWNER_PHONE_VERIFIED      15   owner.phone_verified
    HAS_COMPLETED_BOOKINGS    15   at least one COMPLETED booking for this parking

Shared helper
-------------
``collect_trust_factors`` centralises factor collection so the recommendation
service and the trust-explanation endpoint use identical semantics.
"""
import json
import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import client as watsonx_client
from app.ai.exceptions import AIInvalidOutputError, AIServiceUnavailableError
from app.ai.logging import log_ai_fallback
from app.ai.prompts import build_trust_prompt
from app.ai.schemas import TrustExplanationResponse, TrustFactors
from app.core.config import settings
from app.models.booking import Booking, BookingStatus
from app.models.parking import ParkingSpace, ParkingStatus
from app.models.user import User
from app.repositories.parking import ParkingRepository
from app.repositories.user import UserRepository

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scoring weights — must sum to 100
# ---------------------------------------------------------------------------
WEIGHT_LISTING_VERIFIED = 30
WEIGHT_PHOTOS_VERIFIED = 20
WEIGHT_OWNER_ID_VERIFIED = 20
WEIGHT_OWNER_PHONE_VERIFIED = 15
WEIGHT_HAS_COMPLETED_BOOKINGS = 15
assert (
    WEIGHT_LISTING_VERIFIED
    + WEIGHT_PHOTOS_VERIFIED
    + WEIGHT_OWNER_ID_VERIFIED
    + WEIGHT_OWNER_PHONE_VERIFIED
    + WEIGHT_HAS_COMPLETED_BOOKINGS
) == 100, "Trust score weights must sum to 100"


def compute_trust_score(factors: TrustFactors) -> int:
    """Return a deterministic integer trust score from 0 to 100.

    This function is pure — same inputs always produce the same output.
    """
    score = 0
    if factors.listing_verified:
        score += WEIGHT_LISTING_VERIFIED
    if factors.photos_verified:
        score += WEIGHT_PHOTOS_VERIFIED
    if factors.owner_id_verified:
        score += WEIGHT_OWNER_ID_VERIFIED
    if factors.owner_phone_verified:
        score += WEIGHT_OWNER_PHONE_VERIFIED
    if factors.has_completed_bookings:
        score += WEIGHT_HAS_COMPLETED_BOOKINGS
    return score


def collect_trust_factors(
    parking: ParkingSpace,
    owner: User,
    completed_count: int,
) -> TrustFactors:
    """Build a :class:`TrustFactors` from real database values.

    This is the single place where trust factors are assembled so that the
    recommendation service and the trust-explanation endpoint cannot drift
    from each other.

    Parameters
    ----------
    parking:
        The :class:`ParkingSpace` ORM object (must be loaded with owner relation
        or the caller must pass the owner separately).
    owner:
        The :class:`User` who owns the parking space.
    completed_count:
        Number of COMPLETED bookings for this parking space.
    """
    return TrustFactors(
        listing_verified=parking.status == ParkingStatus.VERIFIED,
        owner_phone_verified=owner.phone_verified,
        owner_id_verified=owner.id_verified,
        photos_verified=parking.photos_verified,
        completed_bookings=completed_count,
        has_completed_bookings=completed_count >= 1,
    )


def _deterministic_explanation(trust_score: int, factors: TrustFactors) -> str:
    """Generate a plain-text explanation without AI when Granite is unavailable."""
    parts = []
    if factors.listing_verified:
        parts.append("listing is verified")
    if factors.photos_verified:
        parts.append("photos verified")
    if factors.owner_id_verified:
        parts.append("owner ID verified")
    if factors.owner_phone_verified:
        parts.append("owner phone verified")
    if factors.has_completed_bookings:
        parts.append(f"{factors.completed_bookings} completed booking(s)")

    if not parts:
        return f"Trust score: {trust_score}/100. No verification factors are confirmed yet."
    return (
        f"Trust score: {trust_score}/100. Verified factors: {', '.join(parts)}."
    )


async def get_trust_explanation(
    parking_id: UUID,
    session: AsyncSession,
) -> TrustExplanationResponse:
    """Compute the deterministic trust score and optionally enrich with Granite explanation.

    Raises HTTP 404 if the parking space is not found or not VERIFIED.
    """
    parking_repo = ParkingRepository(session)
    parking: ParkingSpace | None = await parking_repo.get_public_verified(parking_id)
    if parking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parking space not found",
        )

    # Load the owner
    user_repo = UserRepository(session)
    owner: User | None = await user_repo.get_by_id(parking.owner_id)
    if owner is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parking owner not found",
        )

    # Count completed bookings for this parking
    count_stmt = (
        select(func.count(Booking.id))
        .where(Booking.parking_id == parking_id)
        .where(Booking.status == BookingStatus.COMPLETED)
    )
    completed_count = int((await session.execute(count_stmt)).scalar_one())

    factors = collect_trust_factors(parking, owner, completed_count)
    trust_score = compute_trust_score(factors)

    # --- Granite explanation (best-effort) ---
    ai_generated = False
    model_id: str | None = None
    explanation = _deterministic_explanation(trust_score, factors)

    try:
        prompt = build_trust_prompt(trust_score, factors)
        raw = await watsonx_client.generate(prompt)
        parsed = json.loads(raw)
        ai_explanation = str(parsed.get("explanation", "")).strip()
        if ai_explanation:
            explanation = ai_explanation[:250]
            ai_generated = True
            model_id = settings.WATSONX_MODEL_ID
    except (AIServiceUnavailableError, AIInvalidOutputError, json.JSONDecodeError) as exc:
        log_ai_fallback(log, "trust-explanation", exc)

    return TrustExplanationResponse(
        parking_id=parking_id,
        trust_score=trust_score,
        factors=factors,
        explanation=explanation,
        ai_generated=ai_generated,
        model_id=model_id,
    )
