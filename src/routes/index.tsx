import { createFileRoute, Link } from "@tanstack/react-router";
import {
  ShieldCheck,
  Users,
  Wallet,
  Search,
  MapPin,
  Car,
  Sparkles,
  Navigation,
  Lock,
  ArrowRight,
} from "lucide-react";
import { PublicNavbar } from "@/components/layout/PublicNavbar";
import { PublicFooter } from "@/components/layout/PublicFooter";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export const Route = createFileRoute("/")({
  component: LandingPage,
});

function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <PublicNavbar />
      <main className="flex-1">
        <Hero />
        <TrustIndicators />
        <HowItWorks />
        <Features />
        <OwnerCTA />
      </main>
      <PublicFooter />
    </div>
  );
}

function Hero() {
  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-surface to-background">
      <div className="mx-auto max-w-7xl px-4 pb-20 pt-16 sm:px-6 lg:px-8 lg:pt-24">
        <div className="grid items-center gap-12 lg:grid-cols-[1.15fr_1fr]">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full border border-border bg-background px-3 py-1 text-xs font-medium text-muted-foreground">
              <Sparkles className="h-3 w-3 text-primary" />
              A community marketplace for private parking
            </span>
            <h1 className="mt-5 font-display text-4xl font-bold leading-[1.1] tracking-tight sm:text-5xl lg:text-6xl">
              Find a trusted parking spot.
              <br />
              <span className="text-primary">Right when you need it.</span>
            </h1>
            <p className="mt-5 max-w-xl text-base text-muted-foreground sm:text-lg">
              Drivers discover and reserve unused private parking spaces nearby.
              Owners earn from spaces they're not using. All backed by ParkShare's
              community trust signals.
            </p>

            <form
              onSubmit={(e) => e.preventDefault()}
              className="mt-8 flex flex-col gap-2 rounded-xl border border-border bg-card p-2 shadow-sm sm:flex-row"
            >
              <div className="flex flex-1 items-center gap-2 rounded-lg bg-background px-3">
                <MapPin className="h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Enter a location, area or landmark"
                  className="border-0 shadow-none focus-visible:ring-0"
                  aria-label="Search location"
                />
              </div>
              <Button size="lg" type="submit">
                <Search className="mr-1 h-4 w-4" />
                Find Parking
              </Button>
            </form>
            <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
              <span>Popular:</span>
              {["Indiranagar", "Nariman Point", "Anna Nagar", "Sector 29"].map((c) => (
                <span
                  key={c}
                  className="rounded-full border border-border bg-background px-2 py-0.5"
                >
                  {c}
                </span>
              ))}
            </div>
            <div className="mt-6 flex flex-wrap gap-3">
              <Button asChild variant="outline" size="lg">
                <Link to="/owner">List Your Space</Link>
              </Button>
              <Button asChild variant="ghost" size="lg">
                <Link to="/" hash="how-it-works">
                  How it works <ArrowRight className="ml-1 h-4 w-4" />
                </Link>
              </Button>
            </div>
          </div>

          <div className="relative">
            <div className="absolute -inset-4 rounded-3xl bg-primary/10 blur-3xl" aria-hidden />
            <div className="relative overflow-hidden rounded-2xl border border-border bg-card shadow-xl">
              <img
                src="https://images.unsplash.com/photo-1590674899484-d5640e854abe?w=1200&q=80"
                alt="Private covered parking inside a gated community"
                className="aspect-[4/3] w-full object-cover"
              />
              <div className="grid grid-cols-3 divide-x divide-border border-t border-border bg-background">
                <MiniStat label="Trust Score" value="92/100" />
                <MiniStat label="Verified hosts" value="Yes" />
                <MiniStat label="From" value="₹30/hr" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="px-3 py-3 text-center">
      <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-semibold">{value}</p>
    </div>
  );
}

