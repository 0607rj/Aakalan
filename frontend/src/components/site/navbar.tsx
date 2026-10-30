"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ListIcon, XIcon } from "@phosphor-icons/react/dist/ssr";

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
 * The signed-in bar: the public site's three white pills (logo, page links, actions) floating
 * over the page and gathering once you scroll. `links` are the page links; `actions` sit on the
 * right (new estimate, profile). On phones the links fold into a menu.
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
  const near = useScrolled();
  const [open, setOpen] = React.useState(false);
  // a new page closes the phone menu (state adjusted while rendering, not in an effect)
  const [shownPath, setShownPath] = React.useState(pathname);
  if (shownPath !== pathname) {
    setShownPath(pathname);
    setOpen(false);
  }

  return (
    <header className="fixed inset-x-0 top-0 z-40">
      <div
        className={cn(
          "pill-nav mx-auto flex items-center justify-between gap-2.5 px-3 py-4 sm:px-7",
          near && "near",
        )}
      >
        <div className={cn(PILL, "py-[7px] pr-4 pl-[7px]")}>
          <Logo href={homeHref} />
        </div>
        <nav
          aria-label="Main"
          className={cn(PILL, "hidden items-center gap-0.5 p-1.5 md:flex")}
        >
          {links.map((link) => (
            <NavItem key={link.href} link={link} pathname={pathname} />
          ))}
        </nav>
        <div className={cn(PILL, "hidden items-center gap-1.5 p-1.5 md:flex")}>
          {note}
          {actions}
        </div>
        <button
          type="button"
          className={cn(
            PILL,
            "inline-flex size-12 items-center justify-center md:hidden",
          )}
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
        <div id="mobile-menu" className={cn(PILL, "mx-3 p-2 md:hidden")}>
          <nav aria-label="Main" className="flex flex-col gap-0.5">
            {links.map((link) => (
              <NavItem key={link.href} link={link} pathname={pathname} />
            ))}
          </nav>
          <div className="mt-2 flex flex-wrap items-center gap-2 border-t border-black/10 px-1 pt-2">
            {note}
            {actions}
          </div>
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
        "rounded-[11px] px-4 py-2.5 text-[15px] transition-colors",
        active
          ? "bg-muted text-foreground"
          : "text-foreground/80 hover:bg-black/5",
      )}
    >
      {link.label}
    </Link>
  );
}

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

/** Whether the page has been scrolled away from its top. */
function useScrolled(): boolean {
  return React.useSyncExternalStore(
    (onChange) => {
      window.addEventListener("scroll", onChange, { passive: true });
      return () => window.removeEventListener("scroll", onChange);
    },
    () => window.scrollY > 60,
    () => false,
  );
}

const PILL =
  "rounded-2xl bg-white text-foreground shadow-[0_8px_24px_-12px_rgb(0_0_0/0.3)]";

/**
 * Public pages: three white pills floating over the page (the logo, the page links, sign in /
 * sign up or "Your estimates"). At the top they spread across the page; once you scroll they
 * slide in towards each other (`.pill-nav.near`), and back out at the top. The current page's
 * link is lit. On phones the links fold into a menu.
 */
export function SiteNavBar() {
  const signedIn = useSignedIn();
  const near = useScrolled();
  const pathname = usePathname();
  const [open, setOpen] = React.useState(false);
  // a new page closes the phone menu (state adjusted while rendering, not in an effect)
  const [shownPath, setShownPath] = React.useState(pathname);
  if (shownPath !== pathname) {
    setShownPath(pathname);
    setOpen(false);
  }

  const actions = signedIn ? (
    <Link
      href="/projects"
      className="rounded-[11px] bg-foreground px-3.5 py-2.5 text-[15px] font-medium text-white"
    >
      Your estimates
    </Link>
  ) : (
    <>
      <Link
        href="/login"
        className="rounded-[11px] px-3.5 py-2.5 text-[15px] font-medium hover:bg-black/5"
      >
        Sign in
      </Link>
      <Link
        href="/signup"
        className="rounded-[11px] bg-foreground px-3.5 py-2.5 text-[15px] font-medium text-white"
      >
        Sign up
      </Link>
    </>
  );

  return (
    <header className="fixed inset-x-0 top-0 z-40">
      <div
        className={cn(
          "pill-nav mx-auto flex items-center justify-between gap-2.5 px-3 py-4 sm:px-7",
          near && "near",
        )}
      >
        <div className={cn(PILL, "py-[7px] pr-4 pl-[7px]")}>
          <Logo />
        </div>
        <nav
          aria-label="Main"
          className={cn(PILL, "hidden items-center gap-0.5 p-1.5 md:flex")}
        >
          {SITE_LINKS.map((link) => {
            const active =
              pathname === link.href || pathname.startsWith(`${link.href}/`);
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "rounded-[11px] px-4 py-2.5 text-[15px] transition-colors",
                  active
                    ? "bg-muted text-foreground"
                    : "text-foreground/80 hover:bg-black/5",
                )}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
        <div className={cn(PILL, "hidden items-center gap-1 p-1.5 md:flex")}>
          {actions}
        </div>
        <button
          type="button"
          className={cn(
            PILL,
            "inline-flex size-12 items-center justify-center md:hidden",
          )}
          aria-expanded={open}
          aria-controls="site-menu"
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
        <div id="site-menu" className={cn(PILL, "mx-3 p-2 md:hidden")}>
          <nav aria-label="Main" className="flex flex-col gap-0.5">
            {SITE_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                aria-current={pathname === link.href ? "page" : undefined}
                className={cn(
                  "rounded-xl px-4 py-3 text-[15px]",
                  pathname === link.href && "bg-muted",
                )}
              >
                {link.label}
              </Link>
            ))}
          </nav>
          <div className="mt-2 flex items-center gap-1 border-t border-black/10 pt-2">
            {actions}
          </div>
        </div>
      ) : null}
    </header>
  );
}
