"use client";

import * as React from "react";

import {
  CurrencyInrIcon,
  FileTextIcon,
  ListChecksIcon,
  MagnifyingGlassIcon,
} from "@phosphor-icons/react/dist/ssr";
import type { Icon } from "@phosphor-icons/react";

import { DOCUMENT_STEPS, StepIndicator } from "./parts";

/** The sheet's text lines: their widths (%), and which ones get picked out as a requirement.
 * A drawing only: it shows nothing read from the user's file. */
const LINES: { width: number; hit: boolean }[] = [
  { width: 92, hit: false },
  { width: 78, hit: true },
  { width: 86, hit: false },
  { width: 64, hit: false },
  { width: 90, hit: true },
  { width: 72, hit: false },
  { width: 84, hit: false },
  { width: 68, hit: true },
  { width: 88, hit: false },
  { width: 58, hit: true },
  { width: 80, hit: false },
];

/** The sheet's layout in px (globals.css `.read-sheet`), so each line lights up as the scan
 * line reaches it: the line's middle over the height the scan line travels, of one sweep. */
const FIRST_LINE_PX = 78;
const LINE_STEP_PX = 21;
const LINE_HALF_PX = 4;
const TRAVEL_PX = 340;
const SWEEP_S = 4;

const NOW: { icon: Icon; text: string }[] = [
  { icon: MagnifyingGlassIcon, text: "We read every page and sentence." },
  {
    icon: ListChecksIcon,
    text: "We list what it asks for, each with its page.",
  },
  {
    icon: CurrencyInrIcon,
    text: "You check the list next; nothing is priced before that.",
  },
];

function minutes(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

/** While an uploaded document is read: a sheet with a scan line sweeping down it, lines lit as
 * it passes and some marked as found; beside it the file, the time so far and what happens. */
export function ReadingDocument({ fileName }: { fileName: string }) {
  const [seconds, setSeconds] = React.useState(0);
  React.useEffect(() => {
    const id = window.setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => window.clearInterval(id);
  }, []);

  return (
    <div className="flex flex-col gap-8">
      <StepIndicator labels={DOCUMENT_STEPS} current={1} />
      <section
        role="status"
        aria-live="polite"
        className="read-stage grid min-h-[calc(100svh-14rem)] items-center gap-10 py-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)] lg:gap-14"
      >
        <div aria-hidden="true" className="app-head-grid read-grid" />

        <div aria-hidden="true" className="read-sheet mx-auto w-full max-w-sm">
          <div className="read-sheet-head">
            <FileTextIcon size={16} weight="duotone" />
            <span className="truncate">{fileName}</span>
          </div>
          {LINES.map((line, i) => (
            <span
              key={i}
              className={line.hit ? "read-line hit" : "read-line"}
              style={
                {
                  top: `${FIRST_LINE_PX - LINE_HALF_PX + i * LINE_STEP_PX}px`,
                  width: `calc((100% - 44px) * ${line.width / 100})`,
                  "--d": `${(((FIRST_LINE_PX + i * LINE_STEP_PX) / TRAVEL_PX) * SWEEP_S).toFixed(2)}s`,
                } as React.CSSProperties
              }
            />
          ))}
          <span className="read-beam" />
        </div>

        <div className="flex flex-col gap-5 text-center lg:text-left">
          <div className="flex flex-col gap-2">
            <p className="eyebrow text-tape">Reading</p>
            <h1 className="font-wide text-[2rem] leading-tight text-balance sm:text-[2.4rem]">
              Reading your document
            </h1>
            <p className="mx-auto max-w-md text-muted-foreground lg:mx-0">
              Long documents can take a minute or two. Please keep this page
              open.
            </p>
          </div>
          <p className="mx-auto flex w-fit flex-wrap items-center justify-center gap-x-3 gap-y-1 rounded-full border bg-card px-4 py-2 text-sm lg:mx-0">
            <span className="max-w-[16rem] truncate font-medium">
              {fileName}
            </span>
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
