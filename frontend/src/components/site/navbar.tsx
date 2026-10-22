"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { buttonVariants } from "@/components/ui/button";
import { getToken } from "@/lib/api/client";
import { cn } from "@/lib/utils";

import { Logo } from "./logo";

export const SITE_LINKS = [
  { href: "/features", label: "Features" },
  { href: "/how-it-works", label: "How it works" },
  { href: "/about", label: "About" },
  { href: "/contact", label: "Contact" },
];

export interface NavLink {
  href: string;
  label: string;
}

/**
 * The bar on every page. `links` are the page links; `actions` sit on the right (sign in,
 * start an estimate, log out). On phones the links fold into a menu.
 */
export function NavBar({
  links,
  actions,
  homeHref = "/",
  note,
}: {
  links: NavLink[];
  actions: React.ReactNode;
  homeHref?: string;
  note?: React.ReactNode;
}) {
  const pathname = usePathname();
  const [open, setOpen] = React.useState(false);
  // a new page closes the phone menu (state adjusted while rendering, not in an effect)
  const [shownPath, setShownPath] = React.useState(pathname);
  if (shownPath !== pathname) {
    setShownPath(pathname);
    setOpen(false);
  }

  return (
    <header className="sticky top-0 z-40 border-b bg-background/90 backdrop-blur supports-[backdrop-filter]:bg-background/75">
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-6 px-4 sm:px-6">
        <Logo href={homeHref} />
        <nav aria-label="Main" className="hidden items-center gap-1 md:flex">
          {links.map((link) => (
            <NavItem key={link.href} link={link} pathname={pathname} />
          ))}
        </nav>
        <div className="ml-auto hidden items-center gap-2 md:flex">
          {note}
          {actions}
        </div>
        <button
          type="button"
          className="ml-auto inline-flex size-10 items-center justify-center rounded-full border md:hidden"
          aria-expanded={open}
          aria-controls="mobile-menu"
          aria-label={open ? "Close menu" : "Open menu"}
          onClick={() => setOpen((v) => !v)}
        >
          <svg viewBox="0 0 24 24" className="size-5" aria-hidden="true">
            {open ? (
              <path
                d="M6 6l12 12M18 6L6 18"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            ) : (
              <path
                d="M4 7h16M4 12h16M4 17h10"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            )}
          </svg>
        </button>
      </div>
      {open ? (
        <div id="mobile-menu" className="border-t bg-background md:hidden">
          <nav
            aria-label="Main"
            className="mx-auto flex max-w-6xl flex-col gap-1 px-4 py-3"
          >
            {links.map((link) => (
              <NavItem key={link.href} link={link} pathname={pathname} />
            ))}
            <div className="mt-2 flex flex-wrap items-center gap-2 border-t pt-3">
              {note}
              {actions}
            </div>
          </nav>
        </div>
      ) : null}
    </header>
  );
}

function NavItem({ link, pathname }: { link: NavLink; pathname: string }) {
  const active = pathname === link.href || pathname.startsWith(`${link.href}/`);
  return (
    <Link
      href={link.href}
      aria-current={active ? "page" : undefined}
      className={cn(
        "rounded-full px-3 py-2 text-sm font-medium transition-colors",
        active
          ? "bg-foreground/[0.06] text-foreground"
          : "text-muted-foreground hover:text-foreground",
      )}
    >
      {link.label}
    </Link>
  );
}

/** Public pages: the site links, and sign in / start (or "Your estimates" once signed in). */
/** Whether a sign-in token is stored (re-read when another tab signs in or out). */
function useSignedIn(): boolean {
  return React.useSyncExternalStore(
    (onChange) => {
      window.addEventListener("storage", onChange);
      return () => window.removeEventListener("storage", onChange);
    },
    () => getToken() !== null,
    () => false, // the server cannot see the browser's storage
  );
}

export function SiteNavBar() {
  const signedIn = useSignedIn();
  return (
    <NavBar
      links={SITE_LINKS}
      actions={
        signedIn ? (
          <Link
            href="/projects"
            className={buttonVariants({ size: "default" })}
          >
            Your estimates
          </Link>
        ) : (
          <>
            <Link
              href="/login"
              className={buttonVariants({ variant: "ghost" })}
            >
              Sign in
            </Link>
            <Link
              href="/signup"
              className={buttonVariants({ size: "default" })}
            >
              Sign up
            </Link>
          </>
        )
      }
    />
  );
}
