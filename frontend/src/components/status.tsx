import * as React from "react";

import { cn } from "@/lib/utils";

/**
 * The loading screen: the logo mark drawing itself in the middle of the space, hopping a little.
 * The bell curve draws, the low-to-high bar appears and the dot settles on the likely cost
 * (styles `.loader-*` in globals.css; still under reduced motion).
 */
export function Loading({
  children = "Loading…",
  className,
}: {
  children?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        "flex min-h-[40vh] w-full flex-col items-center justify-center gap-4 py-10",
        className,
      )}
    >
      <div className="loader-mark flex flex-col items-center">
        <svg
          viewBox="0 0 40 40"
          aria-hidden="true"
          focusable="false"
          className="size-16"
        >
          <rect width="40" height="40" rx="10" fill="#16181d" />
          <path
            className="loader-curve"
            d="M8.5 31 C14 31 15.2 9.5 20 9.5 C24.8 9.5 26 31 31.5 31"
            fill="none"
            stroke="#ffffff"
            strokeWidth="3.2"
            strokeLinecap="round"
          />
          <path
            className="loader-bar"
            d="M11.5 24.5 H28.5"
            stroke="#ff6a26"
            strokeWidth="2.6"
            strokeLinecap="round"
          />
          <circle
            className="loader-dot"
            cx="18.4"
            cy="24.5"
            r="2.9"
            fill="#ffc49a"
            stroke="#16181d"
            strokeWidth="1.3"
          />
        </svg>
      </div>
      <div className="loader-shadow" aria-hidden="true" />
      <p className="text-sm text-muted-foreground">{children}</p>
    </div>
  );
}

export function ErrorNotice({
  message,
  className,
}: {
  message: string | null | undefined;
  className?: string;
}) {
  if (!message) return null;
  return (
    <p
      role="alert"
      className={cn(
        "rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive",
        className,
      )}
    >
      {message}
    </p>
  );
}

export function WarningNotice({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-md border border-warning/30 bg-warning-muted px-3 py-2 text-sm text-warning",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function SectionTitle({
  children,
  action,
}: {
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <h2 className="text-base font-semibold">{children}</h2>
      {action}
    </div>
  );
}
