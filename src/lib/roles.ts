import type { UserRole } from "@/types";

/**
 * Maps a backend user role to the home route for that role's experience.
 * DRIVER -> driver app, OWNER -> owner dashboard, ADMIN -> admin dashboard.
 */
export function roleHome(role: UserRole): "/driver" | "/owner" | "/admin" {
  switch (role) {
    case "ADMIN":
      return "/admin";
    case "OWNER":
      return "/owner";
    case "DRIVER":
    default:
      return "/driver";
  }
}
