"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { clearToken, type CurrentUser } from "@/lib/api/client";

/** Up to two letters from the name (else the email) for the round profile button. */
function initials(user: CurrentUser): string {
  const words = user.full_name.trim().split(/\s+/).filter(Boolean);
  const letters = words.length
    ? words.length > 1
      ? words[0][0] + words[words.length - 1][0]
      : words[0][0]
    : user.email[0];
  return letters.toUpperCase();
}

/** The round profile button in the top bar: name and email, Account, Log out. */
export function ProfileMenu({ user }: { user: CurrentUser }) {
  const router = useRouter();
  const [open, setOpen] = React.useState(false);
  const box = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!open) return;
    function onPointer(event: PointerEvent) {
      if (!box.current?.contains(event.target as Node)) setOpen(false);
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("pointerdown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  function logout() {
    clearToken();
    router.replace("/login");
  }

  return (
    <div ref={box} className="relative">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls="profile-menu"
        aria-label={`Your profile: ${user.full_name}`}
        onClick={() => setOpen((v) => !v)}
        className="inline-flex size-10 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground ring-offset-background transition-shadow hover:ring-2 hover:ring-primary/30 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:outline-none"
      >
        {initials(user)}
      </button>
      {open ? (
        <div
          id="profile-menu"
          role="menu"
          className="absolute right-0 z-50 mt-2 w-64 overflow-hidden rounded-xl border bg-background shadow-lg max-md:right-auto max-md:left-0"
        >
          <div className="border-b px-4 py-3">
            <p className="truncate text-sm font-medium">{user.full_name}</p>
            <p className="truncate text-sm text-muted-foreground">
              {user.email}
            </p>
          </div>
          <div className="flex flex-col p-1">
            <Link
              href="/account"
              role="menuitem"
              onClick={() => setOpen(false)}
              className="rounded-lg px-3 py-2 text-sm hover:bg-foreground/[0.06]"
            >
              Account
            </Link>
            <button
              type="button"
              role="menuitem"
              onClick={logout}
              className="rounded-lg px-3 py-2 text-left text-sm hover:bg-foreground/[0.06]"
            >
              Log out
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
