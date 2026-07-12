"""Pydantic I/O schemas for the AI endpoints."""
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.parking import Amenity, ParkingType, VehicleType


# ---------------------------------------------------------------------------
# Recommendation
# ---------------------------------------------------------------------------

class RecommendationRequest(BaseModel):
    city: Optional[str] = None
    vehicle_type: Optional[VehicleType] = None
    max_hourly_price: Optional[Decimal] = None
    preferred_amenities: List[Amenity] = []
    preference_context: str = Field(default="", max_length=500)


class RankedParking(BaseModel):
    parking_id: UUID
    rank: int
    reason: str = Field(max_length=150)
    match_score: int = Field(ge=0, le=100)


class RecommendationResponse(BaseModel):
    recommendations: List[RankedParking]
    total_candidates: int
    ai_generated: bool
    model_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------

class PriceSuggestionRequest(BaseModel):
    city: str
    state: str
    parking_type: ParkingType
    amenities: List[Amenity] = []
    vehicle_types: List[VehicleType] = []
    total_slots: int
    is_24x7: bool


class PriceSuggestionResponse(BaseModel):
    suggested_hourly_price: Optional[Decimal] = None
    price_range: Optional[Dict[str, Decimal]] = None  # {"min": x, "max": y, "median": z}
    explanation: str
    comparable_count: int
    ai_generated: bool
    model_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Trust
# ---------------------------------------------------------------------------

class TrustFactors(BaseModel):
    listing_verified: bool
    owner_phone_verified: bool
    owner_id_verified: bool
    photos_verified: bool
    completed_bookings: int
    has_completed_bookings: bool  # completed_bookings >= 1


class TrustExplanationResponse(BaseModel):
    parking_id: UUID
    trust_score: int = Field(ge=0, le=100)
    factors: TrustFactors
    explanation: str
    ai_generated: bool
    model_id: Optional[str] = None
