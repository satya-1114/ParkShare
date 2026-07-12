import type { User } from "@/types";
import { config } from "@/config";

/**
 * Owns all browser storage access. No other module (components, services,
 * contexts) may touch localStorage directly.
 * Safe to call during SSR — returns null / no-ops when window is unavailable.
 */

function isBrowser(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

function read(key: string): string | null {
  if (!isBrowser()) return null;
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key: string, value: string): void {
  if (!isBrowser()) return;
  try {
    window.localStorage.setItem(key, value);
  } catch {
    /* ignore quota / privacy errors */
  }
}

function remove(key: string): void {
  if (!isBrowser()) return;
  try {
    window.localStorage.removeItem(key);
  } catch {
    /* ignore */
  }
}

export const storageService = {
  saveToken(token: string): void {
    write(config.storageKeys.token, token);
  },
  getToken(): string | null {
    return read(config.storageKeys.token);
  },
  removeToken(): void {
    remove(config.storageKeys.token);
  },
  saveUser(user: User): void {
    write(config.storageKeys.user, JSON.stringify(user));
  },
  getUser(): User | null {
    const raw = read(config.storageKeys.user);
    if (!raw) return null;
    try {
      return JSON.parse(raw) as User;
    } catch {
      return null;
    }
  },
  clearSession(): void {
    remove(config.storageKeys.token);
    remove(config.storageKeys.user);
  },
};
