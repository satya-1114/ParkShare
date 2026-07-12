export const config = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1",
  storageKeys: {
    token: "parkshare.auth.token",
    user: "parkshare.auth.user",
  },
} as const;
