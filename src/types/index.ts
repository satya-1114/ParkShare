export type UserRole = "DRIVER" | "OWNER" | "ADMIN";

export interface User {
  id: string;
  fullName: string;
  email: string;
  phone?: string;
  role: UserRole;
  avatarUrl?: string;
  createdAt: string;
}

export type VehicleType = "BIKE" | "CAR" | "EV" | "TRUCK" | "BICYCLE";

export type ParkingAmenity =
  | "CCTV"
  | "COVERED"
  | "SECURITY"
  | "EV_CHARGING"
  | "ACCESS_24X7";

export type PropertyType =
  | "INDIVIDUAL_HOUSE"
  | "APARTMENT"
  | "COMMERCIAL_BUILDING"
  | "HOTEL"
  | "OFFICE"
  | "EMPTY_LAND";

export interface ParkingSpace {
  id: string;
  name: string;
  area: string;
  city: string;
  state?: string;
  pincode?: string;
  distanceKm: number;
  hourlyPrice: number;
  dailyPrice?: number;
  rating: number;
  reviewCount: number;
  trustScore: number;
  verified: boolean;
  vehicleTypes: VehicleType[];
  amenities: ParkingAmenity[];
  propertyType?: PropertyType;
  totalSlots: number;
  availableSlots: number;
  imageUrl: string;
  description?: string;
  host?: {
    name: string;
    verified: boolean;
    rating: number;
    memberSince: string;
  };
}

export type BookingStatus =
  | "ACTIVE"
  | "UPCOMING"
  | "COMPLETED"
  | "CANCELLED";

export interface Booking {
  id: string;
  parkingId: string;
  parkingName: string;
  area: string;
  date: string;
  startTime: string;
  durationHours: number;
  amount: number;
  status: BookingStatus;
}

export interface TrustScore {
  score: number;
  factors: {
    identityVerified: boolean;
    photosVerified: boolean;
    positiveHistory: boolean;
    customerRatings: number;
  };
}
