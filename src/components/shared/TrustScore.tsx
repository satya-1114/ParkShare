import { ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import { Progress } from "@/components/ui/progress";

interface TrustScoreProps {
  score: number;
  factors?: {
    identityVerified: boolean;
    photosVerified: boolean;
    positiveHistory: boolean;
    customerRatings: number;
  };
  className?: string;
}

export function TrustScore({ score, factors, className }: TrustScoreProps) {
  return (
    <div className={cn("rounded-lg border border-border bg-card p-5", className)}>
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
            {score}
            <span className="text-sm font-normal text-muted-foreground">/100</span>
          </p>
        </div>
      </div>
      <Progress value={score} className="mt-4 h-2" />
      {factors && (
        <ul className="mt-4 grid gap-2 text-sm">
          <Factor label="Identity Verified" ok={factors.identityVerified} />
          <Factor label="Parking Photos Verified" ok={factors.photosVerified} />
          <Factor label="Positive Booking History" ok={factors.positiveHistory} />
          <Factor
            label={`Customer Ratings (${factors.customerRatings.toFixed(1)})`}
            ok={factors.customerRatings >= 4}
          />
        </ul>
      )}
    </div>
  );
}

function Factor({ label, ok }: { label: string; ok: boolean }) {
  return (
    <li className="flex items-center gap-2 text-muted-foreground">
      <span
        className={cn(
          "flex h-4 w-4 items-center justify-center rounded-full text-[10px]",
          ok ? "bg-success text-success-foreground" : "bg-muted text-muted-foreground",
        )}
      >
        {ok ? "✓" : "–"}
      </span>
      <span className={ok ? "text-foreground" : ""}>{label}</span>
    </li>
  );
}
