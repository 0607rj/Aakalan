/**
 * Illustrations made of the product's own pieces: the cost range as a measuring tape, a
 * requirement document with the line a feature came from, a question, the team. Figures are
 * a worked example (a small clinic booking app), labelled as such wherever they appear.
 * Parts marked fig-* play once when their `[data-reveal]` parent comes into view.
 */
import type { CSSProperties } from "react";

import { cn } from "@/lib/utils";

const LAKH = 100_000;

function lakh(rupees: number): string {
  return `₹${(rupees / LAKH).toLocaleString("en-IN", { maximumFractionDigits: 1 })} L`;
}

/** A delay step for the fig-* animations. */
const step = (d: number) => ({ "--d": d }) as CSSProperties;

const FIGURE = "panel rounded-2xl p-5";

/**
 * The signature: a cost range drawn on a measuring tape. The band runs from the low to the
 * high cost; the marker stands on the most likely one.
 */
export function RangeTape({
  low,
  likely,
  high,
  scaleMax,
  className,
}: {
  low: number;
  likely: number;
  high: number;
  scaleMax: number;
  className?: string;
}) {
  const at = (v: number) => `${(100 * v) / scaleMax}%`;
  return (
    <div className={cn("relative pt-9 pb-7", className)}>
      {/* marker */}
      <div
        className="absolute top-0 flex -translate-x-1/2 flex-col items-center"
        style={{ left: at(likely) }}
      >
        <span className="rounded-full bg-foreground px-2.5 py-1 font-mono text-[11px] font-medium whitespace-nowrap text-background tabular-nums">
          Likely {lakh(likely)}
        </span>
        <span className="h-3 w-px bg-foreground" />
      </div>
      {/* tape */}
      <div className="tape-ticks relative h-8 overflow-hidden rounded-md bg-tape shadow-[inset_0_1px_0_rgb(255_255_255/0.4),0_0_40px_-6px_rgb(11_120_184/0.5)]">
        <div
          className="absolute inset-y-0 bg-foreground/15"
          style={{ left: at(low), width: `calc(${at(high)} - ${at(low)})` }}
        />
        <div
          className="absolute inset-y-0 w-0.5 bg-white"
          style={{ left: at(likely) }}
        />
      </div>
      {/* ends of the range */}
      <span
        className="absolute bottom-0 -translate-x-1/2 font-mono text-[11px] text-muted-foreground tabular-nums"
        style={{ left: at(low) }}
      >
        {lakh(low)}
      </span>
      <span
        className="absolute bottom-0 -translate-x-1/2 font-mono text-[11px] text-muted-foreground tabular-nums"
        style={{ left: at(high) }}
      >
        {lakh(high)}
      </span>
    </div>
  );
}

const EXAMPLE = {
  low: 1_400_000,
  likely: 1_900_000,
  high: 2_600_000,
  withoutAi: 2_350_000,
};

const EXAMPLE_FEATURES = [
  { name: "Bookings and appointments", level: "Standard", ai: 2.6, old: 3.3 },
  { name: "Online fee payment", level: "Basic", ai: 1.1, old: 1.4 },
  { name: "Mobile app", level: "Basic", ai: 3.0, old: 3.9 },
  { name: "SMS reminders", level: "", ai: 0.9, old: 1.1 },
];

