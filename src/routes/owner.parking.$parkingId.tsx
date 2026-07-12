import { useEffect, useState } from "react";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { ArrowLeft, Loader2, Save, Trash2, MapPin } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { AMENITY_LABELS, PROPERTY_LABELS, VEHICLE_LABELS } from "@/constants/parking";
import {
  parkingService,
  type BackendAmenity,
  type BackendParkingStatus,
  type CreateParkingPayload,
  type ParkingDTO,
} from "@/services/parkingService";
import type { ParkingAmenity, PropertyType, VehicleType } from "@/types";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/owner/parking/$parkingId")({
  component: OwnerParkingDetail,
});

const STATUS_LABEL: Record<BackendParkingStatus, string> = {
  PENDING: "Pending verification",
  VERIFIED: "Verified",
  REJECTED: "Rejected",
  INACTIVE: "Inactive",
};

const STATUS_CLASS: Record<BackendParkingStatus, string> = {
  PENDING: "bg-warning/15 text-warning-foreground border-warning/30",
  VERIFIED: "bg-success/15 text-success-foreground border-success/30",
  REJECTED: "bg-destructive/10 text-destructive border-destructive/20",
  INACTIVE: "bg-muted text-muted-foreground border-transparent",
};

const allAmenities: ParkingAmenity[] = ["CCTV", "COVERED", "SECURITY", "EV_CHARGING", "ACCESS_24X7"];
const allVehicles: VehicleType[] = ["BIKE", "CAR", "EV", "TRUCK", "BICYCLE"];

interface FormState {
  name: string;
  description: string;
  propertyType: PropertyType;
  address: string;
  city: string;
  state: string;
  pincode: string;
  totalSlots: string;
  availableSlots: string;
  covered: "COVERED" | "OPEN";
  hourlyPrice: string;
  dailyPrice: string;
  is247: boolean;
  openTime: string;
  closeTime: string;
  vehicleTypes: VehicleType[];
  amenities: ParkingAmenity[];
}

function toForm(dto: ParkingDTO): FormState {
  return {
    name: dto.name,
    description: dto.description ?? "",
    propertyType: dto.property_type,
    address: dto.address,
    city: dto.city,
    state: dto.state,
    pincode: dto.pin_code,
    totalSlots: String(dto.total_slots),
    availableSlots: String(dto.available_slots),
    covered: dto.parking_type,
    hourlyPrice: String(dto.hourly_price),
    dailyPrice: dto.daily_price != null ? String(dto.daily_price) : "",
    is247: dto.is_24x7,
    openTime: (dto.opening_time ?? "08:00").slice(0, 5),
    closeTime: (dto.closing_time ?? "20:00").slice(0, 5),
    vehicleTypes: Array.from(new Set(dto.vehicle_types)) as VehicleType[],
    amenities: dto.amenities as ParkingAmenity[],
  };
}

