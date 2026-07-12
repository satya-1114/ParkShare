import { cn } from "@/lib/utils";

interface PriceDisplayProps {
  amount: number;
  suffix?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function PriceDisplay({
  amount,
  suffix = "/hr",
  size = "md",
  className,
}: PriceDisplayProps) {
  const sizes = {
    sm: "text-sm",
    md: "text-lg",
    lg: "text-2xl",
  };
  return (
    <span className={cn("font-semibold text-foreground", sizes[size], className)}>
      <span className="mr-0.5">₹</span>
      {amount.toLocaleString("en-IN")}
      {suffix && (
        <span className="ml-1 text-xs font-normal text-muted-foreground">{suffix}</span>
      )}
    </span>
  );
}
