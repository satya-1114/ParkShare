import { api } from "./api";
import type { ParkingDTO } from "./parkingService";

interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data: T;
}

/**
 * Admin parking verification API. All endpoints require an authenticated
 * ADMIN user; the backend enforces the role via `require_admin`. The frontend
 * route guard is only a UX helper.
 */
export const adminService = {
  async getPendingParkings(): Promise<ParkingDTO[]> {
    const res = await api.get<ApiEnvelope<ParkingDTO[]>>("/admin/parkings/pending");
    return res.data.data;
  },

  async approveParking(id: string): Promise<ParkingDTO> {
    const res = await api.patch<ApiEnvelope<ParkingDTO>>(`/admin/parkings/${id}/approve`);
    return res.data.data;
  },

  async rejectParking(id: string): Promise<ParkingDTO> {
    const res = await api.patch<ApiEnvelope<ParkingDTO>>(`/admin/parkings/${id}/reject`);
    return res.data.data;
  },
};
