import { ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";

export function TrustBadge({ className, label = "Verified" }: { className?: string; label?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full bg-accent px-2 py-0.5 text-xs font-medium text-accent-foreground",
        className,
      )}
    >
      <ShieldCheck className="h-3 w-3" />
      {label}
    </span>
  );
}
