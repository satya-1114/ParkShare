import { useEffect, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { List, Map as MapIcon, MapPin, SlidersHorizontal, Sparkles, Loader2 } from "lucide-react";
import { SearchBar } from "@/components/shared/SearchBar";
import { FilterPanel, type FilterState } from "@/components/shared/FilterPanel";
import { ParkingCard } from "@/components/shared/ParkingCard";
import { EmptyState } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { parkingService, toParkingSpace, type BackendAmenity } from "@/services/parkingService";
import { aiService, type RankedParking } from "@/services/aiService";
import { cn } from "@/lib/utils";
import type { ParkingAmenity, ParkingSpace, VehicleType } from "@/types";

export const Route = createFileRoute("/driver/search")({
  component: SearchPage,
});

/** Single source of truth for all search/filter context on this page.
 *  Used by both normal parking search and Smart Recommendations. */
interface SearchContext {
  city: string;
  filters: FilterState;
}

const DEFAULT_FILTERS: FilterState = {
  vehicleType: null,
  amenities: [],
  minPrice: null,
  maxPrice: null,
};

function SearchPage() {
  const [mobileView, setMobileView] = useState<"list" | "map">("list");

  // ── Shared search context ─────────────────────────────────────────────────
  const [searchCtx, setSearchCtx] = useState<SearchContext>({
    city: "",
    filters: DEFAULT_FILTERS,
  });
  const [spaces, setSpaces] = useState<ParkingSpace[] | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);

  // ── AI recommendations state ──────────────────────────────────────────────
  const [aiLoading, setAiLoading] = useState(false);
  const [aiRecs, setAiRecs] = useState<RankedParking[] | null>(null);
  const [aiGenerated, setAiGenerated] = useState(false);
  const [aiSpaces, setAiSpaces] = useState<Map<string, ParkingSpace>>(new Map());
  const [aiError, setAiError] = useState<string | null>(null);
  const [showAi, setShowAi] = useState(false);

  // ── Normal search (runs on mount + whenever context changes) ─────────────
  useEffect(() => {
    let cancelled = false;
    (async () => {
      setSpaces(null);
      setSearchError(null);
      try {
        const res = await parkingService.searchParkings({
          city: searchCtx.city || undefined,
          vehicle_type: (searchCtx.filters.vehicleType as VehicleType) || undefined,
          amenity: searchCtx.filters.amenities[0] as BackendAmenity | undefined,
          min_price: searchCtx.filters.minPrice ?? undefined,
          max_price: searchCtx.filters.maxPrice ?? undefined,
          page: 1,
          page_size: 30,
        });
        if (!cancelled) setSpaces(res.items.map(toParkingSpace));
      } catch (err) {
        if (!cancelled) {
          setSearchError(
            err instanceof Error ? err.message : "Failed to load parking spaces",
          );
          setSpaces([]);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [searchCtx]);

  function handleCityChange(city: string) {
    setSearchCtx((prev) => ({ ...prev, city }));
  }

  function handleSearchSubmit(city: string) {
    setSearchCtx((prev) => ({ ...prev, city }));
  }

  function handleFilterChange(filters: FilterState) {
    setSearchCtx((prev) => ({ ...prev, filters }));
    // Dismiss any stale AI panel when filters change
    setShowAi(false);
    setAiRecs(null);
  }

  // ── Smart Recommendations ─────────────────────────────────────────────────
  async function handleSmartRecommendations() {
    setAiLoading(true);
    setAiError(null);
    setShowAi(true);
    try {
      const result = await aiService.getRecommendations({
        city: searchCtx.city || undefined,
        vehicle_type: searchCtx.filters.vehicleType || undefined,
        max_hourly_price: searchCtx.filters.maxPrice ?? undefined,
        preferred_amenities: searchCtx.filters.amenities.length > 0
          ? (searchCtx.filters.amenities as ParkingAmenity[])
          : undefined,
        preference_context: "",
      });
      setAiRecs(result.recommendations);
      setAiGenerated(result.ai_generated);

      // Build a lookup of ParkingSpace objects for each recommendation
      const map = new Map<string, ParkingSpace>();
      for (const rec of result.recommendations) {
        try {
          const dto = await parkingService.getParking(rec.parking_id);
          map.set(rec.parking_id, toParkingSpace(dto));
        } catch {
          // skip unavailable spaces
        }
      }
      setAiSpaces(map);
    } catch (err) {
      setAiError(
        err instanceof Error ? err.message : "Could not load recommendations",
      );
    } finally {
      setAiLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <SearchBar
        city={searchCtx.city}
        onCityChange={handleCityChange}
        onSubmit={handleSearchSubmit}
      />

      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          <span className="font-medium text-foreground">
            {spaces === null ? "…" : `${spaces.length} spaces`}
          </span>{" "}
          near your search
        </p>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleSmartRecommendations}
            disabled={aiLoading}
          >
            {aiLoading ? (
              <Loader2 className="mr-1 h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="mr-1 h-4 w-4" />
            )}
            Smart Recommendations
          </Button>
          <Sheet>
            <SheetTrigger asChild>
              <Button variant="outline" size="sm" className="lg:hidden">
                <SlidersHorizontal className="mr-1 h-4 w-4" /> Filters
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-[320px] p-0">
              <SheetHeader className="border-b border-border p-4">
                <SheetTitle>Filters</SheetTitle>
              </SheetHeader>
              <div className="p-4">
                <FilterPanel
                  value={searchCtx.filters}
                  onChange={handleFilterChange}
                />
              </div>
            </SheetContent>
          </Sheet>
          <div className="flex overflow-hidden rounded-md border border-border lg:hidden">
            <ViewBtn
              active={mobileView === "list"}
              onClick={() => setMobileView("list")}
              icon={List}
              label="List"
            />
            <ViewBtn
              active={mobileView === "map"}
              onClick={() => setMobileView("map")}
              icon={MapIcon}
              label="Map"
            />
          </div>
        </div>
      </div>

      {/* AI Recommendations Panel */}
      {showAi && (
        <div className="rounded-xl border border-border bg-surface p-4">
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-semibold">Smart Recommendations</span>
              {aiGenerated && (
                <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                  Powered by IBM Granite
                </span>
              )}
            </div>
            <button
              type="button"
              onClick={() => setShowAi(false)}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              Dismiss
            </button>
          </div>

          {aiLoading && (
            <div className="flex justify-center py-6 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          )}

          {aiError && (
            <p className="py-4 text-center text-sm text-muted-foreground">
              {aiError}
            </p>
          )}

          {!aiLoading && !aiError && aiRecs !== null && (
            aiRecs.length === 0 ? (
              <p className="py-4 text-center text-sm text-muted-foreground">
                No recommendations available right now.
              </p>
            ) : (
              <div className="space-y-4">
                {aiRecs.map((rec) => {
                  const space = aiSpaces.get(rec.parking_id);
                  if (!space) return null;
                  return (
                    <div key={rec.parking_id} className="space-y-1.5">
                      <ParkingCard space={space} />
                      <p className="px-1 text-xs text-muted-foreground">
                        <span className="font-medium text-foreground">
                          Why recommended:
                        </span>{" "}
                        {rec.reason}
                      </p>
                    </div>
                  );
                })}
              </div>
            )
          )}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[280px_1fr_minmax(0,420px)]">
        <aside className="hidden lg:block">
          <FilterPanel
            value={searchCtx.filters}
            onChange={handleFilterChange}
          />
        </aside>

        <div className={cn("space-y-4", mobileView === "map" && "hidden lg:block")}>
          {spaces === null ? (
            <div className="flex justify-center py-16 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          ) : searchError ? (
            <EmptyState
              icon={MapPin}
              title="Couldn't load parking spaces"
              description={searchError}
            />
          ) : spaces.length === 0 ? (
            <EmptyState
              icon={MapPin}
              title="No verified parking spaces yet"
              description="Check back soon — new listings are being verified."
            />
          ) : (
            spaces.map((s) => <ParkingCard key={s.id} space={s} />)
          )}
        </div>

        <div
          className={cn(
            "lg:sticky lg:top-24 lg:self-start",
            mobileView === "list" && "hidden lg:block",
          )}
        >
          <MapPlaceholder />
        </div>
      </div>
    </div>
  );
}

interface ViewBtnProps {
  active: boolean;
  onClick: () => void;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
}

function ViewBtn({ active, onClick, icon: Icon, label }: ViewBtnProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex items-center gap-1 px-3 py-1.5 text-xs font-medium",
        active ? "bg-navy text-navy-foreground" : "bg-background text-muted-foreground",
      )}
    >
      <Icon className="h-3.5 w-3.5" />
      {label}
    </button>
  );
}

function MapPlaceholder() {
  return (
    <div className="relative aspect-square overflow-hidden rounded-xl border border-border bg-[radial-gradient(circle_at_30%_30%,var(--color-accent),var(--color-surface))] lg:aspect-auto lg:h-[calc(100vh-11rem)]">
      <div
        className="absolute inset-0 opacity-40"
        style={{
          backgroundImage:
            "linear-gradient(var(--color-border) 1px, transparent 1px), linear-gradient(90deg, var(--color-border) 1px, transparent 1px)",
          backgroundSize: "32px 32px",
        }}
        aria-hidden
      />
      <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 p-6 text-center">
        <span className="flex h-10 w-10 items-center justify-center rounded-full bg-background/80 text-primary backdrop-blur">
          <MapPin className="h-5 w-5" />
        </span>
        <p className="font-semibold">Interactive map preview</p>
        <p className="max-w-xs text-sm text-muted-foreground">
          Live map integration will be connected in a later phase.
        </p>
      </div>
    </div>
  );
}
