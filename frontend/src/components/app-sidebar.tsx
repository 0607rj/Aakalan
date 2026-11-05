"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  ListBulletsIcon,
  ListIcon,
  PlusIcon,
  QuestionIcon,
  ShieldCheckIcon,
  SignOutIcon,
  UserIcon,
  XIcon,
} from "@phosphor-icons/react/dist/ssr";
import type { Icon } from "@phosphor-icons/react";

import { useCurrentUser } from "@/components/auth-guard";
import { LogoMark } from "@/components/site/logo";
import { clearToken, type CurrentUser } from "@/lib/api/client";
import { cn } from "@/lib/utils";

type NavLink = {
  href: string;
  label: string;
  icon: Icon;
  /** Whether this link is the page being shown. */
  on: (path: string) => boolean;
  ownerOnly?: boolean;
};

const LINKS: NavLink[] = [
  {
    href: "/projects",
    label: "Your estimates",
    icon: ListBulletsIcon,
    // the list, an estimate's result page and its expert view
    on: (p) =>
      p.startsWith("/projects") ||
      (p.startsWith("/estimate/") && !p.startsWith("/estimate/new")),
  },
  {
    href: "/account",
    label: "Account",
    icon: UserIcon,
    on: (p) => p.startsWith("/account"),
  },
  {
    href: "/admin",
    label: "Admin",
    icon: ShieldCheckIcon,
    on: (p) => p.startsWith("/admin"),
    ownerOnly: true,
  },
  {
    href: "/how-it-works",
    label: "How it works",
    icon: QuestionIcon,
    on: () => false,
  },
];

/** Up to two letters from the name (else the email) for the round badge. */
function initials(user: CurrentUser): string {
  const words = user.full_name.trim().split(/\s+/).filter(Boolean);
  const letters = words.length
    ? words.length > 1
      ? words[0][0] + words[words.length - 1][0]
      : words[0][0]
    : user.email[0];
  return letters.toUpperCase();
}

function Brand({ onClick }: { onClick?: () => void }) {
  return (
    <Link
      href="/projects"
      onClick={onClick}
      aria-label="Aakalan home"
      className="flex items-center gap-2.5 rounded-lg px-2"
    >
      <LogoMark />
      <span className="flex flex-col leading-none">
        <span className="font-head text-[1.15rem] font-semibold tracking-[-0.02em]">
          Aakalan
        </span>
        <span className="mt-[3px] text-[11px] leading-[1.55] text-white/55">
          आकलन
        </span>
      </span>
    </Link>
  );
}

/** The sidebar's content: logo, New estimate, the pages, and who is signed in. */
function SideContent({ onPick }: { onPick?: () => void }) {
  const user = useCurrentUser();
  const path = usePathname();
  const router = useRouter();

  function logout() {
    clearToken();
    router.replace("/login");
  }

  return (
    <div className="flex h-full flex-col gap-1.5">
      <div className="pb-5">
        <Brand onClick={onPick} />
      </div>
      <Link
        href="/estimate/new"
        onClick={onPick}
        className={cn(
          "mb-4 flex items-center justify-center gap-2 rounded-full bg-white px-4 py-3 font-semibold text-[#141414] transition-transform hover:-translate-y-px",
          path.startsWith("/estimate/new") &&
            "ring-2 ring-tape-bright ring-offset-2 ring-offset-night",
        )}
      >
        <PlusIcon size={16} weight="bold" aria-hidden="true" />
        New estimate
      </Link>
      <nav aria-label="Main" className="flex flex-col gap-0.5">
        {LINKS.filter((l) => !l.ownerOnly || user.is_owner).map((l) => {
          const on = l.on(path);
          return (
            <Link
              key={l.href}
              href={l.href}
              onClick={onPick}
              aria-current={on ? "page" : undefined}
              className={cn(
                "flex items-center gap-3 rounded-xl px-3 py-2.5 font-medium transition-colors",
                on
                  ? "bg-white/12 text-white"
                  : "text-white/70 hover:bg-white/7 hover:text-white",
              )}
            >
              <l.icon
                size={19}
                weight={on ? "fill" : "regular"}
                aria-hidden="true"
                className={on ? "text-peach" : undefined}
              />
              {l.label}
              {l.ownerOnly ? (
                <span className="ml-auto font-mono text-[10.5px] text-peach">
                  owner
                </span>
              ) : null}
            </Link>
          );
        })}
      </nav>
      <div className="mt-auto flex items-center gap-2.5 border-t border-white/10 px-1 pt-3">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-peach text-[13px] font-bold text-[#4a1903]">
          {initials(user)}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-semibold">
            {user.full_name || user.email}
          </span>
          <span className="block truncate text-xs text-white/55">
            {user.org_name}
          </span>
        </span>
        <button
          type="button"
          onClick={logout}
          aria-label="Log out"
          title="Log out"
          className="rounded-lg p-2 text-white/55 transition-colors hover:bg-white/8 hover:text-white"
        >
          <SignOutIcon size={18} aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}

/**
 * The signed-in app's side: on wide screens a fixed ink sidebar with the ember glow; on phones
 * a slim top bar whose menu button opens the same sidebar as a drawer.
 */
export function AppSidebar() {
  const [open, setOpen] = React.useState(false);

  React.useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <>
      <aside className="app-side sticky top-0 hidden h-svh w-60 shrink-0 px-3.5 py-5 text-white lg:block">
        <SideContent />
      </aside>

      <div className="app-side sticky top-0 z-30 flex items-center gap-3 px-4 py-3 text-white lg:hidden">
        <button
          type="button"
          onClick={() => setOpen(true)}
          aria-label="Open menu"
          aria-expanded={open}
          aria-controls="app-drawer"
          className="rounded-xl p-2 hover:bg-white/10"
        >
          <ListIcon size={22} aria-hidden="true" />
        </button>
        <Brand />
        <Link
          href="/estimate/new"
          className="ml-auto flex items-center gap-1.5 rounded-full bg-white px-4 py-2 text-sm font-semibold text-[#141414]"
        >
          <PlusIcon size={14} weight="bold" aria-hidden="true" />
          New
        </Link>
      </div>

      {open ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            type="button"
            aria-label="Close menu"
            onClick={() => setOpen(false)}
            className="absolute inset-0 bg-black/45"
          />
          <aside
            id="app-drawer"
            className="app-side drawer-in absolute inset-y-0 left-0 w-[17rem] px-3.5 py-5 text-white"
          >
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label="Close menu"
              className="absolute top-5 right-3 rounded-lg p-2 text-white/70 hover:bg-white/10"
            >
              <XIcon size={18} aria-hidden="true" />
            </button>
            <SideContent onPick={() => setOpen(false)} />
          </aside>
        </div>
      ) : null}
    </>
  );
}
