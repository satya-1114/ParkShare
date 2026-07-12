import { Link } from "@tanstack/react-router";
import { Logo } from "@/components/brand/Logo";

const cols = [
  {
    title: "Product",
    links: [
      { label: "Find Parking", to: "/driver/search" },
      { label: "List Your Space", to: "/owner" },
      { label: "How It Works", to: "/" },
    ],
  },
  {
    title: "For Drivers",
    links: [
      { label: "Search", to: "/driver/search" },
      { label: "My Bookings", to: "/driver/bookings" },
      { label: "Dashboard", to: "/driver" },
    ],
  },
  {
    title: "For Hosts",
    links: [
      { label: "Owner Dashboard", to: "/owner" },
      { label: "Add a Space", to: "/owner/parking/new" },
      { label: "Get Started", to: "/register" },
    ],
  },
  {
    title: "Support",
    links: [
      { label: "Help Center", to: "/" },
      { label: "Trust & Safety", to: "/" },
      { label: "Contact", to: "/" },
    ],
  },
];

export function PublicFooter() {
  return (
    <footer className="border-t border-border bg-surface">
      <div className="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8">
        <div className="grid gap-10 md:grid-cols-5">
          <div className="md:col-span-1">
            <Logo />
            <p className="mt-4 text-sm text-muted-foreground">
              A trusted community marketplace for private parking spaces.
            </p>
          </div>
          {cols.map((col) => (
            <div key={col.title}>
              <h4 className="text-sm font-semibold text-foreground">{col.title}</h4>
              <ul className="mt-4 space-y-2">
                {col.links.map((l) => (
                  <li key={l.label}>
                    <Link
                      to={l.to}
                      className="text-sm text-muted-foreground hover:text-foreground"
                    >
                      {l.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="mt-12 flex flex-col items-start justify-between gap-3 border-t border-border pt-6 text-xs text-muted-foreground sm:flex-row sm:items-center">
          <p>© {new Date().getFullYear()} ParkShare. All rights reserved.</p>
          <div className="flex gap-4">
            <Link to="/" className="hover:text-foreground">Terms</Link>
            <Link to="/" className="hover:text-foreground">Privacy</Link>
            <Link to="/" className="hover:text-foreground">Cookies</Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
