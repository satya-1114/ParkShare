import { useEffect, useState } from "react";
import { createFileRoute, Link, notFound, useNavigate } from "@tanstack/react-router";
import { ArrowLeft, MapPin, Calendar, Clock, Timer, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Progress } from "@/components/ui/progress";
import { PriceDisplay } from "@/components/shared/PriceDisplay";
import { TrustBadge } from "@/components/shared/TrustBadge";
import { AmenityBadge } from "@/components/shared/AmenityBadge";
import { PROPERTY_LABELS, VEHICLE_LABELS } from "@/constants/parking";
import { parkingService, toParkingSpace, type ParkingDTO } from "@/services/parkingService";
import { bookingService } from "@/services/bookingService";
import { aiService, type TrustExplanationResponse } from "@/services/aiService";
import { useAuth } from "@/contexts/AuthContext";
import type { ParkingSpace } from "@/types";

export const Route = createFileRoute("/driver/parking/$parkingId")({
  loader: async ({ params }) => {
    try {
      const dto = await parkingService.getParking(params.parkingId);
      return { dto, space: toParkingSpace(dto) };
    } catch {
      throw notFound();
    }
  },
  component: ParkingDetailsPage,
  notFoundComponent: () => <NotFound />,
});

function NotFound() {
  return (
    <div className="text-center">
      <h1 className="text-xl font-semibold">Parking space not found</h1>
      <p className="mt-2 text-sm text-muted-foreground">The space you're looking for isn't available.</p>
      <Button asChild className="mt-4">
        <Link to="/driver/search">Back to search</Link>
      </Button>
    </div>
  );
}

function ParkingDetailsPage() {
  const { dto, space } = Route.useLoaderData() as { dto: ParkingDTO; space: ParkingSpace };
  const gallery = [space.imageUrl, space.imageUrl, space.imageUrl];

  const [trust, setTrust] = useState<TrustExplanationResponse | null>(null);
  const [trustLoading, setTrustLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const result = await aiService.getTrustExplanation(dto.id);
        if (!cancelled) setTrust(result);
      } catch {
        // non-fatal — don't break the page
      } finally {
        if (!cancelled) setTrustLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [dto.id]);

  return (
    <div className="space-y-6">
      <Button asChild variant="ghost" size="sm" className="-ml-2">
        <Link to="/driver/search">
          <ArrowLeft className="mr-1 h-4 w-4" />
          Back to results
        </Link>
      </Button>

      <div className="grid gap-2 overflow-hidden rounded-2xl sm:grid-cols-[2fr_1fr]">
        <img src={gallery[0]} alt={space.name} className="aspect-[16/10] h-full w-full object-cover" />
        <div className="hidden grid-rows-2 gap-2 sm:grid">
          <img src={gallery[1]} alt="" className="h-full w-full object-cover" />
          <img src={gallery[2]} alt="" className="h-full w-full object-cover" />
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-[1fr_360px]">
        <div className="space-y-8">
          <header>
            <div className="flex flex-wrap items-center gap-2">
              {space.verified && <TrustBadge />}
              <span className="rounded-full bg-muted px-2 py-0.5 text-xs">
                {space.propertyType && PROPERTY_LABELS[space.propertyType]}
              </span>
              {trustLoading ? (
                <span className="rounded-full border border-border bg-background px-2 py-0.5 text-xs text-muted-foreground">
                  Loading trust…
                </span>
              ) : trust ? (
                <span className="rounded-full border border-border bg-background px-2 py-0.5 text-xs text-muted-foreground">
                  Trust score: {trust.trust_score}/100
                </span>
              ) : null}
            </div>
            <h1 className="mt-2 font-display text-3xl font-bold">{space.name}</h1>
            <p className="mt-1 flex items-center gap-2 text-sm text-muted-foreground">
              <MapPin className="h-4 w-4" />
              {space.area}, {space.city}
            </p>
          </header>

          <section>
            <h2 className="font-semibold">Supported vehicles</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              {space.vehicleTypes.length
                ? space.vehicleTypes.map((v) => VEHICLE_LABELS[v]).join(" · ")
                : "Not specified"}
            </p>
          </section>

          <section>
            <h2 className="font-semibold">Amenities</h2>
            <div className="mt-3 flex flex-wrap gap-2">
              {space.amenities.length ? (
                space.amenities.map((a) => <AmenityBadge key={a} amenity={a} />)
              ) : (
                <p className="text-sm text-muted-foreground">No amenities listed</p>
              )}
            </div>
          </section>

          {space.description && (
            <section>
              <h2 className="font-semibold">About this space</h2>
              <p className="mt-2 text-sm text-muted-foreground">{space.description}</p>
            </section>
          )}

          {/* Trust Score Section */}
          {trustLoading ? (
            <section className="rounded-xl border border-dashed border-border bg-surface p-5 text-sm text-muted-foreground">
              Loading trust data…
            </section>
          ) : trust ? (
            <TrustScorePanel trust={trust} />
          ) : null}
        </div>

        <aside className="lg:sticky lg:top-24 lg:self-start">
          <BookingWidget parkingId={dto.id} hourlyPrice={Number(dto.hourly_price)} />
        </aside>
      </div>
    </div>
  );
}

