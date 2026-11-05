"use client";

import * as React from "react";

import {
  CalculatorIcon,
  ChartBarHorizontalIcon,
  CloudIcon,
} from "@phosphor-icons/react/dist/ssr";
import type { Icon } from "@phosphor-icons/react";

import { StepIndicator } from "./parts";

/** The cost sheet's rows: the item's width and its amount's width (%). A drawing only: no
 * number on it, nothing from the user's estimate. */
const ROWS: { item: number; amount: number }[] = [
  { item: 62, amount: 70 },
  { item: 48, amount: 55 },
  { item: 70, amount: 85 },
  { item: 40, amount: 45 },
  { item: 56, amount: 62 },
];

/** Seconds between one row and the next, and of one fill of the sheet (globals.css
 * `.cost-row`, `.cost-loop`): the sheet starts again every LOOP_S. */
const ROW_GAP_S = 0.35;
const LOOP_S = 5;

const NOW: { icon: Icon; text: string }[] = [
  {
    icon: CalculatorIcon,
    text: "Each feature is priced from the rate card, by the hours it takes.",
  },
  {
    icon: CloudIcon,
    text: "Hosting, support and the years of running are added.",
  },
  {
    icon: ChartBarHorizontalIcon,
    text: "Many simulated runs give a low, likely and high price. No AI sets any number.",
  },
];

function minutes(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

/** While the engine prices an estimate: a cost sheet filling in row by row and a low / likely
 * / high range settling at its foot; beside it the project, the time so far and how the price
 * is worked out. The same layout as reading a document (`ReadingDocument`). */
export function Calculating({
  labels,
  name,
}: {
  labels: string[];
  name?: string;
}) {
  const [seconds, setSeconds] = React.useState(0);
  React.useEffect(() => {
    const id = window.setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => window.clearInterval(id);
  }, []);

  return (
    <div className="flex flex-col gap-8">
      <StepIndicator labels={labels} current={3} />
      <section
        role="status"
        aria-live="polite"
        className="read-stage grid min-h-[calc(100svh-14rem)] items-center gap-10 py-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)] lg:gap-14"
      >
        <div aria-hidden="true" className="app-head-grid read-grid" />

        <div aria-hidden="true" className="cost-sheet mx-auto w-full max-w-sm">
          {/* a new key starts every animation again: the sheet fills in once per loop */}
          <div key={Math.floor(seconds / LOOP_S)} className="cost-loop">
            <div className="read-sheet-head">
              <CalculatorIcon size={16} weight="duotone" />
              <span>Cost sheet</span>
            </div>
            <div className="flex flex-col gap-3.5 pt-5">
              {ROWS.map((row, i) => (
                <div
                  key={i}
                  className="cost-row"
                  style={
                    {
                      "--d": `${(i * ROW_GAP_S).toFixed(2)}s`,
                    } as React.CSSProperties
                  }
                >
                  <span
                    className="cost-bar"
                    style={{ width: `${row.item}%` }}
                  />
                  <span className="cost-dots" />
                  <span className="cost-amount">
                    <span style={{ width: `${row.amount}%` }} />
                  </span>
                </div>
              ))}
            </div>
            <div className="cost-range">
              <div className="flex justify-between font-mono text-[11px] tracking-[0.06em] text-muted-foreground uppercase">
                <span>Low</span>
                <span>Likely</span>
                <span>High</span>
              </div>
              <div className="cost-track">
                <span className="cost-band" />
                <span className="cost-pin" />
              </div>
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-5 text-center lg:text-left">
          <div className="flex flex-col gap-2">
            <p className="eyebrow text-tape">Pricing</p>
            <h1 className="font-wide text-[2rem] leading-tight text-balance sm:text-[2.4rem]">
              Working out your cost
            </h1>
            <p className="mx-auto max-w-md text-muted-foreground lg:mx-0">
              This usually takes a few seconds. Please keep this page open.
            </p>
          </div>
          <p className="mx-auto flex w-fit flex-wrap items-center justify-center gap-x-3 gap-y-1 rounded-full border bg-card px-4 py-2 text-sm lg:mx-0">
            {name ? (
              <span className="max-w-[16rem] truncate font-medium">{name}</span>
            ) : null}
            <span className="font-mono text-muted-foreground tabular-nums">
              {minutes(seconds)}
            </span>
          </p>
          <ul className="mx-auto flex max-w-md flex-col gap-3 text-left lg:mx-0">
            {NOW.map(({ icon: ItemIcon, text }) => (
              <li key={text} className="flex items-start gap-3 text-sm">
                <span className="grid size-8 shrink-0 place-items-center rounded-full bg-tape-soft text-tape">
                  <ItemIcon size={16} weight="bold" aria-hidden="true" />
                </span>
                <span className="pt-1.5">{text}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>
    </div>
  );
}
