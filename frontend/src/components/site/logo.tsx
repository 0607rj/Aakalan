import Link from "next/link";

import { cn } from "@/lib/utils";

/**
 * The mark: a piece of measuring tape. A sky-blue case, the light tape with tick marks, and a
 * saffron marker where the most likely cost sits.
 */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 40 40"
      aria-hidden="true"
      focusable="false"
      className={cn("size-9", className)}
    >
      <rect
        x="1"
        y="1"
        width="38"
        height="38"
        rx="10"
        fill="#0b78b8"
        stroke="#08639a"
      />
      <rect x="7" y="17" width="26" height="10" rx="2" fill="#f7f4ec" />
      {[10, 14, 18, 22, 26, 30].map((x, i) => (
        <line
          key={x}
          x1={x}
          x2={x}
          y1="17"
          y2={i % 2 === 0 ? 23 : 21}
          stroke="#0b78b8"
          strokeWidth="1.4"
        />
      ))}
      <path d="M22 8 L26 8 L24 13 Z" fill="#f2a541" />
      <line
        x1="24"
        x2="24"
        y1="12"
        y2="29"
        stroke="#f2a541"
        strokeWidth="1.6"
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
        <span className="font-wide text-lg font-semibold">Aakalan</span>
        <span className="text-[11px] text-muted-foreground" lang="hi">
          आकलन
        </span>
      </span>
    </Link>
  );
}
