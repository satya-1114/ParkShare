import { ParkingSquare } from "lucide-react";
import { Link } from "@tanstack/react-router";
import { cn } from "@/lib/utils";

interface LogoProps {
  className?: string;
  variant?: "default" | "light";
  withText?: boolean;
}

export function Logo({ className, variant = "default", withText = true }: LogoProps) {
  const textColor = variant === "light" ? "text-white" : "text-navy";
  return (
    <Link to="/" className={cn("inline-flex items-center gap-2", className)}>
      <span
        className={cn(
          "flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground shadow-sm",
        )}
        aria-hidden
      >
        <ParkingSquare className="h-5 w-5" />
      </span>
      {withText && (
        <span className={cn("font-display text-lg font-bold tracking-tight", textColor)}>
          ParkShare
        </span>
      )}
    </Link>
  );
}
