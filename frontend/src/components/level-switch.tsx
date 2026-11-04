"use client";

import * as React from "react";

import { cn } from "@/lib/utils";

/**
 * Basic / Standard / Advanced as one switch: an orange pill springs to the level picked
 * (`.level-pill` in globals.css). Radio inputs underneath, so arrow keys move between levels.
 * Nothing picked (`value` not among the options) shows no pill.
 */
export function LevelSwitch<T extends string>({
  name,
  label,
  options,
  value,
  onChange,
  size = "md",
  className,
}: {
  /** The radio group's name: unique on the page. */
  name: string;
  label: string;
  options: { key: T; label: string }[];
  value: T | null;
  onChange: (key: T) => void;
  size?: "sm" | "md";
  className?: string;
}) {
  const index = options.findIndex((o) => o.key === value);
  const n = options.length;
  return (
    <div
      role="radiogroup"
      aria-label={label}
      className={cn(
        "relative grid w-fit shrink-0 rounded-full border bg-background p-0.5",
        className,
      )}
      style={{ gridTemplateColumns: `repeat(${n}, minmax(0, 1fr))` }}
    >
      {index >= 0 ? (
        <span
          aria-hidden="true"
          className="level-pill"
          style={{
            width: `calc((100% - 4px) / ${n})`,
            transform: `translateX(${index * 100}%)`,
          }}
        />
      ) : null}
      {options.map((o) => {
        const selected = o.key === value;
        return (
          <label
            key={o.key}
            className={cn(
              "relative z-[1] cursor-pointer rounded-full text-center font-medium whitespace-nowrap transition-colors duration-300 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring",
              size === "sm" ? "px-3 py-1 text-xs" : "px-3.5 py-1.5 text-sm",
              selected
                ? "text-white"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            <input
              type="radio"
              name={name}
              checked={selected}
              onChange={() => onChange(o.key)}
              className="sr-only"
            />
            {o.label}
          </label>
        );
      })}
    </div>
  );
}
