import { MapPin, Calendar, Clock, Timer, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

interface SearchBarProps {
  className?: string;
  /** Controlled city value. When provided the input is controlled. */
  city?: string;
  onCityChange?: (city: string) => void;
  onSubmit?: (city: string) => void;
  variant?: "hero" | "card";
}

export function SearchBar({
  className,
  city,
  onCityChange,
  onSubmit,
  variant = "card",
}: SearchBarProps) {
  const isControlled = city !== undefined;

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (onSubmit) {
          const formData = new FormData(e.currentTarget);
          const val = isControlled ? (city ?? "") : String(formData.get("loc") ?? "");
          onSubmit(val.trim());
        }
      }}
      className={cn(
        "rounded-xl border border-border bg-card p-4 shadow-sm",
        variant === "hero" && "shadow-lg",
        className,
      )}
    >
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-[2fr_1fr_1fr_1fr_auto]">
        <Field icon={MapPin} label="Destination" htmlFor="loc">
          <Input
            id="loc"
            name="loc"
            placeholder="Search location or landmark"
            className="border-0 shadow-none focus-visible:ring-0"
            value={isControlled ? (city ?? "") : undefined}
            onChange={isControlled ? (e) => onCityChange?.(e.target.value) : undefined}
          />
        </Field>
        <Field icon={Calendar} label="Date" htmlFor="date">
          <Input id="date" type="date" className="border-0 shadow-none focus-visible:ring-0" />
        </Field>
        <Field icon={Clock} label="Start" htmlFor="time">
          <Input id="time" type="time" defaultValue="10:00" className="border-0 shadow-none focus-visible:ring-0" />
        </Field>
        <Field icon={Timer} label="Duration" htmlFor="dur">
          <select
            id="dur"
            className="w-full bg-transparent text-sm outline-none"
            defaultValue="2"
          >
            {[1, 2, 3, 4, 6, 8, 12, 24].map((h) => (
              <option key={h} value={h}>
                {h} hr
              </option>
            ))}
          </select>
        </Field>
        <Button type="submit" size="lg" className="lg:self-end">
          <Search className="mr-1 h-4 w-4" />
          Find Parking
        </Button>
      </div>
    </form>
  );
}

function Field({
  icon: Icon,
  label,
  htmlFor,
  children,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  htmlFor: string;
  children: React.ReactNode;
}) {
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
