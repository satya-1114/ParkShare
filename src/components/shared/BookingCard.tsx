import { Calendar, Clock } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { PriceDisplay } from "./PriceDisplay";
import type { Booking, BookingStatus } from "@/types";

const statusStyles: Record<BookingStatus, string> = {
  ACTIVE: "bg-success/15 text-success-foreground border-success/30",
  UPCOMING: "bg-accent text-accent-foreground border-transparent",
  COMPLETED: "bg-muted text-muted-foreground border-transparent",
  CANCELLED: "bg-destructive/10 text-destructive border-destructive/20",
};

const statusLabels: Record<BookingStatus, string> = {
  ACTIVE: "Active",
  UPCOMING: "Upcoming",
  COMPLETED: "Completed",
  CANCELLED: "Cancelled",
};

export function BookingCard({ booking }: { booking: Booking }) {
  return (
    <article className="rounded-lg border border-border bg-card p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold">{booking.parkingName}</h3>
          <p className="text-xs text-muted-foreground">{booking.area}</p>
        </div>
        <Badge variant="outline" className={statusStyles[booking.status]}>
          {statusLabels[booking.status]}
        </Badge>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
        <Info icon={Calendar} label="Date" value={booking.date} />
        <Info icon={Clock} label="Start" value={booking.startTime} />
        <Info icon={Clock} label="Duration" value={`${booking.durationHours} hr`} />
        <div>
          <p className="text-xs text-muted-foreground">Amount</p>
          <PriceDisplay amount={booking.amount} suffix="" size="sm" />
        </div>
      </div>
    </article>
  );
}

function Info({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
}) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-0.5 flex items-center gap-1 font-medium">
        <Icon className="h-3.5 w-3.5 text-muted-foreground" />
        {value}
      </p>
    </div>
  );
}
