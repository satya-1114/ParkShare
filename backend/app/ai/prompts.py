"""Prompt builder functions for IBM Granite model calls.

Each function accepts the structured data needed for inference and returns a
complete prompt string that instructs Granite to reply ONLY with valid JSON.

Rules enforced in every prompt:
- Respond ONLY with valid JSON (no markdown fences, no commentary).
- Do NOT invent parking IDs, ratings, distances, or verifications.
- Use ONLY the data provided in the prompt.
"""
import json
from decimal import Decimal
from typing import Any, Dict, List

from app.ai.schemas import RecommendationRequest, PriceSuggestionRequest, TrustFactors


def build_recommendation_prompt(
    request: RecommendationRequest,
    candidates: List[Dict[str, Any]],
) -> str:
    """Return a prompt that asks Granite to rank the provided parking candidates.

    Parameters
    ----------
    request:
        The user's recommendation request (city, vehicle, preferences…).
    candidates:
        Pre-fetched and pre-ranked candidate list.  Each dict contains:
        parking_id, name, city, hourly_price, amenities (list of strings),
        vehicle_types (list of strings), trust_score (int).
    """
    preference_note = (
        f"\nUser context: {request.preference_context}"
        if request.preference_context
        else ""
    )
    preferred_amenities = (
        [a.value for a in request.preferred_amenities]
        if request.preferred_amenities
        else []
    )

    system_instructions = (
        "You are a parking space ranking assistant. "
        "Your task is to rank the supplied parking spaces based on how well "
        "they match the user preferences. "
        "IMPORTANT RULES:\n"
        "1. Respond ONLY with valid JSON — no markdown, no code fences, no extra text.\n"
        "2. Do NOT invent parking_id values. Only use the parking_id values from the "
        "candidates list provided.\n"
        "3. Do NOT invent ratings, distances, or verification statuses.\n"
        "4. If two spaces are equally good, prefer lower hourly_price.\n"
        "5. Keep each 'reason' field under 150 characters.\n"
        "6. match_score must be an integer from 0 to 100.\n"
    )

    user_message = (
        f"City filter: {request.city or 'Any'}\n"
        f"Vehicle type: {request.vehicle_type.value if request.vehicle_type else 'Any'}\n"
        f"Max hourly price: {request.max_hourly_price or 'Any'}\n"
        f"Preferred amenities: {preferred_amenities}{preference_note}\n\n"
        f"Candidates (JSON):\n{json.dumps(candidates, default=str)}\n\n"
        "Return JSON in this exact format:\n"
        '{"recommendations": [{"parking_id": "<uuid>", "rank": 1, '
        '"match_score": 85, "reason": "<brief reason>"}]}'
    )

    return f"{system_instructions}\n\n{user_message}"


def build_pricing_prompt(
    request: PriceSuggestionRequest,
    min_price: Decimal,
    max_price: Decimal,
    median_price: Decimal,
    comparable_count: int,
    lower_bound: Decimal,
    upper_bound: Decimal,
) -> str:
    """Return a prompt asking Granite for a price suggestion.

    Parameters
    ----------
    request:
        The owner's new parking details.
    min_price / max_price / median_price:
        Statistics computed from comparable verified listings.
    comparable_count:
        Number of comparable listings used for statistics.
    lower_bound / upper_bound:
        Dynamic allowed price range derived from the comparable median.
        Granite is explicitly told to stay within these bounds.
    """
    amenities = [a.value for a in request.amenities]
    vehicles = [v.value for v in request.vehicle_types]

    system_instructions = (
        "You are a parking price advisor. "
        "Suggest a competitive hourly price for a new parking space. "
        "IMPORTANT RULES:\n"
        "1. Respond ONLY with valid JSON — no markdown, no code fences, no extra text.\n"
        "2. suggested_hourly_price must be a number (no currency symbols).\n"
        "3. suggested_hourly_price MUST be between {lower} and {upper} (inclusive).\n"
        "4. Base your suggestion on the comparable listings data provided.\n"
        "5. Keep the explanation under 200 characters.\n"
    ).format(lower=lower_bound, upper=upper_bound)

    user_message = (
        f"New parking details:\n"
        f"  City: {request.city}, State: {request.state}\n"
        f"  Parking type: {request.parking_type.value}\n"
        f"  Amenities: {amenities}\n"
        f"  Vehicle types: {vehicles}\n"
        f"  Total slots: {request.total_slots}\n"
        f"  Available 24x7: {request.is_24x7}\n\n"
        f"Comparable listings in {request.city} ({comparable_count} spaces):\n"
        f"  Min price: {min_price}\n"
        f"  Max price: {max_price}\n"
        f"  Median price: {median_price}\n"
        f"  Allowed price range: {lower_bound} to {upper_bound}\n\n"
        "Return JSON in this exact format:\n"
        '{"suggested_hourly_price": 65, "explanation": "<brief explanation>", '
        '"factors": ["<factor1>", "<factor2>"]}'
    )

    return f"{system_instructions}\n\n{user_message}"


def build_trust_prompt(trust_score: int, factors: TrustFactors) -> str:
    """Return a prompt asking Granite to explain the trust score.

    The trust score has already been computed deterministically. Granite's
    only job is to produce a human-readable explanation of the score.

    Parameters
    ----------
    trust_score:
        Deterministically computed score (0–100).
    factors:
        The :class:`TrustFactors` breakdown.
    """
    system_instructions = (
        "You are a trust advisor for a parking marketplace. "
        "Explain the given trust score to a driver in plain language. "
        "IMPORTANT RULES:\n"
        "1. Respond ONLY with valid JSON — no markdown, no code fences, no extra text.\n"
        "2. Do NOT suggest a different trust score — the score is final.\n"
        "3. Do NOT invent verifications that are not in the factors.\n"
        "4. Keep the explanation under 250 characters.\n"
    )

    factors_dict = {
        "listing_verified": factors.listing_verified,
        "owner_phone_verified": factors.owner_phone_verified,
        "owner_id_verified": factors.owner_id_verified,
        "photos_verified": factors.photos_verified,
        "completed_bookings": factors.completed_bookings,
        "has_completed_bookings": factors.has_completed_bookings,
    }

    user_message = (
        f"Trust score: {trust_score}/100\n"
        f"Factors: {json.dumps(factors_dict)}\n\n"
        "Return JSON in this exact format:\n"
        '{"explanation": "<plain language explanation under 250 characters>"}'
    )

    return f"{system_instructions}\n\n{user_message}"
