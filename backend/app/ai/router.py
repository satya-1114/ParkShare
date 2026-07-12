"""AI FastAPI router — mounted at /api/v1/ai.

Endpoints
---------
POST /ai/recommendations   — driver only
POST /ai/price-suggestion  — owner/admin only
GET  /ai/trust/{parking_id} — public (VERIFIED parkings only)
"""
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.schemas import (
    RecommendationRequest,
    RecommendationResponse,
    PriceSuggestionRequest,
    PriceSuggestionResponse,
    TrustExplanationResponse,
)
from app.ai.services.recommendation import get_recommendations
from app.ai.services.pricing import get_price_suggestion
from app.ai.services.trust import get_trust_explanation
from app.core.responses import ok
from app.database.session import get_session
from app.dependencies.auth import require_driver, require_owner

router = APIRouter(prefix="/ai", tags=["AI"])


@router.post("/recommendations", response_model=None)
async def recommendations_endpoint(
    body: RecommendationRequest,
    _user=Depends(require_driver),
    session: AsyncSession = Depends(get_session),
):
    """Return AI-ranked parking recommendations for the authenticated driver."""
    result: RecommendationResponse = await get_recommendations(body, session)
    return ok(result.model_dump(), "Recommendations ready")


@router.post("/price-suggestion", response_model=None)
async def price_suggestion_endpoint(
    body: PriceSuggestionRequest,
    _user=Depends(require_owner),
    session: AsyncSession = Depends(get_session),
):
    """Return an AI price suggestion for a new parking listing (owner only)."""
    result: PriceSuggestionResponse = await get_price_suggestion(body, session)
    return ok(result.model_dump(), "Price suggestion ready")


@router.get("/trust/{parking_id}", response_model=None)
async def trust_endpoint(
    parking_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Return the deterministic trust score and AI explanation for a verified parking space."""
    result: TrustExplanationResponse = await get_trust_explanation(parking_id, session)
    return ok(result.model_dump(), "Trust score ready")
