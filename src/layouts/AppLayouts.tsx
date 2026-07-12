import { Outlet } from "@tanstack/react-router";
import { AppHeader, type AppNavItem } from "@/components/layout/AppHeader";

const driverNav: AppNavItem[] = [
  { label: "Driver Dashboard", to: "/driver" },
  { label: "Search", to: "/driver/search" },
  { label: "Bookings", to: "/driver/bookings" },
];

export function DriverLayout() {
  return (
    <div className="min-h-screen bg-surface">
      <AppHeader nav={driverNav} />
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <Outlet />
      </main>
    </div>
  );
}

const ownerNav: AppNavItem[] = [
  { label: "Owner Dashboard", to: "/owner" },
  { label: "Add Parking Space", to: "/owner/parking/new" },
];

export function OwnerLayout() {
  return (
    <div className="min-h-screen bg-surface">
      <AppHeader nav={ownerNav} />
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <Outlet />
      </main>
    </div>
  );
}

const adminNav: AppNavItem[] = [
  { label: "Admin Dashboard", to: "/admin" },
];

export function AdminLayout() {
  return (
    <div className="min-h-screen bg-surface">
      <AppHeader nav={adminNav} />
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <Outlet />
      </main>
    </div>
  );
}
