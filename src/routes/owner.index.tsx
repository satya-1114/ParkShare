import { useEffect, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Plus, Wallet, Calendar, Building2, Star, Inbox, TrendingUp, MapPin, Loader2 } from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { StatCard } from "@/components/shared/StatCard";
import { EmptyState } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/button";
import { PriceDisplay } from "@/components/shared/PriceDisplay";
import { Badge } from "@/components/ui/badge";
import { parkingService, type ParkingDTO } from "@/services/parkingService";
import { useAuth } from "@/contexts/AuthContext";

export const Route = createFileRoute("/owner/")({
  component: OwnerDashboard,
});

const STATUS_LABEL: Record<ParkingDTO["status"], string> = {
  PENDING: "Pending verification",
  VERIFIED: "Active",
  REJECTED: "Rejected",
  INACTIVE: "Inactive",
};

const STATUS_CLASS: Record<ParkingDTO["status"], string> = {
  PENDING: "bg-warning/15 text-warning-foreground border-warning/30",
  VERIFIED: "bg-success/15 text-success-foreground border-success/30",
  REJECTED: "bg-destructive/10 text-destructive border-destructive/20",
  INACTIVE: "bg-muted text-muted-foreground border-transparent",
};

function OwnerDashboard() {
  const { user } = useAuth();
  const [listings, setListings] = useState<ParkingDTO[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await parkingService.getMyParkings();
        if (!cancelled) setListings(data);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load listings");
          setListings([]);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const firstName = user?.fullName?.split(" ")[0] ?? "there";

  return (
    <div className="space-y-8">
      <PageHeader
        title={`Welcome back, ${firstName}`}
        description="Manage your parking spaces and monitor your earnings."
        actions={
          <Button asChild>
            <Link to="/owner/parking/new">
              <Plus className="mr-1 h-4 w-4" /> Add parking space
            </Link>
          </Button>
        }
      />

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total earnings" value="₹0" icon={Wallet} hint="This month" />
        <StatCard label="Total bookings" value="0" icon={Calendar} hint="All time" />
        <StatCard label="Active listings" value={listings ? String(listings.length) : "—"} icon={Building2} />
        <StatCard label="Average rating" value="—" icon={Star} hint="Once you've had reviews" />
      </section>

      <section>
        <div className="flex items-end justify-between">
          <div>
            <h2 className="font-display text-xl font-semibold">Your listings</h2>
            <p className="text-sm text-muted-foreground">Spaces currently on ParkShare.</p>
          </div>
          <Button asChild variant="outline" size="sm">
            <Link to="/owner/parking/new">
              <Plus className="mr-1 h-4 w-4" /> New listing
            </Link>
          </Button>
        </div>
        <div className="mt-4">
          {listings === null ? (
            <div className="flex justify-center py-10 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          ) : error ? (
            <EmptyState icon={Inbox} title="Couldn't load listings" description={error} />
          ) : listings.length === 0 ? (
            <EmptyState
              icon={Building2}
              title="No listings yet"
              description="Create your first parking listing to start earning."
              action={
                <Button asChild>
                  <Link to="/owner/parking/new">Add parking space</Link>
                </Button>
              }
            />
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {listings.map((l) => (
                <Link
                  key={l.id}
                  to="/owner/parking/$parkingId"
                  params={{ parkingId: l.id }}
                  className="flex gap-4 rounded-xl border border-border bg-card p-4 transition-colors hover:border-primary/40"
                >
                  <div className="flex h-24 w-32 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
                    <Building2 className="h-6 w-6" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <h3 className="truncate font-semibold">{l.name}</h3>
                        <p className="mt-0.5 flex items-center gap-1 text-xs text-muted-foreground">
                          <MapPin className="h-3 w-3" />
                          {l.city}, {l.state}
                        </p>
                      </div>
                      <Badge variant="outline" className={STATUS_CLASS[l.status]}>
                        {STATUS_LABEL[l.status]}
                      </Badge>
                    </div>
                    <div className="mt-3 flex items-end justify-between">
                      <PriceDisplay amount={Number(l.hourly_price)} />
                      <span className="text-xs text-muted-foreground">
                        {l.total_slots} {l.total_slots === 1 ? "slot" : "slots"}
                      </span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </section>

      <section>
        <h2 className="font-display text-xl font-semibold">Recent booking requests</h2>
        <div className="mt-4">
          <EmptyState
            icon={Inbox}
            title="No booking requests yet"
            description="When drivers reserve one of your spaces, you'll see the details here."
          />
        </div>
      </section>

      <section>
        <h2 className="font-display text-xl font-semibold">Earnings overview</h2>
        <div className="mt-4 rounded-xl border border-border bg-card p-6">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-muted-foreground">This month</p>
              <p className="mt-1 font-display text-3xl font-bold">₹0</p>
              <p className="mt-1 text-xs text-muted-foreground">Detailed analytics arrive with your first booking.</p>
            </div>
            <span className="flex h-10 w-10 items-center justify-center rounded-md bg-accent text-accent-foreground">
              <TrendingUp className="h-5 w-5" />
            </span>
          </div>
          <div className="mt-6 grid grid-cols-7 items-end gap-2 h-24">
            {Array.from({ length: 7 }).map((_, i) => (
              <div key={i} className="rounded-t bg-muted" style={{ height: `${20 + i * 6}%` }} aria-hidden />
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
