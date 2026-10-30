import { cn } from "@/lib/utils";

import { Kicker } from "./sections";

/** The same four features as the home page's example, priced both ways (illustration only). */
const LINES = [
  { name: "Bookings", without: 3.3, withAi: 2.6 },
  { name: "Online payment", without: 1.4, withAi: 1.1 },
  { name: "Mobile app", without: 3.9, withAi: 3.0 },
  { name: "SMS reminders", without: 1.1, withAi: 0.9 },
];

const TOTAL_WITHOUT = 9.7;
const TOTAL_WITH = 7.6;
const LONGEST = Math.max(...LINES.map((l) => l.without));

const lakh = (v: number) => `₹${v.toFixed(1)} L`;

/**
 * The main point of the price, said once and plainly: the same software priced the old way
 * (every line typed by hand) and the way teams build now, with AI tools; per feature, a faint
 * bar for the old price and an orange one for the new. Sample figures, marked as such.
 */
export function AiCompare({ className }: { className?: string }) {
  return (
    <div
      data-reveal
      className={cn(
        "dark-card warm grid gap-10 p-[clamp(28px,4vw,48px)] lg:grid-cols-[0.9fr_1.1fr] lg:gap-14",
        className,
      )}
    >
      <div className="flex flex-col">
        <Kicker tone="dark">Why the price is lower</Kicker>
        <h2 className="font-wide mt-5 text-[clamp(2rem,4vw,3rem)] leading-[1.08]">
          Same software. Less to build now.{" "}
          <span className="text-white/50">The saving is in the price.</span>
        </h2>
        <p className="mt-5 max-w-[30rem] text-[1.05rem] text-white/72">
          AI tools now write much of the code. Aakalan takes the hours they save
          off each feature, task by task, and adds back the time people spend
          checking the AI&apos;s work. A spreadsheet prices every line as if it
          were typed by hand.
        </p>
        <dl className="mt-auto grid grid-cols-2 gap-3 pt-10">
          <div className="rounded-2xl border border-white/12 bg-white/6 px-5 py-4">
            <dt className="text-sm text-white/60">Without AI tools</dt>
            <dd className="font-wide mt-1 text-[clamp(1.6rem,3vw,2.2rem)] text-white/55 line-through decoration-2">
              {lakh(TOTAL_WITHOUT)}
            </dd>
          </div>
          <div className="rounded-2xl bg-white px-5 py-4 text-foreground">
            <dt className="text-sm text-muted-foreground">With AI tools</dt>
            <dd className="font-wide mt-1 text-[clamp(1.6rem,3vw,2.2rem)] text-tape-bright">
              {lakh(TOTAL_WITH)}
            </dd>
          </div>
        </dl>
      </div>

      <div className="flex flex-col justify-center">
        <div className="flex justify-between pb-3 font-mono text-[11px] tracking-[0.06em] text-white/50 uppercase">
          <span>Feature</span>
          <span>Without · with AI tools</span>
        </div>
        <ul className="flex flex-col">
          {LINES.map((l) => (
            <li key={l.name} className="border-t border-white/10 py-4">
              <div className="flex items-baseline justify-between gap-3">
                <span className="font-medium">{l.name}</span>
                <span className="font-mono text-sm tabular-nums">
                  <s className="text-white/45">{lakh(l.without)}</s>{" "}
                  <b className="font-medium text-peach">{lakh(l.withAi)}</b>
                </span>
              </div>
              <div
                aria-hidden="true"
                className="relative mt-2.5 h-2.5 rounded-full bg-white/[0.08]"
                style={{ width: `${(l.without / LONGEST) * 100}%` }}
              >
                <span
                  className="absolute inset-y-0 left-0 rounded-full bg-tape-bright"
                  style={{ width: `${(l.withAi / l.without) * 100}%` }}
                />
              </div>
            </li>
          ))}
        </ul>
        <p className="mt-5 text-[13px] text-white/50">
          *Sample figures, for illustration. Your own estimate can show both
          prices for every feature.
        </p>
      </div>
    </div>
  );
}
