import axios, { AxiosError, type AxiosInstance } from "axios";
import { config } from "@/config";
import { storageService } from "./storageService";

/**
 * Normalized API error. Extends the native Error so that `err instanceof Error`
 * checks in components/forms are TRUE and `err.message` carries the real
 * backend message (e.g. "Invalid email or password") instead of a generic
 * fallback. `status` and `details` remain available for callers that need them.
 */
export class ApiError extends Error {
  status: number;
  details?: unknown;

  constructor(message: string, status: number, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

export const api: AxiosInstance = axios.create({
  baseURL: config.apiBaseUrl,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((request) => {
  const token = storageService.getToken();
  if (token) {
    request.headers = request.headers ?? {};
    request.headers.Authorization = `Bearer ${token}`;
  }
  return request;
});

/** Extract a human-readable message from a variety of backend error shapes. */
function extractMessage(data: unknown, fallback: string): string {
  if (!data || typeof data !== "object") return fallback;
  const obj = data as Record<string, unknown>;
  if (typeof obj.message === "string" && obj.message.trim()) return obj.message;
  // FastAPI validation errors: detail can be a string or an array of {msg,...}
  const detail = obj.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as Record<string, unknown>;
    if (first && typeof first.msg === "string") return first.msg;
  }
  return fallback;
}

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ message?: string; detail?: unknown }>) => {
    if (error.response?.status === 401) {
      storageService.clearSession();
    }
    const status = error.response?.status ?? 0;
    const message = extractMessage(
      error.response?.data,
      error.message ?? "Unexpected network error",
    );
    return Promise.reject(new ApiError(message, status, error.response?.data));
  },
);
