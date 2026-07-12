import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Separator } from "@/components/ui/separator";
import { AMENITY_LABELS, VEHICLE_LABELS } from "@/constants/parking";
import type { ParkingAmenity, VehicleType } from "@/types";

const ALL_AMENITIES: ParkingAmenity[] = ["COVERED", "CCTV", "SECURITY", "EV_CHARGING", "ACCESS_24X7"];
const ALL_VEHICLES: VehicleType[] = ["BIKE", "CAR", "EV", "TRUCK", "BICYCLE"];

export interface FilterState {
  vehicleType: VehicleType | null;
  amenities: ParkingAmenity[];
  minPrice: number | null;
  maxPrice: number | null;
}

interface FilterPanelProps {
  /** When provided, the panel operates in controlled mode. */
  value?: FilterState;
  onChange?: (next: FilterState) => void;
}

export function FilterPanel({ value, onChange }: FilterPanelProps) {
  const isControlled = value !== undefined && onChange !== undefined;

  function toggleVehicle(v: VehicleType) {
    if (!isControlled) return;
    onChange!({
      ...value!,
      vehicleType: value!.vehicleType === v ? null : v,
    });
  }

  function toggleAmenity(a: ParkingAmenity) {
    if (!isControlled) return;
    const current = value!.amenities;
    onChange!({
      ...value!,
      amenities: current.includes(a)
        ? current.filter((x) => x !== a)
        : [...current, a],
    });
  }

  function handlePriceChange(vals: number[]) {
    if (!isControlled) return;
    onChange!({
      ...value!,
      minPrice: vals[0] ?? null,
      maxPrice: vals[1] ?? null,
    });
  }

  const selectedVehicle = isControlled ? value!.vehicleType : null;
  const selectedAmenities = isControlled ? value!.amenities : [];
  const minPrice = isControlled ? (value!.minPrice ?? 0) : 0;
  const maxPrice = isControlled ? (value!.maxPrice ?? 500) : 500;

  return (
    <div className="space-y-6 rounded-xl border border-border bg-card p-5">
      <div>
        <h4 className="text-sm font-semibold">Price per hour</h4>
        <div className="mt-4 px-1">
          <Slider
            value={[minPrice, maxPrice]}
            onValueChange={handlePriceChange}
            min={0}
            max={500}
            step={10}
          />
          <div className="mt-2 flex justify-between text-xs text-muted-foreground">
            <span>₹{minPrice}</span>
            <span>₹{maxPrice}</span>
          </div>
        </div>
      </div>
      <Separator />
      <div>
        <h4 className="text-sm font-semibold">Distance</h4>
        <div className="mt-4 px-1">
          <Slider defaultValue={[5]} min={0.5} max={20} step={0.5} />
          <p className="mt-2 text-xs text-muted-foreground">Within 5 km</p>
        </div>
      </div>
      <Separator />
      <div>
        <h4 className="text-sm font-semibold">Vehicle type</h4>
        <div className="mt-3 space-y-2">
          {ALL_VEHICLES.map((v) => (
            <label key={v} className="flex items-center gap-2 text-sm cursor-pointer">
              <Checkbox
                id={`v-${v}`}
                checked={selectedVehicle === v}
                onCheckedChange={() => toggleVehicle(v)}
              />
              <Label htmlFor={`v-${v}`} className="font-normal cursor-pointer">
                {VEHICLE_LABELS[v]}
              </Label>
            </label>
          ))}
        </div>
      </div>
      <Separator />
      <div>
        <h4 className="text-sm font-semibold">Amenities</h4>
        <div className="mt-3 space-y-2">
          {ALL_AMENITIES.map((a) => (
            <label key={a} className="flex items-center gap-2 text-sm cursor-pointer">
              <Checkbox
                id={`a-${a}`}
                checked={selectedAmenities.includes(a)}
                onCheckedChange={() => toggleAmenity(a)}
              />
              <Label htmlFor={`a-${a}`} className="font-normal cursor-pointer">
                {AMENITY_LABELS[a]}
              </Label>
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}
