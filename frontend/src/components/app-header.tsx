"use client";

import Link from "next/link";

import { useCurrentUser } from "@/components/auth-guard";
import { ProfileMenu } from "@/components/profile-menu";
import { NavBar } from "@/components/site/navbar";
import { buttonVariants } from "@/components/ui/button";

const APP_LINKS = [
  { href: "/projects", label: "Your estimates" },
  { href: "/how-it-works", label: "How it works" },
];

/** The signed-in bar: the same bar as the public pages, with the app's own links and the
 * profile button (Account, Log out). */
export function AppHeader() {
  const user = useCurrentUser();

  return (
    <NavBar
      homeHref="/projects"
      links={APP_LINKS}
      actions={
        <>
          <Link href="/estimate/new" className={buttonVariants()}>
            New estimate
          </Link>
          <ProfileMenu user={user} />
        </>
      }
    />
  );
}
