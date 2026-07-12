import { createFileRoute, redirect } from "@tanstack/react-router";
import { AdminLayout } from "@/layouts/AppLayouts";
import { storageService } from "@/services/storageService";
import { roleHome } from "@/lib/roles";

export const Route = createFileRoute("/admin")({
  ssr: false,
  beforeLoad: ({ location }) => {
    const user = storageService.getUser();
    if (!user) {
      throw redirect({ to: "/login", search: { redirect: location.href } });
    }
    if (user.role !== "ADMIN") {
      throw redirect({ to: roleHome(user.role) });
    }
  },
  component: AdminLayout,
});