function TrustIndicators() {
  const items = [
    { icon: ShieldCheck, title: "Verified parking spaces", text: "Every listing is reviewed before it goes live." },
    { icon: Users, title: "Trusted community hosts", text: "Real people, identity-verified profiles." },
    { icon: Wallet, title: "Transparent pricing", text: "See the exact hourly price. No hidden fees." },
  ];
  return (
    <section className="border-y border-border bg-background">
      <div className="mx-auto grid max-w-7xl gap-6 px-4 py-10 sm:grid-cols-3 sm:px-6 lg:px-8">
        {items.map((it) => (
          <div key={it.title} className="flex items-start gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-foreground">
              <it.icon className="h-5 w-5" />
            </span>
            <div>
              <p className="font-semibold">{it.title}</p>
              <p className="mt-1 text-sm text-muted-foreground">{it.text}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function HowItWorks() {
  const drivers = [
    { n: "1", title: "Search nearby", text: "Enter your destination and see private spaces around you." },
    { n: "2", title: "Choose a trusted space", text: "Compare trust scores, amenities and prices." },
    { n: "3", title: "Reserve your spot", text: "Book in a few taps and drive up with confidence." },
  ];
  const owners = [
    { n: "1", title: "List your parking space", text: "Add photos, describe the space and set access rules." },
    { n: "2", title: "Set availability and price", text: "Choose the hours you're available and your rate." },
    { n: "3", title: "Earn from unused space", text: "Turn an idle driveway or slot into recurring income." },
  ];

  return (
    <section id="how-it-works" className="bg-surface">
      <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="font-display text-3xl font-bold sm:text-4xl">How ParkShare works</h2>
          <p className="mt-3 text-muted-foreground">
            A simple, trustworthy path for both sides of the marketplace.
          </p>
        </div>

        <div className="mt-12 grid gap-8 lg:grid-cols-2">
          <FlowCard title="For drivers" steps={drivers} accent="For drivers" />
          <FlowCard title="For hosts" steps={owners} accent="For hosts" />
        </div>
      </div>
    </section>
  );
}

function FlowCard({
  title,
  steps,
  accent,
}: {
  title: string;
  steps: { n: string; title: string; text: string }[];
  accent: string;
}) {
  return (
    <div className="rounded-2xl border border-border bg-card p-8">
      <p className="text-xs font-medium uppercase tracking-wide text-primary">{accent}</p>
      <h3 className="mt-2 font-display text-2xl font-bold">{title}</h3>
      <ol className="mt-6 space-y-5">
        {steps.map((s) => (
          <li key={s.n} className="flex gap-4">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-navy text-sm font-semibold text-navy-foreground">
              {s.n}
            </span>
            <div>
              <p className="font-semibold">{s.title}</p>
              <p className="mt-1 text-sm text-muted-foreground">{s.text}</p>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}

function Features() {
  const features = [
    { icon: MapPin, title: "Nearby parking discovery", text: "Find private spaces just steps from your destination." },
    { icon: ShieldCheck, title: "Verified & trusted", text: "Each space is verified and rated by real drivers." },
    { icon: Car, title: "Flexible reservations", text: "Book by the hour, day or in advance." },
    { icon: Wallet, title: "Transparent pricing", text: "See prices in ₹ before you book. Nothing hidden." },
    { icon: Navigation, title: "Easy navigation", text: "Directions and access notes shared with every booking." },
    { icon: Lock, title: "Secure experience", text: "Trust scores, host verification and clear booking rules." },
  ];
  return (
    <section className="bg-background">
      <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8">
        <div className="max-w-2xl">
          <h2 className="font-display text-3xl font-bold sm:text-4xl">
            Built for the way people actually park.
          </h2>
          <p className="mt-3 text-muted-foreground">
            Every feature is designed to make private parking feel as reliable as
            a hotel booking.
          </p>
        </div>
        <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => (
            <div
              key={f.title}
              className="rounded-xl border border-border bg-card p-6 transition-shadow hover:shadow-sm"
            >
              <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent text-accent-foreground">
                <f.icon className="h-5 w-5" />
              </span>
              <h3 className="mt-4 font-semibold">{f.title}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{f.text}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function OwnerCTA() {
  return (
    <section className="bg-navy text-navy-foreground">
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-20 sm:px-6 lg:grid-cols-2 lg:items-center lg:px-8">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-primary">
            For property owners
          </p>
          <h2 className="mt-2 font-display text-3xl font-bold sm:text-4xl">
            Turn your unused parking into a steady income.
          </h2>
          <p className="mt-4 max-w-lg text-navy-foreground/80">
            Whether it's a driveway at home, a slot in your apartment tower or an
            empty spot at your office — list it in minutes and earn from drivers
            who need it most.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Button asChild size="lg" variant="secondary">
              <Link to="/owner">List Your Space</Link>
            </Button>
            <Button asChild size="lg" variant="ghost" className="text-navy-foreground hover:bg-white/10">
              <Link to="/register">Create a host account</Link>
            </Button>
          </div>
        </div>

        <ul className="grid gap-3 sm:grid-cols-2">
          {[
            "Set your own hourly and daily price",
            "Choose the days and hours you're available",
            "Verified drivers only",
            "Full visibility on every booking",
          ].map((t) => (
            <li
              key={t}
              className="flex items-start gap-2 rounded-lg border border-white/10 bg-white/5 p-4 text-sm"
            >
              <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
              {t}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