/** What an estimate looks like. */
export function EstimateMockup({ className }: { className?: string }) {
  return (
    <figure className={cn("panel rounded-[22px] p-5 sm:p-6", className)}>
      <figcaption className="flex items-start justify-between gap-3">
        <span className="flex flex-col gap-1">
          <span className="eyebrow">Example estimate</span>
          <span className="font-semibold">Clinic booking app</span>
        </span>
        <span className="rounded-full border border-ai/30 bg-ai-soft px-2.5 py-1 text-xs font-semibold text-ai">
          {Math.round(100 * (1 - EXAMPLE.likely / EXAMPLE.withoutAi))}% less
          with AI tools
        </span>
      </figcaption>
      <RangeTape
        className="mt-4"
        low={EXAMPLE.low}
        likely={EXAMPLE.likely}
        high={EXAMPLE.high}
        scaleMax={3_000_000}
      />
      <table className="mt-4 w-full text-sm">
        <thead>
          <tr className="text-left">
            <th className="eyebrow pb-2 font-normal">Feature</th>
            <th className="eyebrow pb-2 pl-3 text-right font-normal whitespace-nowrap">
              Without AI
            </th>
            <th className="eyebrow pb-2 pl-3 text-right font-normal whitespace-nowrap">
              With AI
            </th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {EXAMPLE_FEATURES.map((f) => (
            <tr key={f.name}>
              <td className="py-2 pr-2">
                {f.name}
                {f.level ? (
                  <span className="ml-2 rounded-full border px-2 py-0.5 text-[11px] text-muted-foreground">
                    {f.level}
                  </span>
                ) : null}
              </td>
              <td className="py-2 text-right font-mono text-[13px] text-muted-foreground tabular-nums line-through decoration-muted-foreground/40">
                ₹{f.old} L
              </td>
              <td className="py-2 text-right font-mono text-[13px] font-medium tabular-nums">
                ₹{f.ai} L
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-4 flex items-center gap-3 rounded-xl bg-panel-2 px-3 py-2.5 text-sm">
        <PeopleIcons count={4} />
        <span>About 4 people for 3 months</span>
      </div>
    </figure>
  );
}

export function PeopleIcons({ count }: { count: number }) {
  return (
    <span className="flex -space-x-1.5" aria-hidden="true">
      {Array.from({ length: count }, (_, i) => (
        <svg
          key={i}
          viewBox="0 0 24 24"
          className="size-6 rounded-full border-2 border-card bg-muted p-0.5"
        >
          <circle cx="12" cy="9" r="4" fill="#8a94a3" />
          <path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6" fill="#8a94a3" />
        </svg>
      ))}
    </span>
  );
}

/** A page of a requirement document, with the line a feature was found in. */
export function DocumentMockup({ className }: { className?: string }) {
  return (
    <figure data-reveal className={cn(FIGURE, "relative", className)}>
      <figcaption className="eyebrow">
        requirement-document.pdf · page 4
      </figcaption>
      <div className="mt-3 flex flex-col gap-2" aria-hidden="true">
        <div className="h-2 w-3/4 rounded bg-foreground/[0.07]" />
        <div className="h-2 w-full rounded bg-foreground/[0.07]" />
        <div className="h-2 w-5/6 rounded bg-foreground/[0.07]" />
      </div>
      <p className="fig-mark mt-3 rounded-md px-2 py-1.5 text-sm">
        <span className="font-mono font-medium text-tape">4.2</span> Patients
        shall book, move and cancel appointments online, and receive an SMS
        reminder.
      </p>
      <div className="mt-3 flex flex-col gap-2" aria-hidden="true">
        <div className="h-2 w-full rounded bg-foreground/[0.07]" />
        <div className="h-2 w-2/3 rounded bg-foreground/[0.07]" />
      </div>
      <div className="mt-4 flex flex-wrap gap-2 text-xs">
        <span
          className="fig-step lit rounded-full px-2.5 py-1 font-semibold"
          style={step(2)}
        >
          Bookings · clause 4.2
        </span>
        <span
          className="fig-step rounded-full border px-2.5 py-1 font-medium"
          style={step(3)}
        >
          SMS reminders · clause 4.2
        </span>
      </div>
    </figure>
  );
}

/** One question, the way the form asks it. */
export function QuestionMockup({ className }: { className?: string }) {
  const options = ["Up to 100", "100 – 1,000", "1,000 – 10,000", "Not sure"];
  return (
    <figure data-reveal className={cn(FIGURE, className)}>
      <figcaption className="eyebrow">Question 3 of 10</figcaption>
      <p className="mt-2 font-semibold">How many people will use it?</p>
      <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
        {options.map((o, i) => (
          <span
            key={o}
            className={cn(
              "fig-step rounded-xl border px-3 py-2",
              i === 2 &&
                "border-tape/60 bg-tape-soft font-semibold shadow-[0_0_24px_-8px_rgb(11_120_184/0.6)]",
            )}
            style={step(i)}
          >
            {o}
          </span>
        ))}
      </div>
    </figure>
  );
}

/** The team behind the work, by role. */
export function TeamMockup({ className }: { className?: string }) {
  const rows = [
    { role: "Developer", people: 2 },
    { role: "Senior developer (checks AI code)", people: 1 },
    { role: "Tester", people: 1 },
    { role: "Designer", people: 1 },
  ];
  return (
    <figure data-reveal className={cn(FIGURE, className)}>
      <figcaption className="eyebrow">Team needed · example</figcaption>
      <ul className="mt-3 flex flex-col divide-y text-sm">
        {rows.map((r, i) => (
          <li
            key={r.role}
            className="fig-step flex items-center justify-between gap-3 py-2"
            style={step(i)}
          >
            <span>{r.role}</span>
            <PeopleIcons count={r.people} />
          </li>
        ))}
      </ul>
    </figure>
  );
}

/** What the document asks for that the price leaves out. */
export function NotPricedMockup({ className }: { className?: string }) {
  const items = [
    ["Penalties for delay", "page 12"],
    ["One year of warranty", "page 13"],
    ["Source code handover", "page 15"],
  ];
  return (
    <figure
      data-reveal
      className={cn(
        "rounded-2xl border border-warning/25 bg-warning-muted p-5",
        className,
      )}
    >
      <figcaption className="flex items-center gap-2 font-semibold">
        <span
          className="pulse-dot size-2 rounded-full bg-warning"
          aria-hidden="true"
        />
        In the document, but not in this price
      </figcaption>
      <ul className="mt-3 flex flex-col gap-2 text-sm">
        {items.map(([what, page], i) => (
          <li
            key={what}
            className="fig-step flex justify-between gap-3"
            style={step(i)}
          >
            <span>{what}</span>
            <span className="font-mono text-xs text-muted-foreground">
              {page}
            </span>
          </li>
        ))}
      </ul>
    </figure>
  );
}

/**
 * Traceability: a clause on a page, the feature it became, the rate and the cost line, joined
 * by drawn lines.
 */
export function TraceFigure({ className }: { className?: string }) {
  const chain = [
    { label: "Clause 4.2, page 4", value: "“book, move and cancel…”" },
    { label: "Feature", value: "Bookings · Standard" },
    { label: "Work", value: "226 h, of which 38 h check AI work" },
    { label: "Rate card v8", value: "₹1,150 / h, source listed" },
    { label: "Cost line", value: "₹2.6 L" },
  ];
  return (
    <figure data-reveal className={cn(FIGURE, "p-6", className)}>
      <figcaption className="eyebrow">
        Where one number comes from · example
      </figcaption>
      <ol className="relative mt-5 flex flex-col gap-4">
        <span
          aria-hidden="true"
          className="fig-drop absolute top-3 bottom-3 left-[7px] w-0.5 rounded-full bg-tape/60"
        />
        {chain.map((c, i) => (
          <li
            key={c.label}
            className="fig-step relative flex items-baseline gap-4 pl-7"
            style={step(i)}
          >
            <span
              aria-hidden="true"
              className={cn(
                "absolute top-1.5 left-0 size-4 rounded-full border-2 border-tape bg-background",
                i === chain.length - 1 && "bg-tape",
              )}
            />
            <span className="eyebrow w-28 shrink-0">{c.label}</span>
            <span
              className={cn(
                "text-sm",
                i === chain.length - 1 && "font-mono font-semibold text-tape",
              )}
            >
              {c.value}
            </span>
          </li>
        ))}
      </ol>
    </figure>
  );
}

/** Each feature's cost with and without AI tools, as two bars. */
export function FeatureBarsFigure({ className }: { className?: string }) {
  const max = 4;
  return (
    <figure data-reveal className={cn(FIGURE, "p-6", className)}>
      <figcaption className="flex items-center justify-between gap-3">
        <span className="eyebrow">Each feature on its own line</span>
        <span className="flex gap-3 text-[11px] text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <span className="size-2 rounded-full bg-foreground/25" />
            Without AI
          </span>
          <span className="flex items-center gap-1.5">
            <span className="size-2 rounded-full bg-tape" />
            With AI
          </span>
        </span>
      </figcaption>
      <ul className="mt-5 flex flex-col gap-4">
        {EXAMPLE_FEATURES.map((f, i) => (
          <li key={f.name} className="flex flex-col gap-1.5">
            <span className="flex justify-between gap-3 text-sm">
              <span>{f.name}</span>
              <span className="font-mono text-[13px] tabular-nums">
                ₹{f.ai} L
              </span>
            </span>
            <span className="relative h-2.5 overflow-hidden rounded-full bg-foreground/[0.05]">
              <span
                className="fig-bar absolute inset-y-0 left-0 rounded-full bg-foreground/20"
                style={{ ...step(i), width: `${(100 * f.old) / max}%` }}
              />
              <span
                className="fig-bar absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-tape to-tape-2 shadow-[0_0_16px_rgb(11_120_184/0.5)]"
                style={{ ...step(i + 2), width: `${(100 * f.ai) / max}%` }}
              />
            </span>
          </li>
        ))}
      </ul>
    </figure>
  );
}

/** The range widening when three answers are "not sure". */
export function RangeWidenFigure({ className }: { className?: string }) {
  const max = 3_300_000;
  const at = (v: number) => (100 * v) / max;
  const sure = { low: 1_500_000, high: 2_400_000 };
  const unsure = { low: 1_200_000, high: 3_000_000 };
  const likely = 1_900_000;
  return (
    <figure data-reveal className={cn(FIGURE, "group p-6", className)}>
      <figcaption className="flex items-center justify-between gap-3">
        <span className="eyebrow">The same app, answered twice</span>
        <span className="relative text-xs">
          <span className="fig-swap-old rounded-full border px-2.5 py-1">
            All answered
          </span>
          <span className="fig-swap-new absolute top-0 right-0 rounded-full border border-warning/40 bg-warning-muted px-2.5 py-1 whitespace-nowrap text-warning">
            3 × Not sure
          </span>
        </span>
      </figcaption>
      <div className="relative mt-10 mb-12">
        <div className="tape-ticks relative h-8 overflow-hidden rounded-md bg-foreground/[0.06]" />
        <div
          className="fig-range absolute inset-y-0 rounded-md bg-tape/85 shadow-[0_0_40px_-4px_rgb(11_120_184/0.55)] group-[.is-in]:left-(--l2)! group-[.is-in]:w-(--w2)!"
          style={
            {
              left: `${at(sure.low)}%`,
              width: `${at(sure.high) - at(sure.low)}%`,
              "--l2": `${at(unsure.low)}%`,
              "--w2": `${at(unsure.high) - at(unsure.low)}%`,
            } as CSSProperties
          }
        />
        <div
          className="absolute -top-7 flex -translate-x-1/2 flex-col items-center"
          style={{ left: `${at(likely)}%` }}
        >
          <span className="font-mono text-[11px] whitespace-nowrap">
            Likely {lakh(likely)}
          </span>
          <span className="h-[3.25rem] w-px bg-white" />
        </div>
        <div className="absolute inset-x-0 -bottom-3 font-mono text-[11px] text-muted-foreground tabular-nums">
          <span className="fig-swap-old absolute inset-x-0">
            <span
              className="absolute -translate-x-1/2"
              style={{ left: `${at(sure.low)}%` }}
            >
              {lakh(sure.low)}
            </span>
            <span
              className="absolute -translate-x-1/2"
              style={{ left: `${at(sure.high)}%` }}
            >
              {lakh(sure.high)}
            </span>
          </span>
          <span className="fig-swap-new absolute inset-x-0">
            <span
              className="absolute -translate-x-1/2"
              style={{ left: `${at(unsure.low)}%` }}
            >
              {lakh(unsure.low)}
            </span>
            <span
              className="absolute -translate-x-1/2"
              style={{ left: `${at(unsure.high)}%` }}
            >
              {lakh(unsure.high)}
            </span>
          </span>
        </div>
      </div>
      <p className="text-sm text-muted-foreground">
        Find out the answers and calculate again for a narrower range.
      </p>
    </figure>
  );
}