function OwnerParkingDetail() {
  const { parkingId } = Route.useParams();
  const navigate = useNavigate();
  const [dto, setDto] = useState<ParkingDTO | null>(null);
  const [form, setForm] = useState<FormState | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await parkingService.getMyParking(parkingId);
        if (!cancelled) {
          setDto(data);
          setForm(toForm(data));
        }
      } catch (err) {
        if (!cancelled) setLoadError(err instanceof Error ? err.message : "Failed to load listing");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [parkingId]);

  const update = <K extends keyof FormState>(k: K, v: FormState[K]) =>
    setForm((f) => (f ? { ...f, [k]: v } : f));

  function toggle<K extends "vehicleTypes" | "amenities">(k: K, value: FormState[K][number]) {
    setForm((f) => {
      if (!f) return f;
      const list = f[k] as string[];
      const next = list.includes(value)
        ? list.filter((x) => x !== value)
        : [...list, value];
      return { ...f, [k]: next as FormState[K] };
    });
  }

  async function save() {
    if (!form) return;
    if (!/^\d{6}$/.test(form.pincode)) {
      toast.error("PIN code must be 6 digits");
      return;
    }
    const total = Number(form.totalSlots);
    const available = Number(form.availableSlots);
    const hourly = Number(form.hourlyPrice);
    if (!Number.isFinite(total) || total <= 0) {
      toast.error("Total slots must be greater than 0");
      return;
    }
    if (!Number.isFinite(available) || available < 0 || available > total) {
      toast.error("Available slots must be between 0 and total slots");
      return;
    }
    if (!Number.isFinite(hourly) || hourly < 0) {
      toast.error("Enter a valid hourly price");
      return;
    }
    setSaving(true);
    try {
      const payload: Partial<CreateParkingPayload> = {
        name: form.name,
        description: form.description || undefined,
        property_type: form.propertyType,
        address: form.address,
        city: form.city,
        state: form.state,
        pin_code: form.pincode,
        total_slots: total,
        available_slots: available,
        parking_type: form.covered,
        hourly_price: hourly,
        daily_price: form.dailyPrice ? Number(form.dailyPrice) : undefined,
        is_24x7: form.is247,
        opening_time: form.is247 ? null : `${form.openTime}:00`,
        closing_time: form.is247 ? null : `${form.closeTime}:00`,
        vehicle_types: form.vehicleTypes,
        amenities: form.amenities.map((a) => a as BackendAmenity),
      };
      const updated = await parkingService.updateParking(parkingId, payload);
      setDto(updated);
      setForm(toForm(updated));
      toast.success("Listing updated");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update listing");
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    setDeleting(true);
    try {
      await parkingService.deleteParking(parkingId);
      toast.success("Listing deleted");
      navigate({ to: "/owner" });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to delete listing");
      setDeleting(false);
    }
  }

  if (loadError) {
    return (
      <div className="space-y-4">
        <Button asChild variant="ghost" size="sm" className="-ml-2">
          <Link to="/owner">
            <ArrowLeft className="mr-1 h-4 w-4" /> Back
          </Link>
        </Button>
        <div className="rounded-xl border border-border bg-card p-8 text-center">
          <h1 className="text-lg font-semibold">Couldn't load listing</h1>
          <p className="mt-2 text-sm text-muted-foreground">{loadError}</p>
        </div>
      </div>
    );
  }

  if (!dto || !form) {
    return (
      <div className="flex justify-center py-20 text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Button asChild variant="ghost" size="sm" className="-ml-2">
        <Link to="/owner">
          <ArrowLeft className="mr-1 h-4 w-4" /> Back to dashboard
        </Link>
      </Button>

      <PageHeader
        title="Edit parking space"
        description="Update your listing details. Verification status is managed by admins."
        actions={
          <Badge variant="outline" className={STATUS_CLASS[dto.status]}>
            {STATUS_LABEL[dto.status]}
          </Badge>
        }
      />

      <div className="space-y-6 rounded-2xl border border-border bg-card p-6 sm:p-8">
        <Field label="Parking name" htmlFor="name">
          <Input id="name" value={form.name} onChange={(e) => update("name", e.target.value)} />
        </Field>
        <Field label="Property type" htmlFor="ptype">
          <Select value={form.propertyType} onValueChange={(v) => update("propertyType", v as PropertyType)}>
            <SelectTrigger id="ptype"><SelectValue /></SelectTrigger>
            <SelectContent>
              {(Object.keys(PROPERTY_LABELS) as PropertyType[]).map((p) => (
                <SelectItem key={p} value={p}>{PROPERTY_LABELS[p]}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
        <Field label="Description" htmlFor="desc">
          <Textarea id="desc" rows={3} value={form.description} onChange={(e) => update("description", e.target.value)} />
        </Field>

        <Separator />

        <Field label="Street address" htmlFor="addr">
          <Input id="addr" value={form.address} onChange={(e) => update("address", e.target.value)} />
        </Field>
        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="City" htmlFor="city">
            <Input id="city" value={form.city} onChange={(e) => update("city", e.target.value)} />
          </Field>
          <Field label="State" htmlFor="state">
            <Input id="state" value={form.state} onChange={(e) => update("state", e.target.value)} />
          </Field>
          <Field label="PIN code" htmlFor="pin">
            <Input id="pin" value={form.pincode} onChange={(e) => update("pincode", e.target.value)} />
          </Field>
        </div>
        <p className="flex items-center gap-1 text-xs text-muted-foreground">
          <MapPin className="h-3 w-3" /> Coordinates: {dto.latitude}, {dto.longitude}
        </p>

        <Separator />

        <div>
          <Label>Supported vehicle types</Label>
          <div className="mt-2 flex flex-wrap gap-2">
            {allVehicles.map((v) => {
              const on = form.vehicleTypes.includes(v);
              return (
                <button
                  key={v}
                  type="button"
                  onClick={() => toggle("vehicleTypes", v)}
                  className={cn(
                    "rounded-full border px-3 py-1.5 text-sm",
                    on ? "border-primary bg-accent text-accent-foreground" : "border-border bg-background",
                  )}
                >
                  {VEHICLE_LABELS[v]}
                </button>
              );
            })}
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="Total slots" htmlFor="slots">
            <Input id="slots" type="number" min={1} value={form.totalSlots}
              onChange={(e) => update("totalSlots", e.target.value)} />
          </Field>
          <Field label="Available slots" htmlFor="avail">
            <Input id="avail" type="number" min={0} value={form.availableSlots}
              onChange={(e) => update("availableSlots", e.target.value)} />
          </Field>
          <Field label="Covered / Open" htmlFor="cov">
            <Select value={form.covered} onValueChange={(v) => update("covered", v as "COVERED" | "OPEN")}>
              <SelectTrigger id="cov"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="COVERED">Covered</SelectItem>
                <SelectItem value="OPEN">Open</SelectItem>
              </SelectContent>
            </Select>
          </Field>
        </div>

        <div>
          <Label>Amenities</Label>
          <div className="mt-2 grid gap-2 sm:grid-cols-2">
            {allAmenities.map((a) => (
              <label key={a} className="flex items-center gap-2 rounded-md border border-border bg-background p-3 text-sm">
                <Checkbox checked={form.amenities.includes(a)} onCheckedChange={() => toggle("amenities", a)} />
                {AMENITY_LABELS[a]}
              </label>
            ))}
          </div>
        </div>

        <Separator />

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Hourly price (₹)" htmlFor="hp">
            <Input id="hp" type="number" min={0} value={form.hourlyPrice}
              onChange={(e) => update("hourlyPrice", e.target.value)} />
          </Field>
          <Field label="Daily price (₹)" htmlFor="dp">
            <Input id="dp" type="number" min={0} value={form.dailyPrice}
              onChange={(e) => update("dailyPrice", e.target.value)} />
          </Field>
        </div>

        <div className="flex items-center justify-between rounded-md border border-border bg-background p-3">
          <div>
            <p className="text-sm font-medium">Open 24×7</p>
            <p className="text-xs text-muted-foreground">Disable to set opening and closing times.</p>
          </div>
          <Switch checked={form.is247} onCheckedChange={(v) => update("is247", v)} />
        </div>
        {!form.is247 && (
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Opening time" htmlFor="ot">
              <Input id="ot" type="time" value={form.openTime} onChange={(e) => update("openTime", e.target.value)} />
            </Field>
            <Field label="Closing time" htmlFor="ct">
              <Input id="ct" type="time" value={form.closeTime} onChange={(e) => update("closeTime", e.target.value)} />
            </Field>
          </div>
        )}

        <Separator />

        <div className="flex flex-wrap items-center justify-between gap-3">
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="outline" className="text-destructive" disabled={deleting}>
                <Trash2 className="mr-1 h-4 w-4" /> Delete listing
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete this listing?</AlertDialogTitle>
                <AlertDialogDescription>
                  This permanently removes “{dto.name}” from ParkShare. This action cannot be undone.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={remove}>Delete</AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>

          <Button onClick={save} disabled={saving}>
            {saving ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <Save className="mr-1 h-4 w-4" />}
            Save changes
          </Button>
        </div>
      </div>
    </div>
  );
}

function Field({ label, htmlFor, children }: { label: string; htmlFor: string; children: React.ReactNode }) {
  return (
    <div>
      <Label htmlFor={htmlFor}>{label}</Label>
      <div className="mt-1.5">{children}</div>
    </div>
  );
}
