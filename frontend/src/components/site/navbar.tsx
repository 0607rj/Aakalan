"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ListIcon, XIcon } from "@phosphor-icons/react/dist/ssr";

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
    <header className="sticky top-0 z-40 px-3 pt-3 sm:px-4">
      <div className="mx-auto max-w-6xl rounded-2xl border border-foreground/[0.08] bg-background/80 shadow-[0_1px_0_rgb(255_255_255/0.7)_inset,0_12px_32px_-20px_rgb(27_36_51/0.35)] backdrop-blur-md supports-[backdrop-filter]:bg-background/70">
        <div className="flex h-14 items-center gap-6 pr-2 pl-4">
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
            className="ml-auto inline-flex size-10 items-center justify-center rounded-xl md:hidden"
            aria-expanded={open}
            aria-controls="mobile-menu"
            aria-label={open ? "Close menu" : "Open menu"}
            onClick={() => setOpen((v) => !v)}
          >
            {open ? (
              <XIcon size={20} weight="bold" aria-hidden="true" />
            ) : (
              <ListIcon size={20} weight="bold" aria-hidden="true" />
            )}
          </button>
        </div>
        {open ? (
          <div id="mobile-menu" className="border-t md:hidden">
            <nav aria-label="Main" className="flex flex-col gap-1 px-2 py-3">
              {links.map((link) => (
                <NavItem key={link.href} link={link} pathname={pathname} />
              ))}
              <div className="mt-2 flex flex-wrap items-center gap-2 border-t px-1 pt-3">
                {note}
                {actions}
              </div>
            </nav>
          </div>
        ) : null}
      </div>
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
        "rounded-lg px-3 py-2 text-sm font-medium transition-colors",
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
