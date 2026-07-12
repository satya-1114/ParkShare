import { useEffect, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { CarFront, Loader2, X } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/shared/PageHeader";
import { BookingCard } from "@/components/shared/BookingCard";
import { EmptyState } from "@/components/shared/EmptyState";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { bookingService, toBooking, type BookingDTO } from "@/services/bookingService";
import type { Booking, BookingStatus } from "@/types";

export const Route = createFileRoute("/driver/bookings")({
  component: BookingsPage,
});

const tabs: { key: BookingStatus; label: string }[] = [
  { key: "ACTIVE", label: "Active" },
  { key: "UPCOMING", label: "Upcoming" },
  { key: "COMPLETED", label: "Completed" },
  { key: "CANCELLED", label: "Cancelled" },
];

interface BookingRow {
  booking: Booking;
  raw: BookingDTO;
}

function BookingsPage() {
  const [tab, setTab] = useState<BookingStatus>("UPCOMING");
  const [rows, setRows] = useState<BookingRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cancellingId, setCancellingId] = useState<string | null>(null);

  async function load() {
    try {
      const items = await bookingService.getMyBookings();
      setRows(items.map((raw) => ({ raw, booking: toBooking(raw) })));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load bookings");
      setRows([]);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function cancel(id: string) {
    setCancellingId(id);
    try {
      await bookingService.cancelBooking(id);
      toast.success("Booking cancelled");
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Cancel failed");
    } finally {
      setCancellingId(null);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="My bookings"
        description="Track your current, upcoming and past parking reservations."
      />
      <Tabs value={tab} onValueChange={(v) => setTab(v as BookingStatus)}>
        <TabsList>
          {tabs.map((t) => (
            <TabsTrigger key={t.key} value={t.key}>{t.label}</TabsTrigger>
          ))}
        </TabsList>

        {rows === null ? (
          <div className="mt-8 flex justify-center text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : error ? (
          <EmptyState
            icon={CarFront}
            title="Couldn't load bookings"
            description={error}
          />
        ) : (
          tabs.map((t) => {
            const items = rows.filter((r) => r.booking.status === t.key);
            return (
              <TabsContent key={t.key} value={t.key} className="mt-6">
                {items.length ? (
                  <div className="space-y-3">
                    {items.map((r) => (
                      <div key={r.booking.id} className="space-y-2">
                        <BookingCard booking={r.booking} />
                        {(t.key === "UPCOMING" || t.key === "ACTIVE") && (
                          <div className="flex justify-end">
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={cancellingId === r.booking.id}
                              onClick={() => cancel(r.booking.id)}
                            >
                              <X className="mr-1 h-3.5 w-3.5" />
                              {cancellingId === r.booking.id ? "Cancelling…" : "Cancel booking"}
                            </Button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    icon={CarFront}
                    title={`No ${t.label.toLowerCase()} bookings`}
                    description="When you have bookings in this state, they'll show up here."
                    action={
                      <Button asChild>
                        <Link to="/driver/search">Find parking</Link>
                      </Button>
                    }
                  />
                )}
              </TabsContent>
            );
          })
        )}
      </Tabs>
    </div>
  );
}
