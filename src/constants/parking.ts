import type { ParkingAmenity, PropertyType, VehicleType } from "@/types";

export const AMENITY_LABELS: Record<ParkingAmenity, string> = {
  CCTV: "CCTV",
  COVERED: "Covered",
  SECURITY: "Security",
  EV_CHARGING: "EV Charging",
  ACCESS_24X7: "24×7 Access",
};

export const VEHICLE_LABELS: Record<VehicleType, string> = {
  BIKE: "Bike",
  CAR: "Car",
  EV: "Electric Vehicle",
  TRUCK: "Truck",
  BICYCLE: "Bicycle",
};

export const PROPERTY_LABELS: Record<PropertyType, string> = {
  INDIVIDUAL_HOUSE: "Individual House",
  APARTMENT: "Apartment",
  COMMERCIAL_BUILDING: "Commercial Building",
  HOTEL: "Hotel",
  OFFICE: "Office",
  EMPTY_LAND: "Empty Land",
};