function TrustScorePanel({ trust }: { trust: TrustExplanationResponse }) {
  return (
    <section className="rounded-xl border border-border bg-card p-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-accent text-accent-foreground">
            <ShieldCheck className="h-4 w-4" />
          </span>
          <div>
            <p className="text-sm font-semibold">ParkShare Trust Score</p>
            <p className="text-xs text-muted-foreground">Verified marketplace signal</p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-2xl font-bold text-foreground">
            {trust.trust_score}
            <span className="text-sm font-normal text-muted-foreground">/100</span>
          </p>
        </div>
      </div>
      <Progress value={trust.trust_score} className="mt-4 h-2" />
      <ul className="mt-4 grid gap-2 text-sm">
        <TrustFactor label="Listing Verified" ok={trust.factors.listing_verified} />
        <TrustFactor label="Parking Photos Verified" ok={trust.factors.photos_verified} />
        <TrustFactor label="Owner ID Verified" ok={trust.factors.owner_id_verified} />
        <TrustFactor label="Owner Phone Verified" ok={trust.factors.owner_phone_verified} />
        <TrustFactor
          label={`Completed Bookings (${trust.factors.completed_bookings})`}
          ok={trust.factors.has_completed_bookings}
        />
      </ul>
      <p className="mt-4 text-sm text-muted-foreground">{trust.explanation}</p>
      {trust.ai_generated && (
        <p className="mt-2 text-xs text-muted-foreground">Explanation by IBM Granite</p>
      )}
    </section>
  );
}

function TrustFactor({ label, ok }: { label: string; ok: boolean }) {
  return (
    <li className="flex items-center gap-2 text-muted-foreground">
      <span
        className={`flex h-4 w-4 items-center justify-center rounded-full text-[10px] ${
          ok ? "bg-success text-success-foreground" : "bg-muted text-muted-foreground"
        }`}
      >
        {ok ? "✓" : "–"}
      </span>
      <span className={ok ? "text-foreground" : ""}>{label}</span>
    </li>
  );
}

interface BookingWidgetProps {
  parkingId: string;
  hourlyPrice: number;
}

function BookingWidget({ parkingId, hourlyPrice }: BookingWidgetProps) {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const today = new Date();
  const defaultDate = today.toISOString().slice(0, 10);
  const [date, setDate] = useState(defaultDate);
  const [startTime, setStartTime] = useState("10:00");
  const [duration, setDuration] = useState(3);
  const [submitting, setSubmitting] = useState(false);
  const total = hourlyPrice * duration;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!isAuthenticated) {
      toast.error("Sign in to book a parking space");
      navigate({ to: "/login" });
      return;
    }
    try {
      setSubmitting(true);
      const start = new Date(`${date}T${startTime}:00`);
      const end = new Date(start.getTime() + duration * 60 * 60 * 1000);
      const booking = await bookingService.createBooking({
        parking_id: parkingId,
        start_time: start.toISOString(),
        end_time: end.toISOString(),
      });
      toast.success(`Booking confirmed — ${booking.booking_reference}`);
      navigate({ to: "/driver/bookings" });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Booking failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} className="rounded-xl border border-border bg-card p-5 shadow-sm">
      <div className="flex items-baseline justify-between">
        <PriceDisplay amount={hourlyPrice} size="lg" />
        <span className="text-xs text-muted-foreground">Best hourly rate</span>
      </div>
      <Separator className="my-4" />
      <div className="space-y-3">
        <Field icon={Calendar} label="Date" htmlFor="d">
          <Input id="d" type="date" value={date} min={defaultDate}
            onChange={(e) => setDate(e.target.value)}
            className="border-0 shadow-none focus-visible:ring-0" />
        </Field>
        <Field icon={Clock} label="Start time" htmlFor="t">
          <Input id="t" type="time" value={startTime}
            onChange={(e) => setStartTime(e.target.value)}
            className="border-0 shadow-none focus-visible:ring-0" />
        </Field>
        <Field icon={Timer} label="Duration" htmlFor="dur">
          <select id="dur" value={duration} onChange={(e) => setDuration(Number(e.target.value))}
            className="w-full bg-transparent text-sm outline-none">
            {[1, 2, 3, 4, 6, 8, 12].map((h) => (
              <option key={h} value={h}>{h} hr</option>
            ))}
          </select>
        </Field>
      </div>
      <div className="mt-4 rounded-md bg-muted p-3 text-sm">
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground">Estimated total</span>
          <PriceDisplay amount={total} suffix="" size="md" />
        </div>
      </div>
      <Button type="submit" className="mt-4 w-full" size="lg" disabled={submitting}>
        {submitting ? "Reserving…" : "Reserve Parking"}
      </Button>
      <p className="mt-2 text-center text-xs text-muted-foreground">
        You won't be charged yet.
      </p>
    </form>
  );
}

interface FieldProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  htmlFor: string;
  children: React.ReactNode;
}

function Field({ icon: Icon, label, htmlFor, children }: FieldProps) {
  return (
    <div className="rounded-md border border-border bg-background px-3 py-2">
      <Label htmlFor={htmlFor} className="flex items-center gap-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        <Icon className="h-3 w-3" />
        {label}
      </Label>
      <div className="mt-0.5">{children}</div>
    </div>
  );
}
