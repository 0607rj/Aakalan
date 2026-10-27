import Link from "next/link";

import { cn } from "@/lib/utils";

/**
 * The mark: the A of Aakalan drawn as an estimate. Its two strokes are a bell curve, the spread
 * of possible costs; the crossbar is the low-to-high range, and the dot sits where the most likely
 * cost is (left of centre: overruns go further than savings). White and violet on an ink tile, so
 * it reads at 16px as well as large.
 */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 40 40"
      aria-hidden="true"
      focusable="false"
      className={cn("size-9", className)}
    >
      <rect width="40" height="40" rx="10" fill="#16181d" />
      <path
        d="M8.5 31 C14 31 15.2 9.5 20 9.5 C24.8 9.5 26 31 31.5 31"
        fill="none"
        stroke="#ffffff"
        strokeWidth="3.2"
        strokeLinecap="round"
      />
      <path
        d="M11.5 24.5 H28.5"
        stroke="#8f7ff0"
        strokeWidth="2.6"
        strokeLinecap="round"
      />
      <circle
        cx="18.4"
        cy="24.5"
        r="2.9"
        fill="#c9bfff"
        stroke="#16181d"
        strokeWidth="1.3"
      />
    </svg>
  );
}

export function Logo({
  href = "/",
  className,
}: {
  href?: string;
  className?: string;
}) {
  return (
    <Link
      href={href}
      className={cn("flex items-center gap-2.5 rounded-lg", className)}
      aria-label="Aakalan home"
    >
      <LogoMark />
      <span className="flex flex-col leading-none">
        <span className="font-display text-[1.2rem] tracking-[-0.04em]">
          Aakalan
        </span>
        <span className="text-[11px] text-muted-foreground" lang="hi">
          आकलन
        </span>
      </span>
    </Link>
  );
}
