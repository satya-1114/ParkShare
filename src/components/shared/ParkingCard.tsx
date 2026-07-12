import { Link } from "@tanstack/react-router";
import { MapPin, Star } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PriceDisplay } from "./PriceDisplay";
import { TrustBadge } from "./TrustBadge";
import { AmenityBadge } from "./AmenityBadge";
import { VEHICLE_LABELS } from "@/constants/parking";
import type { ParkingSpace } from "@/types";

export function ParkingCard({ space }: { space: ParkingSpace }) {
  return (
    <article className="group overflow-hidden rounded-xl border border-border bg-card transition-shadow hover:shadow-md">
      <div className="relative aspect-[16/10] overflow-hidden bg-muted">
        <img
          src={space.imageUrl}
          alt={space.name}
          loading="lazy"
          className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
        />
        {space.verified && (
          <div className="absolute left-3 top-3">
            <TrustBadge />
          </div>
        )}
        <div className="absolute right-3 top-3 rounded-full bg-background/90 px-2 py-0.5 text-xs font-medium backdrop-blur">
          {space.totalSlots} {space.totalSlots === 1 ? "slot" : "slots"}
        </div>
      </div>
      <div className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="truncate text-base font-semibold">{space.name}</h3>
            <p className="mt-0.5 flex items-center gap-1 text-xs text-muted-foreground">
              <MapPin className="h-3 w-3" />
              {space.area}, {space.city} · {space.distanceKm.toFixed(1)} km
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-1 text-sm">
            <Star className="h-3.5 w-3.5 fill-warning text-warning" />
            <span className="font-medium">{space.rating.toFixed(1)}</span>
            <span className="text-xs text-muted-foreground">({space.reviewCount})</span>
          </div>
        </div>

        <div className="mt-3 flex flex-wrap gap-1.5">
          {space.amenities.slice(0, 3).map((a) => (
            <AmenityBadge key={a} amenity={a} />
          ))}
        </div>

        <p className="mt-3 text-xs text-muted-foreground">
          Fits: {space.vehicleTypes.map((v) => VEHICLE_LABELS[v]).join(", ")}
        </p>

        <div className="mt-4 flex items-center justify-between">
          <PriceDisplay amount={space.hourlyPrice} />
          <Button asChild size="sm">
            <Link to="/driver/parking/$parkingId" params={{ parkingId: space.id }}>
              View Details
            </Link>
          </Button>
        </div>
      </div>
    </article>
  );
}
