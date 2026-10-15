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
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-6">
        <Link href="/projects" className="flex items-baseline gap-2">
          <span className="text-lg font-semibold tracking-tight text-primary">
            Aakalan
          </span>
          <span className="hidden text-xs text-muted-foreground sm:inline">
            {user.org_name}
          </span>
        </Link>
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground">{user.email}</span>
          <Button variant="outline" size="sm" onClick={logout}>
            Log out
          </Button>
        </div>
      </div>
    </header>
  );
}
