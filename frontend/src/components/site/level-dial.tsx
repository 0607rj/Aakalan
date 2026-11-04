"use client";

import * as React from "react";

import { LevelSwitch } from "@/components/level-switch";

type Key = "basic" | "standard" | "advanced";

/** Illustration only: one feature at three levels, in lakh; not a real estimate. */
const LEVELS: {
  key: Key;
  label: string;
  likely: number;
  low: number;
  high: number;
  what: string;
}[] = [
  {
    key: "basic",
    label: "Basic",
    likely: 1.1,
    low: 0.9,
    high: 1.5,
    what: "Pay by UPI or card, with one receipt.",
  },
  {
    key: "standard",
    label: "Standard",
    likely: 2.4,
    low: 1.9,
    high: 3.3,
    what: "Pay by UPI or card, refunds, saved cards and a payment report.",
  },
  {
    key: "advanced",
    label: "Advanced",
    likely: 4.2,
    low: 3.3,
    high: 6.1,
    what: "Everything in Standard, plus split payments and daily matching with the bank.",
  },
];
/** The range bar's right end, in lakh. */
const SCALE = 7;
const AUTO_MS = 2600;
const DIGITS = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"];

/** One digit that rolls to its value, like a meter. */
function Roll({ digit, delay = 0 }: { digit: number; delay?: number }) {
  return (
    <span className="roll-col">
      <span
        style={{
          transform: `translateY(-${digit}em)`,
          transitionDelay: `${delay}ms`,
        }}
      >
        {DIGITS.map((d) => (
          <i key={d}>{d}</i>
        ))}
      </span>
    </span>
  );
}

/**
 * The Features page's first row: pick Basic, Standard or Advanced for one feature and the price
 * rolls to it while the low-to-high range stretches. It steps through the levels by itself
 * until someone picks one (not with reduced motion).
 */
export function LevelDial() {
  const [index, setIndex] = React.useState(1);
  const [auto, setAuto] = React.useState(true);

  React.useEffect(() => {
    if (!auto) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const timer = window.setInterval(
      () => setIndex((i) => (i + 1) % LEVELS.length),
      AUTO_MS,
    );
    return () => window.clearInterval(timer);
  }, [auto]);

  const level = LEVELS[index];
  if (!level) return null;
  const [whole = 0, tenth = 0] = level.likely.toFixed(1).split(".").map(Number);
  const pct = (v: number) => `${(v / SCALE) * 100}%`;

  return (
    <div className="flex flex-col gap-6 p-5 sm:p-6">
      <div className="flex items-baseline justify-between gap-3">
        <span className="font-wide text-lg">Online payment</span>
        <span className="text-xs text-muted-foreground">one feature</span>
      </div>
      <LevelSwitch
        name="level-dial"
        label="Level"
        options={LEVELS}
        value={level.key}
        onChange={(key) => {
          setAuto(false);
          setIndex(LEVELS.findIndex((l) => l.key === key));
        }}
        className="w-full"
      />
      <p
        className="font-wide flex items-baseline text-[3.4rem] leading-none tracking-[-0.03em] tabular-nums"
        aria-live="polite"
      >
        <span className="mr-1.5 text-[0.7em] text-tape">₹</span>
        <span className="sr-only">{level.likely.toFixed(1)}</span>
        <span aria-hidden="true" className="flex">
          <Roll digit={whole} />.<Roll digit={tenth} delay={70} />
        </span>
        <span className="ml-2 font-sans text-[0.3em] tracking-normal text-muted-foreground">
          lakh likely
        </span>
      </p>
      <div className="flex flex-col gap-2">
        <div className="relative h-2.5 rounded-full bg-border">
          <div
            className="range-band absolute inset-y-0 rounded-full bg-tape/85"
            style={{ left: pct(level.low), width: pct(level.high - level.low) }}
          />
          <div
            className="range-pin absolute top-1/2 -mt-[9px] -ml-[9px] size-[18px] rounded-full border-[3px] border-tape-bright bg-card"
            style={{ left: pct(level.likely) }}
          />
        </div>
        <div className="flex justify-between font-mono text-[11.5px] text-muted-foreground tabular-nums">
          <span>low ₹{level.low.toFixed(1)} L</span>
          <span>high ₹{level.high.toFixed(1)} L</span>
        </div>
      </div>
      <p className="min-h-[2.8em] text-sm text-muted-foreground">
        {level.what}
      </p>
    </div>
  );
}
