import { useState } from "react";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { Check, ChevronLeft, ChevronRight, Loader2, Sparkles, Upload } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { AMENITY_LABELS, VEHICLE_LABELS, PROPERTY_LABELS } from "@/constants/parking";
import type { ParkingAmenity, PropertyType, VehicleType } from "@/types";
import {
  parkingService,
  type BackendAmenity,
  type BackendVehicleType,
} from "@/services/parkingService";
import { aiService, type PriceSuggestionResponse } from "@/services/aiService";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/owner/parking/new")({
  component: AddParkingPage,
});

const steps = [
  "Basic Information",
  "Location",
  "Parking Details",
  "Pricing",
  "Photos",
  "Availability",
  "Review",
];

interface FormState {
  name: string;
  propertyType: PropertyType | "";
  description: string;
  address: string;
  city: string;
  state: string;
  pincode: string;
  vehicleTypes: VehicleType[];
  totalSlots: string;
  covered: "COVERED" | "OPEN";
  amenities: ParkingAmenity[];
  hourlyPrice: string;
  dailyPrice: string;
  photos: string[];
  days: string[];
  openTime: string;
  closeTime: string;
  is247: boolean;
}

const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const allAmenities: ParkingAmenity[] = ["CCTV", "COVERED", "SECURITY", "EV_CHARGING", "ACCESS_24X7"];
const allVehicles: VehicleType[] = ["BIKE", "CAR", "EV", "TRUCK", "BICYCLE"];

function toBackendVehicle(v: VehicleType): BackendVehicleType {
  // Frontend and backend vehicle enums are aligned — pass through.
  return v;
}
function toBackendAmenity(a: ParkingAmenity): BackendAmenity {
  return a as BackendAmenity;
}


function AddParkingPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [priceSuggesting, setPriceSuggesting] = useState(false);
  const [priceSuggestion, setPriceSuggestion] = useState<PriceSuggestionResponse | null>(null);
  const [priceError, setPriceError] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>({
    name: "",
    propertyType: "",
    description: "",
    address: "",
    city: "",
    state: "",
    pincode: "",
    vehicleTypes: [],
    totalSlots: "1",
    covered: "OPEN",
    amenities: [],
    hourlyPrice: "",
    dailyPrice: "",
    photos: [],
    days: ["Mon", "Tue", "Wed", "Thu", "Fri"],
    openTime: "08:00",
    closeTime: "20:00",
    is247: false,
  });

  const update = <K extends keyof FormState>(k: K, v: FormState[K]) =>
    setForm((f) => ({ ...f, [k]: v }));

  type ArrayFields = {
    [K in keyof FormState]: FormState[K] extends readonly unknown[] ? K : never;
  }[keyof FormState];

  const toggle = <K extends ArrayFields>(k: K, value: FormState[K][number]) =>
    setForm((f) => {
      const list = f[k] as ReadonlyArray<FormState[K][number]>;
      const next = list.includes(value)
        ? list.filter((x) => x !== value)
        : [...list, value];
      return { ...f, [k]: next as FormState[K] };
    });

  async function submit() {
    if (!form.propertyType) {
      toast.error("Select a property type");
      setStep(0);
      return;
    }
    if (!/^\d{6}$/.test(form.pincode)) {
      toast.error("PIN code must be 6 digits");
      setStep(1);
      return;
    }
    const total = Number(form.totalSlots);
    const hourly = Number(form.hourlyPrice);
    if (!Number.isFinite(total) || total <= 0) {
      toast.error("Total slots must be greater than 0");
      setStep(2);
      return;
    }
    if (!Number.isFinite(hourly) || hourly < 0) {
      toast.error("Enter a valid hourly price");
      setStep(3);
      return;
    }
    setSubmitting(true);
    try {
      await parkingService.createParking({
        name: form.name,
        description: form.description || undefined,
        property_type: form.propertyType as PropertyType,
        address: form.address,
        city: form.city,
        state: form.state,
        pin_code: form.pincode,
        latitude: 0,
        longitude: 0,
        total_slots: total,
        available_slots: total,
        parking_type: form.covered,
        hourly_price: hourly,
        daily_price: form.dailyPrice ? Number(form.dailyPrice) : undefined,
        is_24x7: form.is247,
        opening_time: form.is247 ? null : `${form.openTime}:00`,
        closing_time: form.is247 ? null : `${form.closeTime}:00`,
        vehicle_types: form.vehicleTypes.map(toBackendVehicle),
        amenities: form.amenities.map(toBackendAmenity),
        image_urls: [],
      });
      toast.success("Parking submitted — pending verification");
      navigate({ to: "/owner" });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to create listing");
    } finally {
      setSubmitting(false);
    }
  }

  async function suggestPrice() {
    if (!form.city) {
      toast.error("Enter a city first (Location step)");
      return;
    }
    setPriceSuggesting(true);
    setPriceError(null);
    setPriceSuggestion(null);
    try {
      const result = await aiService.getPriceSuggestion({
        city: form.city,
        state: form.state || "Unknown",
        parking_type: form.covered,
        amenities: form.amenities,
        vehicle_types: form.vehicleTypes,
        total_slots: Number(form.totalSlots) || 1,
        is_24x7: form.is247,
      });
      setPriceSuggestion(result);
    } catch (err) {
      setPriceError(err instanceof Error ? err.message : "Could not get suggestion");
    } finally {
      setPriceSuggesting(false);
    }
  }

  const canSuggestPrice = Boolean(form.city && form.vehicleTypes.length > 0);

  return (
    <div className="space-y-8">
      <PageHeader
        title="Add a parking space"
        description="Share the details, availability and price. You can edit anything later."
        actions={
          <Button asChild variant="ghost">
            <Link to="/owner">Cancel</Link>
          </Button>
        }
      />

      <Stepper current={step} />

      <div className="rounded-2xl border border-border bg-card p-6 sm:p-8">
        {step === 0 && (
          <Section title="Basic information">
            <Field label="Parking name" htmlFor="pname">
              <Input id="pname" placeholder="e.g. Green Meadows Residency" value={form.name}
                onChange={(e) => update("name", e.target.value)} />
            </Field>
            <Field label="Property type" htmlFor="ptype">
              <Select value={form.propertyType} onValueChange={(v) => update("propertyType", v as PropertyType)}>
                <SelectTrigger id="ptype"><SelectValue placeholder="Select property type" /></SelectTrigger>
                <SelectContent>
                  {(Object.keys(PROPERTY_LABELS) as PropertyType[]).map((p) => (
                    <SelectItem key={p} value={p}>{PROPERTY_LABELS[p]}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <Field label="Description" htmlFor="pdesc">
              <Textarea id="pdesc" rows={4} placeholder="Describe access, landmarks and anything drivers should know."
                value={form.description} onChange={(e) => update("description", e.target.value)} />
            </Field>
          </Section>
        )}

        {step === 1 && (
          <Section title="Location">
            <Field label="Street address" htmlFor="addr">
              <Input id="addr" placeholder="Building name, street, area" value={form.address}
                onChange={(e) => update("address", e.target.value)} />
            </Field>
            <div className="grid gap-4 sm:grid-cols-3">
              <Field label="City" htmlFor="city">
                <Input id="city" placeholder="Bengaluru" value={form.city} onChange={(e) => update("city", e.target.value)} />
              </Field>
              <Field label="State" htmlFor="state">
                <Input id="state" placeholder="Karnataka" value={form.state} onChange={(e) => update("state", e.target.value)} />
              </Field>
              <Field label="PIN code" htmlFor="pin">
                <Input id="pin" placeholder="560038" value={form.pincode} onChange={(e) => update("pincode", e.target.value)} />
              </Field>
            </div>
            <div className="rounded-lg border border-dashed border-border bg-surface p-8 text-center text-sm text-muted-foreground">
              Map location picker will be added in a later phase.
            </div>
          </Section>
        )}

        {step === 2 && (
          <Section title="Parking details">
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
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Total slots" htmlFor="slots">
                <Input id="slots" type="number" min={1} value={form.totalSlots}
                  onChange={(e) => update("totalSlots", e.target.value)} />
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
          </Section>
        )}

        {step === 3 && (
          <Section title="Pricing">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Hourly price (₹)" htmlFor="hp">
                <Input id="hp" type="number" min={0} placeholder="40" value={form.hourlyPrice}
                  onChange={(e) => update("hourlyPrice", e.target.value)} />
              </Field>
              <Field label="Daily price (₹)" htmlFor="dp">
                <Input id="dp" type="number" min={0} placeholder="320" value={form.dailyPrice}
                  onChange={(e) => update("dailyPrice", e.target.value)} />
              </Field>
            </div>
            <div className="rounded-lg border border-border bg-surface p-4 space-y-3">
              <div className="flex items-start gap-3">
                <span className="flex h-8 w-8 items-center justify-center rounded-md bg-muted text-muted-foreground">
                  <Sparkles className="h-4 w-4" />
                </span>
                <div className="flex-1">
                  <p className="font-medium">Get smart price suggestion</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {canSuggestPrice
                      ? "Based on comparable listings in your city."
                      : "Complete city and vehicle types first."}
                  </p>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  disabled={!canSuggestPrice || priceSuggesting}
                  onClick={suggestPrice}
                >
                  {priceSuggesting ? (
                    <><Loader2 className="mr-1 h-4 w-4 animate-spin" /> Suggesting…</>
                  ) : (
                    "Suggest price"
                  )}
                </Button>
              </div>
              {priceError && (
                <p className="text-sm text-muted-foreground">{priceError}</p>
              )}
              {priceSuggestion && (
                <div className="rounded-md border border-border bg-background p-3 space-y-2">
                  {priceSuggestion.suggested_hourly_price && (
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Suggested hourly price</span>
                      <span className="text-base font-bold">
                        ₹{priceSuggestion.suggested_hourly_price}
                      </span>
                    </div>
                  )}
                  {priceSuggestion.price_range && (
                    <p className="text-xs text-muted-foreground">
                      Market range: ₹{priceSuggestion.price_range.min}–₹{priceSuggestion.price_range.max}
                      {" "}(median ₹{priceSuggestion.price_range.median})
                    </p>
                  )}
                  <p className="text-xs text-muted-foreground">{priceSuggestion.explanation}</p>
                  {priceSuggestion.suggested_hourly_price && (
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => update("hourlyPrice", String(priceSuggestion.suggested_hourly_price))}
                    >
                      Use suggested price
                    </Button>
                  )}
                  {priceSuggestion.ai_generated && (
                    <p className="text-xs text-muted-foreground">Powered by IBM Granite</p>
                  )}
                </div>
              )}
            </div>
          </Section>
        )}

        {step === 4 && (
          <Section title="Photos">
            <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-border bg-surface p-10 text-center">
              <Upload className="h-6 w-6 text-muted-foreground" />
              <p className="font-medium">Upload parking photos</p>
              <p className="text-sm text-muted-foreground">PNG or JPG · up to 8 photos</p>
              <input type="file" multiple accept="image/*" className="hidden" />
            </label>
          </Section>
        )}

        {step === 5 && (
          <Section title="Availability">
            <div>
              <Label>Available days</Label>
              <div className="mt-2 flex flex-wrap gap-2">
                {days.map((d) => {
                  const on = form.days.includes(d);
                  return (
                    <button
                      key={d}
                      type="button"
                      onClick={() => toggle("days", d)}
                      className={cn(
                        "rounded-md border px-3 py-1.5 text-sm",
                        on ? "border-primary bg-accent text-accent-foreground" : "border-border bg-background",
                      )}
                    >
                      {d}
                    </button>
                  );
                })}
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Opening time" htmlFor="ot">
                <Input id="ot" type="time" value={form.openTime} onChange={(e) => update("openTime", e.target.value)} disabled={form.is247} />
              </Field>
              <Field label="Closing time" htmlFor="ct">
                <Input id="ct" type="time" value={form.closeTime} onChange={(e) => update("closeTime", e.target.value)} disabled={form.is247} />
              </Field>
            </div>
            <label className="flex items-center justify-between rounded-md border border-border bg-background p-3 text-sm">
              <span>Available 24×7</span>
              <Switch checked={form.is247} onCheckedChange={(v) => update("is247", v)} />
            </label>
          </Section>
        )}

        {step === 6 && (
          <Section title="Review your listing">
            <dl className="grid gap-3 sm:grid-cols-2">
              <Row label="Name" value={form.name || "—"} />
              <Row label="Property type" value={form.propertyType ? PROPERTY_LABELS[form.propertyType] : "—"} />
              <Row label="Address" value={[form.address, form.city, form.state, form.pincode].filter(Boolean).join(", ") || "—"} />
              <Row label="Total slots" value={form.totalSlots} />
              <Row label="Vehicle types" value={form.vehicleTypes.map((v) => VEHICLE_LABELS[v]).join(", ") || "—"} />
              <Row label="Amenities" value={form.amenities.map((a) => AMENITY_LABELS[a]).join(", ") || "—"} />
              <Row label="Hourly price" value={form.hourlyPrice ? `₹${form.hourlyPrice}` : "—"} />
              <Row label="Daily price" value={form.dailyPrice ? `₹${form.dailyPrice}` : "—"} />
              <Row label="Availability" value={form.is247 ? "24×7" : `${form.days.join(", ")} · ${form.openTime}–${form.closeTime}`} />
            </dl>
            <p className="text-xs text-muted-foreground">
              This preview is local to the form. Submission will be enabled in a later phase.
            </p>
          </Section>
        )}

        <div className="mt-8 flex items-center justify-between border-t border-border pt-6">
          <Button
            variant="outline"
            disabled={step === 0}
            onClick={() => setStep((s) => Math.max(0, s - 1))}
          >
            <ChevronLeft className="mr-1 h-4 w-4" /> Back
          </Button>
          {step < steps.length - 1 ? (
            <Button onClick={() => setStep((s) => Math.min(steps.length - 1, s + 1))}>
              Continue <ChevronRight className="ml-1 h-4 w-4" />
            </Button>
          ) : (
            <Button onClick={submit} disabled={submitting}>
              {submitting ? "Publishing…" : "Publish listing"}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

function Stepper({ current }: { current: number }) {
  return (
    <ol className="flex flex-wrap items-center gap-2">
      {steps.map((s, i) => {
        const done = i < current;
        const active = i === current;
        return (
          <li key={s} className="flex items-center gap-2">
            <span
              className={cn(
                "flex h-7 w-7 items-center justify-center rounded-full text-xs font-medium",
                done && "bg-primary text-primary-foreground",
                active && "bg-navy text-navy-foreground",
                !done && !active && "bg-muted text-muted-foreground",
              )}
            >
              {done ? <Check className="h-3.5 w-3.5" /> : i + 1}
            </span>
            <span className={cn("text-xs sm:text-sm", active ? "font-semibold text-foreground" : "text-muted-foreground")}>
              {s}
            </span>
            {i < steps.length - 1 && <span className="mx-1 h-px w-4 bg-border sm:w-6" aria-hidden />}
          </li>
        );
      })}
    </ol>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-5">
      <h2 className="font-display text-xl font-semibold">{title}</h2>
      {children}
    </div>
  );
}

function Field({ label, htmlFor, children }: { label: string; htmlFor?: string; children: React.ReactNode }) {
  return (
    <div>
      <Label htmlFor={htmlFor}>{label}</Label>
      <div className="mt-1.5">{children}</div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-background p-3">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-0.5 text-sm font-medium">{value}</dd>
    </div>
  );
}
