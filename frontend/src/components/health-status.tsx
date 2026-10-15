"use client";

import * as React from "react";

import { api, API_URL } from "@/lib/api/client";
import { cn } from "@/lib/utils";

type HealthState =
  { kind: "checking" } | { kind: "ok"; version: string } | { kind: "down" };

/** Small footer indicator showing whether the backend `/health` endpoint responds. */
export function HealthStatus() {
  const [state, setState] = React.useState<HealthState>({ kind: "checking" });

  React.useEffect(() => {
    let cancelled = false;
    api
      .health()
      .then((health) => {
        if (!cancelled) setState({ kind: "ok", version: health.version });
      })
      .catch(() => {
        if (!cancelled) setState({ kind: "down" });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const label =
    state.kind === "checking"
      ? "Checking API…"
      : state.kind === "ok"
        ? `API online · v${state.version}`
        : `API unreachable at ${API_URL}`;

  return (
    <footer className="border-t bg-card">
      <div className="mx-auto flex h-10 max-w-6xl items-center gap-2 px-6 text-xs text-muted-foreground">
        <span
          aria-hidden
          className={cn(
            "size-2 rounded-full",
            state.kind === "ok" && "bg-success",
            state.kind === "down" && "bg-destructive",
            state.kind === "checking" && "bg-muted-foreground/40",
          )}
        />
        <span>{label}</span>
      </div>
    </footer>
  );
}
