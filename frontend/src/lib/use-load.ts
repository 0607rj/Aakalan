"use client";

import * as React from "react";

import { errorText } from "@/lib/api/client";

export type LoadState<T> =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; data: T };

/**
 * Runs `loader` on mount and whenever it changes (wrap it in `useCallback`). `reload()` re-runs
 * it without flashing the loading state; `setData` lets callers apply a server response.
 */
export function useLoad<T>(loader: () => Promise<T>) {
  const [state, setState] = React.useState<LoadState<T>>({ kind: "loading" });
  const [version, setVersion] = React.useState(0);

  React.useEffect(() => {
    let cancelled = false;
    loader()
      .then((data) => {
        if (!cancelled) setState({ kind: "ready", data });
      })
      .catch((error: unknown) => {
        if (!cancelled) setState({ kind: "error", message: errorText(error) });
      });
    return () => {
      cancelled = true;
    };
  }, [loader, version]);

  const reload = React.useCallback(() => setVersion((v) => v + 1), []);
  const setData = React.useCallback(
    (data: T) => setState({ kind: "ready", data }),
    [],
  );
  return { state, reload, setData };
}
