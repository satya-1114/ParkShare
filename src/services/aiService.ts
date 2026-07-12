/**
 * AI service — typed client for the three IBM Granite AI endpoints.
 *
 * Security note: IBM watsonx credentials are NEVER present in this file or
 * any frontend code. All Granite calls are made server-side by the FastAPI
 * backend. This module only calls the ParkShare REST API.
 */
import { api } from "./api";

interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data: T;
}

// ---------------------------------------------------------------------------
// Smart Parking Recommendation
// ---------------------------------------------------------------------------

export interface RecommendationRequest {
  city?: string;
  vehicle_type?: string;
  max_hourly_price?: number;
  preferred_amenities?: string[];
  preference_context?: string;
}

export interface RankedParking {
  parking_id: string;
  rank: number;
  reason: string;
  match_score: number;
}

export interface RecommendationResponse {
  recommendations: RankedParking[];
  total_candidates: number;
  ai_generated: boolean;
  model_id: string | null;
}

// ---------------------------------------------------------------------------
// Smart Price Suggestion
// ---------------------------------------------------------------------------

export interface PriceSuggestionRequest {
  city: string;
  state: string;
  parking_type: string;
  amenities: string[];
  vehicle_types: string[];
  total_slots: number;
  is_24x7: boolean;
}

export interface PriceSuggestionResponse {
  suggested_hourly_price: string | null;
  price_range: { min: string; max: string; median: string } | null;
  explanation: string;
  comparable_count: number;
  ai_generated: boolean;
  model_id: string | null;
}

// ---------------------------------------------------------------------------
// Trust Score Explanation
// ---------------------------------------------------------------------------

export interface TrustFactors {
  listing_verified: boolean;
  owner_phone_verified: boolean;
  owner_id_verified: boolean;
  photos_verified: boolean;
  completed_bookings: number;
  has_completed_bookings: boolean;
}

export interface TrustExplanationResponse {
  parking_id: string;
  trust_score: number;
  factors: TrustFactors;
  explanation: string;
  ai_generated: boolean;
  model_id: string | null;
}

// ---------------------------------------------------------------------------
// Service
// ---------------------------------------------------------------------------

export const aiService = {
  /**
   * Get AI-ranked parking recommendations for the authenticated driver.
   * Requires DRIVER role — Bearer token is attached by the api.ts interceptor.
   */
  async getRecommendations(
    req: RecommendationRequest,
  ): Promise<RecommendationResponse> {
    const res = await api.post<ApiEnvelope<RecommendationResponse>>(
      "/ai/recommendations",
      req,
    );
    return res.data.data;
  },

  /**
   * Get an AI price suggestion for a new parking listing.
   * Requires OWNER role — Bearer token is attached by the api.ts interceptor.
   * The backend never updates prices automatically; the owner must confirm.
   */
  async getPriceSuggestion(
    req: PriceSuggestionRequest,
  ): Promise<PriceSuggestionResponse> {
    const res = await api.post<ApiEnvelope<PriceSuggestionResponse>>(
      "/ai/price-suggestion",
      req,
    );
    return res.data.data;
  },

  /**
   * Get the deterministic trust score and Granite explanation for a parking space.
   * Public endpoint — no auth required.
   */
  async getTrustExplanation(parkingId: string): Promise<TrustExplanationResponse> {
    const res = await api.get<ApiEnvelope<TrustExplanationResponse>>(
      `/ai/trust/${parkingId}`,
    );
    return res.data.data;
  },
};
