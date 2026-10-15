"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { useCurrentUser } from "@/components/auth-guard";
import { Button } from "@/components/ui/button";
import { clearToken } from "@/lib/api/client";

export function AppHeader() {
  const user = useCurrentUser();
  const router = useRouter();

  function logout() {
    clearToken();
    router.replace("/login");
  }

  return (
    <header className="border-b bg-card">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-3 px-4 sm:px-6">
        <Link href="/projects" className="flex items-baseline gap-2">
          <span className="text-lg font-semibold tracking-tight text-primary">
            Aakalan
          </span>
          <span className="hidden text-xs text-muted-foreground md:inline">
            {user.org_name}
          </span>
        </Link>
        <nav className="flex items-center gap-2 sm:gap-3">
          <Link
            href="/estimate/new"
            className="rounded-md px-3 py-1.5 text-sm font-medium text-primary hover:bg-muted"
          >
            New estimate
          </Link>
          <span className="hidden text-sm text-muted-foreground lg:inline">
            {user.email}
          </span>
          <Button variant="outline" size="sm" onClick={logout}>
            Log out
          </Button>
        </nav>
      </div>
    </header>
  );
}
