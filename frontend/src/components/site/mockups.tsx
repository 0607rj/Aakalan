/**
 * Illustrations made of the product's own pieces: the cost range as a measuring tape, a
 * requirement document with the line a feature came from, a question, the team. Figures are
 * a worked example (a small clinic booking app), labelled as such wherever they appear.
 */
import { cn } from "@/lib/utils";

const LAKH = 100_000;

function lakh(rupees: number): string {
  return `₹${(rupees / LAKH).toLocaleString("en-IN", { maximumFractionDigits: 1 })} L`;
}

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
        <span className="rounded-full bg-foreground px-2.5 py-1 text-xs font-semibold whitespace-nowrap text-primary-foreground tabular-nums">
          Likely {lakh(likely)}
        </span>
        <span className="h-3 w-0.5 bg-foreground" />
      </div>
      {/* tape */}
      <div className="tape-ticks relative h-8 overflow-hidden rounded-md bg-tape shadow-[inset_0_-2px_0_rgb(23_32_58/0.15)]">
        <div
          className="absolute inset-y-0 bg-foreground/15"
          style={{ left: at(low), width: `calc(${at(high)} - ${at(low)})` }}
        />
        <div
          className="absolute inset-y-0 w-0.5 bg-foreground"
          style={{ left: at(likely) }}
        />
      </div>
      {/* ends of the range */}
      <span
        className="absolute bottom-0 -translate-x-1/2 text-xs text-muted-foreground tabular-nums"
        style={{ left: at(low) }}
      >
        {lakh(low)}
      </span>
      <span
        className="absolute bottom-0 -translate-x-1/2 text-xs text-muted-foreground tabular-nums"
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

/** The hero picture: what an estimate looks like. */
export function EstimateMockup({ className }: { className?: string }) {
  const features = [
    { name: "Bookings and appointments", level: "Standard", ai: 2.6, old: 3.3 },
    { name: "Online fee payment", level: "Basic", ai: 1.1, old: 1.4 },
    { name: "Mobile app", level: "Basic", ai: 3.0, old: 3.9 },
    { name: "SMS reminders", level: "", ai: 0.9, old: 1.1 },
  ];
  return (
    <figure
      className={cn(
        "rounded-[22px] border bg-card p-5 shadow-[0_24px_60px_-28px_rgb(23_32_58/0.35)] sm:p-6",
        className,
      )}
    >
      <figcaption className="flex items-start justify-between gap-3">
        <span className="flex flex-col">
          <span className="text-sm text-muted-foreground">
            Example estimate
          </span>
          <span className="font-semibold">Clinic booking app</span>
        </span>
        <span className="rounded-full bg-ai-soft px-2.5 py-1 text-xs font-semibold text-ai">
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
          <tr className="text-left text-xs text-muted-foreground">
            <th className="pb-2 font-medium">Feature</th>
            <th className="pb-2 text-right font-medium">Without AI</th>
            <th className="pb-2 text-right font-medium">With AI</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {features.map((f) => (
            <tr key={f.name}>
              <td className="py-2 pr-2">
                {f.name}
                {f.level ? (
                  <span className="ml-2 rounded-full border px-2 py-0.5 text-[11px] text-muted-foreground">
                    {f.level}
                  </span>
                ) : null}
              </td>
              <td className="py-2 text-right text-muted-foreground tabular-nums line-through decoration-muted-foreground/40">
                ₹{f.old} L
              </td>
              <td className="py-2 text-right font-semibold tabular-nums">
                ₹{f.ai} L
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-4 flex items-center gap-3 rounded-xl bg-muted px-3 py-2.5 text-sm">
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
          className="size-6 rounded-full border-2 border-card bg-secondary p-0.5"
        >
          <circle cx="12" cy="9" r="4" fill="#17203a" />
          <path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6" fill="#17203a" />
        </svg>
      ))}
    </span>
  );
}

/** A page of a requirement document, with the line a feature was found in. */
export function DocumentMockup({ className }: { className?: string }) {
  return (
    <figure
      className={cn(
        "relative rounded-2xl border bg-card p-5 shadow-[0_16px_40px_-24px_rgb(23_32_58/0.35)]",
        className,
      )}
    >
      <figcaption className="text-xs text-muted-foreground">
        requirement-document.pdf, page 4
      </figcaption>
      <div className="mt-3 flex flex-col gap-2" aria-hidden="true">
        <div className="h-2 w-3/4 rounded bg-muted" />
        <div className="h-2 w-full rounded bg-muted" />
        <div className="h-2 w-5/6 rounded bg-muted" />
      </div>
      <p className="mt-3 rounded-md bg-tape-soft px-2 py-1.5 text-sm">
        <span className="font-semibold">4.2</span> Patients shall book, move and
        cancel appointments online, and receive an SMS reminder.
      </p>
      <div className="mt-3 flex flex-col gap-2" aria-hidden="true">
        <div className="h-2 w-full rounded bg-muted" />
        <div className="h-2 w-2/3 rounded bg-muted" />
      </div>
      <div className="mt-4 flex flex-wrap gap-2 text-xs">
        <span className="rounded-full bg-foreground px-2.5 py-1 font-semibold text-primary-foreground">
          Bookings found in clause 4.2
        </span>
        <span className="rounded-full border px-2.5 py-1 font-medium">
          SMS reminders found in clause 4.2
        </span>
      </div>
    </figure>
  );
}

/** One question, the way the form asks it. */
export function QuestionMockup({ className }: { className?: string }) {
  const options = ["Up to 100", "100 – 1,000", "1,000 – 10,000", "Not sure"];
  return (
    <figure
      className={cn(
        "rounded-2xl border bg-card p-5 shadow-[0_16px_40px_-24px_rgb(23_32_58/0.35)]",
        className,
      )}
    >
      <figcaption className="text-xs text-muted-foreground">
        Question 3 of 10
      </figcaption>
      <p className="mt-2 font-semibold">How many people will use it?</p>
      <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
        {options.map((o, i) => (
          <span
            key={o}
            className={cn(
              "rounded-xl border px-3 py-2",
              i === 2 && "border-foreground bg-foreground/[0.04] font-semibold",
            )}
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
    { role: "Developer", people: 2, ai: true },
    { role: "Senior developer (checks AI code)", people: 1, ai: true },
    { role: "Tester", people: 1, ai: false },
    { role: "Designer", people: 1, ai: false },
  ];
  return (
    <figure
      className={cn(
        "rounded-2xl border bg-card p-5 shadow-[0_16px_40px_-24px_rgb(23_32_58/0.35)]",
        className,
      )}
    >
      <figcaption className="text-xs text-muted-foreground">
        Team needed, example
      </figcaption>
      <ul className="mt-3 flex flex-col divide-y text-sm">
        {rows.map((r) => (
          <li
            key={r.role}
            className="flex items-center justify-between gap-3 py-2"
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
  return (
    <figure
      className={cn(
        "rounded-2xl border border-warning/30 bg-warning-muted p-5",
        className,
      )}
    >
      <figcaption className="font-semibold">
        In the document, but not in this price
      </figcaption>
      <ul className="mt-3 flex flex-col gap-2 text-sm">
        <li>Penalties for delay, page 12</li>
        <li>One year of warranty, page 13</li>
        <li>Source code handover, page 15</li>
      </ul>
    </figure>
  );
}
