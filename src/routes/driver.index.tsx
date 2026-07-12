import { useEffect, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Calendar, CarFront, Heart, Clock, Loader2, MapPin } from "lucide-react";
import { SearchBar } from "@/components/shared/SearchBar";
import { StatCard } from "@/components/shared/StatCard";
import { ParkingCard } from "@/components/shared/ParkingCard";
import { BookingCard } from "@/components/shared/BookingCard";
import { EmptyState } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";
import { parkingService, toParkingSpace } from "@/services/parkingService";
import { bookingService, toBooking } from "@/services/bookingService";
import type { Booking, ParkingSpace } from "@/types";

export const Route = createFileRoute("/driver/")({
  component: DriverDashboard,
});

function DriverDashboard() {
  const { user } = useAuth();
  const [nearby, setNearby] = useState<ParkingSpace[] | null>(null);
  const [nearbyError, setNearbyError] = useState<string | null>(null);
  const [bookings, setBookings] = useState<Booking[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await parkingService.searchParkings({ page: 1, page_size: 3 });
        if (!cancelled) setNearby(res.items.map(toParkingSpace));
      } catch (err) {
        if (!cancelled) {
          setNearbyError(err instanceof Error ? err.message : "Failed to load parking");
          setNearby([]);
        }
      }
      try {
        const items = await bookingService.getMyBookings();
        if (!cancelled) setBookings(items.map(toBooking));
      } catch {
        if (!cancelled) setBookings([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const firstName = user?.fullName?.split(" ")[0] ?? "there";
  const activeCount = bookings?.filter((b) => b.status === "ACTIVE").length ?? 0;
  const totalCount = bookings?.length ?? 0;
  const recent = (bookings ?? []).slice(0, 3);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-2xl font-bold sm:text-3xl">
          Welcome back, {firstName}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Find a trusted parking spot near your destination.
        </p>
      </div>

      <SearchBar variant="hero" />

      <section className="grid gap-4 sm:grid-cols-3">
        <StatCard
          label="Active booking"
          value={bookings === null ? "—" : String(activeCount)}
          icon={Clock}
          hint={activeCount ? "In progress" : "No active session"}
        />
        <StatCard
          label="Total bookings"
          value={bookings === null ? "—" : String(totalCount)}
          icon={Calendar}
          hint="All time"
        />
        <StatCard label="Favorite spaces" value="0" icon={Heart} hint="Add some to compare quickly" />
      </section>

      <section>
        <div className="flex items-end justify-between">
          <div>
            <h2 className="font-display text-xl font-semibold">Nearby parking</h2>
            <p className="text-sm text-muted-foreground">Verified spaces available now.</p>
          </div>
          <Button asChild variant="ghost" size="sm">
            <Link to="/driver/search">View all</Link>
          </Button>
        </div>
        <div className="mt-4">
          {nearby === null ? (
            <div className="flex justify-center py-10 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          ) : nearbyError ? (
            <EmptyState icon={MapPin} title="Couldn't load parking" description={nearbyError} />
          ) : nearby.length === 0 ? (
            <EmptyState
              icon={MapPin}
              title="No verified parking yet"
              description="Check back soon — new listings are being verified."
            />
          ) : (
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {nearby.map((s) => (
                <ParkingCard key={s.id} space={s} />
              ))}
            </div>
          )}
        </div>
      </section>

      <section>
        <h2 className="font-display text-xl font-semibold">Recent bookings</h2>
        <div className="mt-4">
          {bookings === null ? (
            <div className="flex justify-center py-10 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          ) : recent.length === 0 ? (
            <EmptyState
              icon={CarFront}
              title="No bookings yet"
              description="Your booking history will appear here once you reserve your first parking space."
              action={
                <Button asChild>
                  <Link to="/driver/search">Find parking</Link>
                </Button>
              }
            />
          ) : (
            <div className="space-y-3">
              {recent.map((b) => (
                <BookingCard key={b.id} booking={b} />
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
