import Link from "next/link";
import {
  ArrowUpIcon,
  EnvelopeSimpleIcon,
  UserIcon,
} from "@phosphor-icons/react/dist/ssr";

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
      { href: "/signup", label: "Create an account" },
      { href: "/projects", label: "Your estimates" },
    ],
  },
];

/** The round buttons at the bottom right: real places, no social accounts. */
const ROUND = [
  { href: "/contact", label: "Contact", icon: EnvelopeSimpleIcon },
  { href: "/login", label: "Sign in", icon: UserIcon },
  { href: "#", label: "Back to top", icon: ArrowUpIcon },
];

/**
 * The footer, after the reference the user picked: a large logo with one line and an email box
 * that starts an account, the links in columns under plain headings, then a rule with the small
 * print and round buttons.
 */
export function Footer() {
  return (
    <footer className="page-wrap mt-auto pt-20 pb-10">
      <div className="grid gap-12 lg:grid-cols-[1.5fr_1fr_1fr_1fr] lg:gap-8">
        <div className="flex flex-col">
          <Logo large className="w-fit" />
          <h2 className="font-wide mt-10 text-[1.6rem] leading-tight">
            Price your next software project
          </h2>
          <p className="mt-2.5 max-w-[26rem] text-[17px] text-muted-foreground">
            Every feature priced the way teams build today, with AI tools.
          </p>
          <form
            action="/signup"
            className="mt-7 flex flex-col gap-3 sm:flex-row sm:items-center"
          >
            <label htmlFor="footer-email" className="sr-only">
              Your email
            </label>
            <input
              id="footer-email"
              name="email"
              type="email"
              autoComplete="email"
              placeholder="Enter your email"
              className="h-[52px] w-full rounded-full bg-black/[0.06] px-6 text-[16px] outline-none placeholder:text-faint focus-visible:ring-2 focus-visible:ring-ring sm:max-w-[18rem]"
            />
            <button
              type="submit"
              className="h-[52px] shrink-0 rounded-full bg-foreground px-8 text-[16px] font-medium text-white transition-transform hover:-translate-y-px"
            >
              Get started
            </button>
          </form>
        </div>
        {COLUMNS.map((col) => (
          <nav
            key={col.title}
            aria-label={col.title}
            className="flex flex-col gap-3.5"
          >
            <span className="mb-3 text-[17px] font-medium">{col.title}</span>
            {col.links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="w-fit text-[17px] text-muted-foreground transition-colors hover:text-foreground"
              >
                {link.label}
              </Link>
            ))}
          </nav>
        ))}
      </div>
      <div className="mt-16 flex flex-col-reverse items-center gap-5 border-t pt-8 sm:flex-row sm:justify-between">
        <p className="text-center text-[15px] text-muted-foreground sm:text-left">
          <span className="text-foreground">© Aakalan</span> · Estimates are a
          guide before work starts, not a quote or a bill.
        </p>
        <div className="flex gap-2.5">
          {ROUND.map((r) => (
            <Link
              key={r.label}
              href={r.href}
              aria-label={r.label}
              className="grid size-9 place-items-center rounded-full bg-black/[0.07] text-foreground transition-colors hover:bg-black/[0.12]"
            >
              <r.icon size={16} weight="bold" aria-hidden="true" />
            </Link>
          ))}
        </div>
      </div>
    </footer>
  );
}
