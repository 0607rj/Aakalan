import Link from "next/link";

import { cn } from "@/lib/utils";

/**
 * The mark: the A of Aakalan drawn as an estimate. Its two strokes are a bell curve, the spread
 * of possible costs; the crossbar is the low-to-high range, and the dot sits where the most likely
 * cost is (left of centre: overruns go further than savings). White and orange on an ink tile, so
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
        stroke="#ff6a26"
        strokeWidth="2.6"
        strokeLinecap="round"
      />
      <circle
        cx="18.4"
        cy="24.5"
        r="2.9"
        fill="#ffc49a"
        stroke="#16181d"
        strokeWidth="1.3"
      />
    </svg>
  );
}

export function Logo({
  href = "/",
  large = false,
  className,
}: {
  href?: string;
  /** The footer's size. */
  large?: boolean;
  className?: string;
}) {
  return (
    <Link
      href={href}
      className={cn("flex items-center gap-2.5 rounded-lg", className)}
      aria-label="Aakalan home"
    >
      <LogoMark className={large ? "size-12" : undefined} />
      <span className="flex flex-col leading-none">
        <span
          className={cn(
            "font-head font-semibold tracking-[-0.02em]",
            large ? "text-[1.75rem]" : "text-[1.15rem]",
          )}
        >
          Aakalan
        </span>
        <span
          className={cn(
            "mt-[3px] leading-[1.55] text-muted-foreground",
            large ? "text-[13px]" : "text-[11px]",
          )}
          lang="hi"
        >
          आकलन
        </span>
      </span>
    </Link>
  );
}
