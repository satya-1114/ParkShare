import { useCallback, useEffect, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { ShieldCheck, Check, X, MapPin, Loader2, Inbox } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/shared/PageHeader";
import { EmptyState } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { PriceDisplay } from "@/components/shared/PriceDisplay";
import { AMENITY_LABELS, PROPERTY_LABELS, VEHICLE_LABELS } from "@/constants/parking";
import { adminService } from "@/services/adminService";
import type { ParkingDTO } from "@/services/parkingService";

export const Route = createFileRoute("/admin/")({
  component: AdminDashboard,
});

function AdminDashboard() {
  const [pending, setPending] = useState<ParkingDTO[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actingId, setActingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await adminService.getPendingParkings();
      setPending(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load pending listings");
      setPending([]);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function act(id: string, action: "approve" | "reject") {
    setActingId(id);
    try {
      if (action === "approve") {
        await adminService.approveParking(id);
        toast.success("Parking approved and verified");
      } else {
        await adminService.rejectParking(id);
        toast.success("Parking rejected");
      }
      // Refresh from backend — never fake local status transitions.
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Action failed");
    } finally {
      setActingId(null);
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Parking verification"
        description="Review and verify parking listings submitted by owners."
      />

      {pending === null ? (
        <div className="flex justify-center py-16 text-muted-foreground">
          <Loader2 className="h-5 w-5 animate-spin" />
        </div>
      ) : error ? (
        <EmptyState icon={Inbox} title="Couldn't load pending listings" description={error} />
      ) : pending.length === 0 ? (
        <EmptyState
          icon={ShieldCheck}
          title="Nothing to review"
          description="There are no parking listings awaiting verification right now."
        />
      ) : (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            <span className="font-medium text-foreground">{pending.length}</span> listing
            {pending.length === 1 ? "" : "s"} awaiting verification
          </p>
          {pending.map((p) => (
            <PendingCard
              key={p.id}
              parking={p}
              busy={actingId === p.id}
              onApprove={() => act(p.id, "approve")}
              onReject={() => act(p.id, "reject")}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface PendingCardProps {
  parking: ParkingDTO;
  busy: boolean;
  onApprove: () => void;
  onReject: () => void;
}

function PendingCard({ parking: p, busy, onApprove, onReject }: PendingCardProps) {
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-semibold">{p.name}</h3>
            <Badge variant="outline" className="bg-warning/15 text-warning-foreground border-warning/30">
              Pending
            </Badge>
            <span className="rounded-full bg-muted px-2 py-0.5 text-xs">
              {PROPERTY_LABELS[p.property_type]}
            </span>
          </div>
          <p className="mt-1 flex items-center gap-1 text-sm text-muted-foreground">
            <MapPin className="h-3.5 w-3.5" />
            {p.address}, {p.city}, {p.state} {p.pin_code}
          </p>
        </div>
        <PriceDisplay amount={Number(p.hourly_price)} />
      </div>

      {p.description && (
        <p className="mt-3 text-sm text-muted-foreground">{p.description}</p>
      )}

      <div className="mt-4 grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
        <Detail label="Parking type" value={p.parking_type === "COVERED" ? "Covered" : "Open"} />
        <Detail label="Total slots" value={String(p.total_slots)} />
        <Detail label="Available" value={String(p.available_slots)} />
        <Detail
          label="Hours"
          value={p.is_24x7 ? "24×7" : `${p.opening_time ?? "—"} – ${p.closing_time ?? "—"}`}
        />
      </div>

      <div className="mt-4 flex flex-wrap gap-4 text-sm">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Vehicles</p>
          <p className="mt-0.5">
            {p.vehicle_types.length
              ? p.vehicle_types.map((v) => VEHICLE_LABELS[v]).join(" · ")
              : "Not specified"}
          </p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Amenities</p>
          <p className="mt-0.5">
            {p.amenities.length
              ? p.amenities.map((a) => AMENITY_LABELS[a]).join(" · ")
              : "None listed"}
          </p>
        </div>
      </div>

      <Separator className="my-4" />

      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={onReject} disabled={busy}>
          {busy ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <X className="mr-1 h-4 w-4" />}
          Reject
        </Button>
        <Button onClick={onApprove} disabled={busy}>
          {busy ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <Check className="mr-1 h-4 w-4" />}
          Approve
        </Button>
      </div>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-0.5">{value}</p>
    </div>
  );
}
