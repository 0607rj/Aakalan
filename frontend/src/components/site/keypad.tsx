import Link from "next/link";

import { cn } from "@/lib/utils";

const KEYS = [
  "7",
  "8",
  "9",
  "÷",
  "4",
  "5",
  "6",
  "×",
  "1",
  "2",
  "3",
  "−",
  "0",
  ".",
  "Not sure",
  "+",
];

/** The keys that are not digits, in the accent. */
const SUMS = new Set(["÷", "×", "−", "+", "Not sure"]);

/**
 * The closing picture: a calculator a little askew, for the sums a spreadsheet makes you type.
 * Only "Estimate" works, and starts an estimate.
 */
export function Keypad({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "grid w-[min(300px,100%)] rotate-3 grid-cols-4 gap-2.5 justify-self-center rounded-[26px] bg-white p-[18px] text-foreground shadow-[0_30px_60px_-30px_rgb(0_0_0/0.7)]",
        className,
      )}
    >
      {KEYS.map((k) => (
        <span
          key={k}
          aria-hidden="true"
          className={cn(
            "grid aspect-square place-items-center rounded-full text-center leading-none select-none",
            SUMS.has(k)
              ? "bg-tape-soft font-mono text-tape"
              : "bg-muted font-head font-medium",
            k === "Not sure" ? "text-[11px]" : "text-lg",
          )}
        >
          {k}
        </span>
      ))}
      <Link
        href="/estimate/new"
        className="col-span-full rounded-[14px] bg-tape-bright p-[13px] text-center text-[15px] font-medium text-white transition-transform hover:-translate-y-px"
      >
        Estimate
      </Link>
    </div>
  );
}
