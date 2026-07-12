import type { User, UserRole } from "@/types";
import { api } from "./api";
import { storageService } from "./storageService";

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  fullName: string;
  email: string;
  phone: string;
  password: string;
  role: UserRole;
}

export interface AuthResult {
  user: User;
  token: string;
}

interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data: T;
}

interface AuthTokenResponseDTO {
  access_token: string;
  token_type: string;
  user: UserDTO;
}

interface UserDTO {
  id: string;
  full_name: string;
  email: string;
  phone: string | null;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

function toUser(dto: UserDTO): User {
  return {
    id: dto.id,
    fullName: dto.full_name,
    email: dto.email,
    phone: dto.phone ?? undefined,
    role: dto.role,
    createdAt: dto.created_at,
  };
}

async function completeAuth(dto: AuthTokenResponseDTO): Promise<AuthResult> {
  const user = toUser(dto.user);
  storageService.saveToken(dto.access_token);
  storageService.saveUser(user);
  return { user, token: dto.access_token };
}

export const authService = {
  async login(payload: LoginPayload): Promise<AuthResult> {
    const res = await api.post<ApiEnvelope<AuthTokenResponseDTO>>("/auth/login", {
      email: payload.email,
      password: payload.password,
    });
    return completeAuth(res.data.data);
  },

  async register(payload: RegisterPayload): Promise<AuthResult> {
    if (payload.role !== "DRIVER" && payload.role !== "OWNER") {
      throw new Error("Invalid registration role");
    }
    const res = await api.post<ApiEnvelope<AuthTokenResponseDTO>>("/auth/register", {
      full_name: payload.fullName,
      email: payload.email,
      phone: payload.phone,
      password: payload.password,
      role: payload.role,
    });
    return completeAuth(res.data.data);
  },

  async logout(): Promise<void> {
    storageService.clearSession();
  },

  async fetchCurrentUser(): Promise<User | null> {
    if (!storageService.getToken()) return null;
    try {
      const res = await api.get<ApiEnvelope<UserDTO>>("/auth/me");
      const user = toUser(res.data.data);
      storageService.saveUser(user);
      return user;
    } catch {
      storageService.clearSession();
      return null;
    }
  },

  getCachedUser(): User | null {
    return storageService.getUser();
  },
};
