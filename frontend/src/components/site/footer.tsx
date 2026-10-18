import Link from "next/link";

import { Logo } from "./logo";

const COLUMNS = [
  {
    title: "Product",
    links: [
      { href: "/features", label: "Features" },
      { href: "/how-it-works", label: "How it works" },
      { href: "/estimate/new", label: "Start an estimate" },
    ],
  },
  {
    title: "Company",
    links: [
      { href: "/about", label: "About" },
      { href: "/contact", label: "Contact" },
    ],
  },
  {
    title: "Your account",
    links: [
      { href: "/login", label: "Sign in" },
      { href: "/projects", label: "Your estimates" },
      { href: "/settings", label: "Company settings" },
    ],
  },
];

export function Footer() {
  return (
    <footer className="mt-auto border-t bg-card">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-12 sm:px-6 md:grid-cols-[1.4fr_repeat(3,1fr)]">
        <div className="flex max-w-xs flex-col gap-4">
          <Logo />
          <p className="text-sm text-muted-foreground">
            Costs software by what is built, the way it is built today: with AI
            tools, and people who check their work.
          </p>
          {/* the tape, as a quiet signature */}
          <div
            aria-hidden="true"
            className="tape-ticks h-3 w-40 rounded-sm bg-tape"
          />
        </div>
        {COLUMNS.map((col) => (
          <nav
            key={col.title}
            aria-label={col.title}
            className="flex flex-col gap-3"
          >
            <span className="text-sm font-semibold">{col.title}</span>
            {col.links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="w-fit text-sm text-muted-foreground hover:text-foreground"
              >
                {link.label}
              </Link>
            ))}
          </nav>
        ))}
      </div>
      <div className="border-t">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-4 text-xs text-muted-foreground sm:px-6">
          <span>© Aakalan</span>
          <span>
            Estimates are a guide before work starts, not a quote or a bill.
          </span>
        </div>
      </div>
    </footer>
  );
}
