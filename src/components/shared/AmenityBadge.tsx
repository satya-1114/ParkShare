import { cn } from "@/lib/utils";
import { AMENITY_LABELS } from "@/constants/parking";
import type { ParkingAmenity } from "@/types";
import {
  Camera,
  Shield,
  Zap,
  Umbrella,
  Clock,
  type LucideIcon,
} from "lucide-react";

const iconMap: Record<ParkingAmenity, LucideIcon> = {
  CCTV: Camera,
  SECURITY: Shield,
  EV_CHARGING: Zap,
  COVERED: Umbrella,
  ACCESS_24X7: Clock,
};

export function AmenityBadge({
  amenity,
  className,
}: {
  amenity: ParkingAmenity;
  className?: string;
}) {
  const Icon = iconMap[amenity];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md border border-border bg-background px-2 py-1 text-xs text-muted-foreground",
        className,
      )}
    >
      <Icon className="h-3 w-3" />
      {AMENITY_LABELS[amenity]}
    </span>
  );
}
