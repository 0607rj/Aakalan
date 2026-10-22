"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { useCurrentUser } from "@/components/auth-guard";
import { NavBar } from "@/components/site/navbar";
import { Button, buttonVariants } from "@/components/ui/button";
import { clearToken } from "@/lib/api/client";

const APP_LINKS = [
  { href: "/projects", label: "Your estimates" },
  { href: "/how-it-works", label: "How it works" },
];

/** The signed-in bar: the same bar as the public pages, with the app's own links. */
export function AppHeader() {
  const user = useCurrentUser();
  const router = useRouter();

  function logout() {
    clearToken();
    router.replace("/login");
  }

  return (
    <NavBar
      homeHref="/projects"
      links={APP_LINKS}
      note={
        <span className="hidden text-sm text-muted-foreground lg:inline">
          {user.org_name}
        </span>
      }
      actions={
        <>
          <Link href="/estimate/new" className={buttonVariants()}>
            New estimate
          </Link>
          <Button variant="outline" onClick={logout}>
            Log out
          </Button>
        </>
      }
    />
  );
}
