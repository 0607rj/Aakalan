"use client";

import { useRouter } from "next/navigation";
import { EyeIcon } from "@phosphor-icons/react/dist/ssr";

import { useCurrentUser } from "@/components/auth-guard";
import { clearToken, stopViewing } from "@/lib/api/client";

/** While the site owner looks at someone's account: whose it is, that nothing can be changed,
 * and the way back to Admin. */
export function ViewingBanner() {
  const user = useCurrentUser();
  const router = useRouter();
  if (!user.viewed_by_owner) return null;

  function back() {
    if (stopViewing()) {
      router.push("/admin");
    } else {
      clearToken();
      router.replace("/login");
    }
  }

  return (
    <div className="bg-tape text-primary-foreground">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-2.5 text-sm sm:px-6">
        <EyeIcon size={18} weight="bold" aria-hidden="true" />
        <span className="flex-1">
          Viewing <strong>{user.full_name || user.email}</strong> ({user.email}
          {user.org_name !== user.email ? `, ${user.org_name}` : ""}). Read
          only: nothing can be changed.
        </span>
        <button
          type="button"
          onClick={back}
          className="rounded-full bg-black/15 px-3 py-1 font-semibold transition-colors hover:bg-black/25 focus-visible:ring-2 focus-visible:ring-black focus-visible:outline-none"
        >
          Back to Admin
        </button>
      </div>
    </div>
  );
}
