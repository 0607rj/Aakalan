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

/** Client-side guard: verifies the stored token with `/auth/me`, else redirects to `/login`. */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [state, setState] = React.useState<GuardState>({ kind: "loading" });

  React.useEffect(() => {
    let cancelled = false;

    async function verify() {
      if (!getToken()) {
        router.replace("/login");
        return;
      }
      try {
        const user = await api.me();
        if (!cancelled) setState({ kind: "ready", user });
      } catch (error) {
        if (cancelled) return;
        if (error instanceof ApiError && error.status === 401) {
          clearToken();
          router.replace("/login");
          return;
        }
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
      <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
        Checking session…
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
