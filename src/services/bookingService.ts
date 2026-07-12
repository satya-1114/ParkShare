import { api } from "./api";
import type { Booking, BookingStatus } from "@/types";

interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data: T;
}

export type BackendBookingStatus =
  | "PENDING"
  | "CONFIRMED"
  | "ACTIVE"
  | "COMPLETED"
  | "CANCELLED";

export interface BookingDTO {
  id: string;
  driver_id: string;
  parking_id: string;
  booking_reference: string;
  booking_date: string;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  total_amount: string | number;
  status: BackendBookingStatus;
  parking_name: string;
  parking_city: string;
}

export interface BookingListDTO {
  items: BookingDTO[];
}

export interface CreateBookingPayload {
  parking_id: string;
  start_time: string; // ISO
  end_time: string; // ISO
}

const STATUS_MAP: Record<BackendBookingStatus, BookingStatus> = {
  PENDING: "UPCOMING",
  CONFIRMED: "UPCOMING",
  ACTIVE: "ACTIVE",
  COMPLETED: "COMPLETED",
  CANCELLED: "CANCELLED",
};

export function toBooking(dto: BookingDTO): Booking {
  const start = new Date(dto.start_time);
  const duration = Math.max(1, Math.round(dto.duration_minutes / 60));
  return {
    id: dto.id,
    parkingId: dto.parking_id,
    parkingName: dto.parking_name || "Parking space",
    area: dto.parking_city || "",
    date: start.toLocaleDateString(),
    startTime: start.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    durationHours: duration,
    amount: Number(dto.total_amount),
    status: STATUS_MAP[dto.status],
  };
}

export const bookingService = {
  async createBooking(payload: CreateBookingPayload): Promise<BookingDTO> {
    const res = await api.post<ApiEnvelope<BookingDTO>>("/bookings", payload);
    return res.data.data;
  },

  async getMyBookings(): Promise<BookingDTO[]> {
    const res = await api.get<ApiEnvelope<BookingListDTO>>("/bookings/mine");
    return res.data.data.items;
  },

  async getBooking(id: string): Promise<BookingDTO> {
    const res = await api.get<ApiEnvelope<BookingDTO>>(`/bookings/${id}`);
    return res.data.data;
  },

  async cancelBooking(id: string): Promise<BookingDTO> {
    const res = await api.patch<ApiEnvelope<BookingDTO>>(`/bookings/${id}/cancel`);
    return res.data.data;
  },
};
