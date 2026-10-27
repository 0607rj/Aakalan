import type { CSSProperties } from "react";
import Link from "next/link";

import { cn } from "@/lib/utils";

const KEY_ROWS = [
  ["7", "8", "9", "÷"],
  ["4", "5", "6", "×"],
  ["1", "2", "3", "−"],
  ["0", ".", "%", "+"],
];

/** The sums a spreadsheet estimate makes you type, each pressed in turn. */
const SUMS: Record<string, { label: string; order: number }> = {
  "×": { label: "Hours", order: 0 },
  "8": { label: "Rate", order: 1 },
  "+": { label: "Risk", order: 2 },
  "%": { label: "GST", order: 3 },
  "−": { label: "AI saving", order: 4 },
  "3": { label: "Years O&M", order: 5 },
};

/**
 * The closing picture: a keypad whose sums press themselves when it comes into view, then
 * "Estimate" lights up. The keys only give a little under the pointer; "Estimate" is the one
 * that works, and starts an estimate.
 */
export function Keypad({ className }: { className?: string }) {
  return (
    <div
      data-reveal
      className={cn("keypad flex flex-col items-center gap-3", className)}
    >
      <div
        aria-hidden="true"
        className="grid grid-cols-4 gap-2 rounded-[22px] border bg-card p-3 shadow-[0_1px_2px_rgb(0_0_0/0.05),0_12px_28px_-20px_rgb(0_0_0/0.2)] sm:gap-2.5 sm:p-4"
      >
        {KEY_ROWS.flat().map((k) => {
          const sum = SUMS[k];
          return (
            <span
              key={k}
              className={cn(
                "key flex size-14 flex-col items-center justify-center rounded-xl border border-foreground/[0.08] bg-gradient-to-b from-card to-muted font-mono text-lg text-foreground/85 shadow-[inset_0_-2px_0_rgb(0_0_0/0.08)] transition-[transform,box-shadow,color] duration-150 select-none hover:-translate-y-0.5 hover:text-primary hover:shadow-[inset_0_-2px_0_rgb(0_0_0/0.08),0_6px_14px_-8px_rgb(0_0_0/0.35)] active:translate-y-px active:shadow-none sm:size-16",
                sum && "sum",
              )}
              style={sum ? ({ "--d": sum.order } as CSSProperties) : undefined}
            >
              <b className="leading-none font-medium">{k}</b>
              {sum ? (
                <small className="mt-1 text-[9px] tracking-wide text-muted-foreground uppercase">
                  {sum.label}
                </small>
              ) : null}
            </span>
          );
        })}
      </div>
      <Link
        href="/estimate/new"
        className="keypad-auto flex items-center gap-2 rounded-xl border border-foreground/[0.08] bg-gradient-to-b from-card to-muted px-6 py-3 font-semibold text-foreground/80 shadow-[inset_0_-2px_0_rgb(0_0_0/0.08)] transition-transform duration-150 hover:-translate-y-0.5 active:translate-y-px"
      >
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          className="size-[18px]"
          fill="none"
        >
          <path
            d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          />
        </svg>
        Estimate
      </Link>
    </div>
  );
}
