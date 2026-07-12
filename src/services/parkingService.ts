import { api } from "./api";

import type {
  ParkingAmenity,
  ParkingSpace,
  PropertyType,
  VehicleType,
} from "@/types";

interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data: T;
}

// Backend and frontend vehicle enums are now aligned (BIKE/CAR/EV/TRUCK/BICYCLE).
// This alias remains for backward-compatible imports elsewhere in the app.
export type BackendVehicleType = VehicleType;
export type BackendAmenity =
  | "CCTV"
  | "COVERED"
  | "SECURITY"
  | "EV_CHARGING"
  | "ACCESS_24X7";
export type BackendParkingStatus = "PENDING" | "VERIFIED" | "REJECTED" | "INACTIVE";

interface ParkingImageDTO {
  id: string;
  image_url: string;
  display_order: number;
}

export interface ParkingDTO {
  id: string;
  owner_id: string;
  name: string;
  description: string | null;
  property_type: PropertyType;
  address: string;
  city: string;
  state: string;
  pin_code: string;
  latitude: number;
  longitude: number;
  total_slots: number;
  available_slots: number;
  parking_type: "COVERED" | "OPEN";
  hourly_price: string | number;
  daily_price: string | number | null;
  is_24x7: boolean;
  opening_time: string | null;
  closing_time: string | null;
  status: BackendParkingStatus;
  vehicle_types: BackendVehicleType[];
  amenities: BackendAmenity[];
  images: ParkingImageDTO[];
  created_at: string;
  updated_at: string;
}

export interface ParkingListDTO {
  items: ParkingDTO[];
  page: number;
  page_size: number;
  total: number;
}

export interface ParkingSearchParams {
  city?: string;
  vehicle_type?: BackendVehicleType;
  min_price?: number;
  max_price?: number;
  amenity?: BackendAmenity;
  page?: number;
  page_size?: number;
}

export interface CreateParkingPayload {
  name: string;
  description?: string;
  property_type: PropertyType;
  address: string;
  city: string;
  state: string;
  pin_code: string;
  latitude: number;
  longitude: number;
  total_slots: number;
  available_slots?: number;
  parking_type: "COVERED" | "OPEN";
  hourly_price: number;
  daily_price?: number;
  is_24x7: boolean;
  opening_time?: string | null;
  closing_time?: string | null;
  vehicle_types: BackendVehicleType[];
  amenities: BackendAmenity[];
  image_urls?: string[];
}

const PLACEHOLDER_IMAGE =
  "https://images.unsplash.com/photo-1470224114660-3f6686c562eb?auto=format&fit=crop&w=800&q=60";

export function toParkingSpace(dto: ParkingDTO): ParkingSpace {
  const hourly = Number(dto.hourly_price);
  const daily = dto.daily_price !== null ? Number(dto.daily_price) : undefined;
  return {
    id: dto.id,
    name: dto.name,
    area: dto.address,
    city: dto.city,
    state: dto.state,
    pincode: dto.pin_code,
    distanceKm: 0,
    hourlyPrice: hourly,
    dailyPrice: daily,
    rating: 0,
    reviewCount: 0,
    trustScore: 0,
    verified: dto.status === "VERIFIED",
    vehicleTypes: Array.from(new Set(dto.vehicle_types)),
    amenities: dto.amenities as ParkingAmenity[],
    propertyType: dto.property_type,
    totalSlots: dto.total_slots,
    availableSlots: dto.available_slots,
    imageUrl: dto.images[0]?.image_url ?? PLACEHOLDER_IMAGE,
    description: dto.description ?? undefined,
  };
}

export const parkingService = {
  async searchParkings(params: ParkingSearchParams = {}): Promise<ParkingListDTO> {
    const res = await api.get<ApiEnvelope<ParkingListDTO>>("/parkings", { params });
    return res.data.data;
  },

  async getParking(id: string): Promise<ParkingDTO> {
    const res = await api.get<ApiEnvelope<ParkingDTO>>(`/parkings/${id}`);
    return res.data.data;
  },

  async getMyParkings(): Promise<ParkingDTO[]> {
    const res = await api.get<ApiEnvelope<ParkingDTO[]>>("/parkings/mine");
    return res.data.data;
  },

  /**
   * Fetch a single parking listing owned by the authenticated owner.
   * Unlike getParking (public, VERIFIED-only), this returns the listing at any
   * status (PENDING/VERIFIED/REJECTED/INACTIVE) and 404s if not owned.
   */
  async getMyParking(id: string): Promise<ParkingDTO> {
    const res = await api.get<ApiEnvelope<ParkingDTO>>(`/parkings/mine/${id}`);
    return res.data.data;
  },


  async createParking(payload: CreateParkingPayload): Promise<ParkingDTO> {
    const res = await api.post<ApiEnvelope<ParkingDTO>>("/parkings", payload);
    return res.data.data;
  },

  async updateParking(id: string, payload: Partial<CreateParkingPayload>): Promise<ParkingDTO> {
    const res = await api.patch<ApiEnvelope<ParkingDTO>>(`/parkings/${id}`, payload);
    return res.data.data;
  },

  async deleteParking(id: string): Promise<void> {
    await api.delete(`/parkings/${id}`);
  },
};
