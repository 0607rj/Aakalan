"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

import {
  ApiError,
  api,
  clearToken,
  getToken,
  type CurrentUser,
} from "@/lib/api/client";
import { Loading } from "@/components/status";

const CurrentUserContext = React.createContext<CurrentUser | null>(null);

export function useCurrentUser(): CurrentUser {
  const user = React.useContext(CurrentUserContext);
  if (!user) {
    throw new Error("useCurrentUser must be used inside <AuthGuard>");
  }
  return user;
}

type GuardState =
  | { kind: "loading" }
  | { kind: "ready"; user: CurrentUser }
  | { kind: "error"; message: string };

/** The user last checked in this browser tab, with the token it was checked for. Each signed-in
 * section has its own layout, so the guard mounts again on every move between them: with this
 * it shows the page at once (checking again quietly) instead of a second loading screen. */
let checked: { token: string; user: CurrentUser } | null = null;

function remembered(): CurrentUser | null {
  const token = getToken();
  return checked && token && checked.token === token ? checked.user : null;
}

/** Client-side guard: verifies the stored token with `/auth/me`, else redirects to `/login`. */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [state, setState] = React.useState<GuardState>(() => {
    const user = remembered();
    return user ? { kind: "ready", user } : { kind: "loading" };
  });

  React.useEffect(() => {
    let cancelled = false;

    async function verify() {
      const token = getToken();
      if (!token) {
        checked = null;
        router.replace("/login");
        return;
      }
      try {
        const user = await api.me();
        checked = { token, user };
        if (!cancelled) setState({ kind: "ready", user });
      } catch (error) {
        if (cancelled) return;
        if (error instanceof ApiError && error.status === 401) {
          checked = null;
          clearToken();
          router.replace("/login");
          return;
        }
        // a quiet re-check that could not reach the API: keep the page already shown
        if (remembered()) return;
        setState({
          kind: "error",
          message:
            error instanceof Error ? error.message : "Could not reach the API",
        });
      }
    }

    void verify();
    return () => {
      cancelled = true;
    };
  }, [router]);

  if (state.kind === "loading") {
    return (
      <div className="flex min-h-svh flex-1 items-center justify-center">
        <Loading>Checking your session…</Loading>
      </div>
    );
  }

  if (state.kind === "error") {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-2 text-sm">
        <p className="font-medium text-destructive">
          Could not verify your session.
        </p>
        <p className="text-muted-foreground">{state.message}</p>
      </div>
    );
  }

  return (
    <CurrentUserContext.Provider value={state.user}>
      {children}
    </CurrentUserContext.Provider>
  );
}
