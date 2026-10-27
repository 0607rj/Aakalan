"use client";

import * as React from "react";
import Link from "next/link";

import {
  ArrowRightIcon,
  FileArrowUpIcon,
  MagnifyingGlassIcon,
  PencilSimpleLineIcon,
  TrashIcon,
  WarningCircleIcon,
} from "@phosphor-icons/react/dist/ssr";

import { useCurrentUser } from "@/components/auth-guard";
import { ErrorNotice, Loading } from "@/components/status";
import { api, errorText, type QuickSummary } from "@/lib/api/client";
import {
  formatApprox,
  formatDate,
  formatDecimal,
  formatRange,
} from "@/lib/format";
import { useLoad } from "@/lib/use-load";
import { cn } from "@/lib/utils";

const STEPS = [
  {
    title: "Upload or describe",
    text: "A PDF or Word requirement document, or a few lines about what the software should do.",
  },
  {
    title: "Check and fill the gaps",
    text: "Untick anything wrong, add anything missing, and answer only what the document doesn't say.",
  },
  {
    title: "See your cost",
    text: "A total with a likely range, and where the money goes.",
  },
];

/** Search appears once the list is long enough to need it. */
const SEARCH_FROM = 6;

/** The two ways to begin, as one surface split in two (no icon tiles, no big cards). */
function StartStrip() {
  const ways = [
    {
      href: "/estimate/new?via=upload",
      icon: FileArrowUpIcon,
      title: "Upload a requirement document",
      text: "PDF or Word. Each feature keeps the page it came from.",
    },
    {
      href: "/estimate/new?via=manual",
      icon: PencilSimpleLineIcon,
      title: "Describe it or tick features",
      text: "No document? A few lines about the software are enough.",
    },
  ];
  return (
    <div className="settle grid grid-cols-1 overflow-hidden rounded-xl border bg-card sm:grid-cols-2">
      {ways.map((way, i) => (
        <Link
          key={way.href}
          href={way.href}
          className={cn(
            "group flex items-start gap-4 p-5 transition-colors hover:bg-panel-2 focus-visible:bg-panel-2 focus-visible:outline-none sm:p-6",
            i > 0 && "border-t sm:border-t-0 sm:border-l",
          )}
        >
          <way.icon
            size={22}
            weight="duotone"
            aria-hidden="true"
            className="mt-0.5 shrink-0 text-tape"
          />
          <span className="flex min-w-0 flex-1 flex-col gap-1">
            <span className="font-semibold">{way.title}</span>
            <span className="text-sm text-muted-foreground">{way.text}</span>
          </span>
          <ArrowRightIcon
            size={18}
            weight="bold"
            aria-hidden="true"
            className="mt-0.5 shrink-0 text-muted-foreground transition-[transform,color] group-hover:translate-x-1 group-hover:text-tape"
          />
        </Link>
      ))}
    </div>
  );
}

/** The owner's check of the estimates against real results; nobody else sees it. */
function CalibrationCard() {
  const user = useCurrentUser();
  if (!user.is_owner) return null;
  return <CalibrationReport />;
}

function CalibrationReport() {
  const loader = React.useCallback(() => api.calibration(), []);
  const { state } = useLoad(loader);
  if (state.kind !== "ready" || state.data.outcomes === 0) return null;
  const report = state.data;
  const share = report.l1_within_range_share_percent;
  return (
    <section className="flex flex-col gap-2 border-t pt-8">
      <p className="eyebrow">Only you see this</p>
      <h2 className="font-wide text-xl">How close are our estimates?</h2>
      <p className="max-w-2xl text-muted-foreground">{report.message}</p>
      {share !== null ? (
        <p className="text-sm text-muted-foreground">
          Winning prices fell inside our range in {formatDecimal(share, 0)}% of
          projects ({report.with_l1} with a winning price recorded), from{" "}
          {report.outcomes} recorded bid result
          {report.outcomes === 1 ? "" : "s"}.
        </p>
      ) : null}
    </section>
  );
}

/** Where a price sits on the shared scale of the list: a log scale, so a ₹5 L tool and a
 * ₹1 Cr portal both stay readable. */
type Scale = (paise: number) => number;

function makeScale(estimates: QuickSummary[]): Scale | null {
  const ends = estimates
    .filter((e) => e.feasible && e.low_paise && e.high_paise)
    .flatMap((e) => [e.low_paise as number, e.high_paise as number]);
  if (ends.length === 0) return null;
  const lo = Math.log(Math.min(...ends));
  const hi = Math.log(Math.max(...ends));
  if (hi - lo < 1e-9) return () => 50;
  // a little room at both ends so no mark sits on the edge
  return (paise) => 4 + ((Math.log(paise) - lo) / (hi - lo)) * 92;
}

/** Low to high as a band on the measuring line, the likely price as the mark. */
function RangeBar({ summary, scale }: { summary: QuickSummary; scale: Scale }) {
  const { low_paise: low, likely_paise: likely, high_paise: high } = summary;
  if (!low || !likely || !high) return null;
  const left = scale(low);
  const right = scale(high);
  return (
    <span
      aria-hidden="true"
      className="relative block h-1.5 w-full rounded-full bg-muted"
    >
      <span
        className="absolute inset-y-0 rounded-full bg-tape/25"
        style={{ left: `${left}%`, width: `${Math.max(right - left, 1)}%` }}
      />
      <span
        className="absolute top-1/2 h-3.5 w-[3px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-warm"
        style={{ left: `${scale(likely)}%` }}
      />
    </span>
  );
}

/** "6 features · 4 months · 3 years' support" */
function scopeLine(summary: QuickSummary): string {
  const parts = [
    summary.features.length
      ? `${summary.features.length} feature${summary.features.length === 1 ? "" : "s"}`
      : null,
    summary.build_months ? `${summary.build_months} months to build` : null,
    summary.support_years
      ? `${summary.support_years} year${summary.support_years === 1 ? "" : "s"} of support`
      : null,
  ];
  return parts.filter(Boolean).join(" · ");
}

const short = (paise: number | null, currency: string) =>
  formatApprox(paise, currency).replace("about ", "");

const COLUMNS =
  "md:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)_7.5rem_2.25rem] md:gap-8";

function EstimateRow({
  summary,
  scale,
  onDelete,
}: {
  summary: QuickSummary;
  scale: Scale | null;
  onDelete: () => void;
}) {
  const [deleting, setDeleting] = React.useState(false);
  async function remove() {
    if (
      !window.confirm(
        `Delete "${summary.name}"? Its estimates and uploaded documents are removed. What the estimator has learned is kept.`,
      )
    )
      return;
    setDeleting(true);
    try {
      await api.deleteProject(summary.project_id);
      onDelete();
    } catch (e) {
      setDeleting(false);
      window.alert(errorText(e));
    }
  }
  return (
    <li className="group relative border-b last:border-b-0">
      <Link
        href={`/estimate/${summary.estimate_id}`}
        className={cn(
          "grid grid-cols-1 gap-3 px-5 py-4 pr-14 transition-colors hover:bg-panel-2 focus-visible:bg-panel-2 focus-visible:outline-none md:items-center md:pr-5",
          COLUMNS,
        )}
      >
        <span className="flex min-w-0 flex-col gap-0.5">
          <span className="truncate font-semibold group-hover:text-tape">
            {summary.name}
          </span>
          <span className="truncate text-xs text-muted-foreground">
            {formatDate(summary.created_at)}
            {scopeLine(summary) ? ` · ${scopeLine(summary)}` : ""}
          </span>
        </span>
        {summary.feasible ? (
          <>
            <span className="flex flex-col gap-1.5">
              {scale ? <RangeBar summary={summary} scale={scale} /> : null}
              <span className="text-xs text-muted-foreground tabular-nums">
                {formatRange(
                  summary.low_paise,
                  summary.high_paise,
                  summary.currency,
                )}
              </span>
            </span>
            <span className="text-lg font-semibold tracking-tight tabular-nums md:text-right">
              {short(summary.likely_paise, summary.currency)}
            </span>
          </>
        ) : (
          <span className="flex items-center gap-2 text-sm text-warning md:col-span-2">
            <WarningCircleIcon size={16} weight="bold" aria-hidden="true" />
            Deadline too short, no price yet
          </span>
        )}
        <span className="hidden md:block" />
      </Link>
      <button
        type="button"
        onClick={remove}
        disabled={deleting}
        title="Delete"
        aria-label={`Delete ${summary.name}`}
        className="absolute top-4 right-3 flex size-8 items-center justify-center rounded-md text-muted-foreground transition-[opacity,color,background-color] hover:bg-destructive/10 hover:text-destructive focus-visible:opacity-100 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none md:top-1/2 md:right-4 md:-translate-y-1/2 md:opacity-0 md:group-hover:opacity-100"
      >
        <TrashIcon size={16} aria-hidden="true" />
      </button>
    </li>
  );
}

function EstimateList({
  estimates,
  onDelete,
}: {
  estimates: QuickSummary[];
  onDelete: () => void;
}) {
  const [query, setQuery] = React.useState("");
  const shown = estimates.filter((e) =>
    e.name.toLowerCase().includes(query.trim().toLowerCase()),
  );
  const scale = makeScale(estimates);
  return (
    <section className="flex flex-col overflow-hidden rounded-xl border bg-card">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b px-5 py-3.5">
        <h2 className="font-semibold">
          All estimates{" "}
          <span className="font-normal text-muted-foreground">
            {estimates.length}
          </span>
        </h2>
        {estimates.length >= SEARCH_FROM ? (
          <label className="flex h-9 w-full items-center gap-2 rounded-lg border bg-background px-3 text-sm focus-within:ring-2 focus-within:ring-ring sm:w-64">
            <MagnifyingGlassIcon
              size={15}
              aria-hidden="true"
              className="text-muted-foreground"
            />
            <input
              type="search"
              aria-label="Search your estimates"
              placeholder="Search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="min-w-0 flex-1 bg-transparent outline-none placeholder:text-muted-foreground"
            />
          </label>
        ) : null}
      </div>
      <div
        className={cn(
          "eyebrow hidden border-b bg-panel-2 px-5 py-2.5 md:grid",
          COLUMNS,
        )}
      >
        <span>Estimate</span>
        <span>Low to high</span>
        <span className="text-right">Likely</span>
        <span />
      </div>
      {shown.length === 0 ? (
        <p className="px-5 py-10 text-center text-sm text-muted-foreground">
          No estimate matches &quot;{query}&quot;.
        </p>
      ) : (
        <ul>
          {shown.map((summary) => (
            <EstimateRow
              key={summary.estimate_id}
              summary={summary}
              scale={scale}
              onDelete={onDelete}
            />
          ))}
        </ul>
      )}
    </section>
  );
}

/** What happens, for someone with no estimate yet: three steps as ruled columns. */
function FirstSteps() {
  return (
    <section className="flex flex-col gap-6 pt-2">
      <p className="eyebrow">Your estimates will appear here</p>
      <ol className="grid grid-cols-1 gap-8 sm:grid-cols-3">
        {STEPS.map((step, i) => (
          <li
            key={step.title}
            className="flex flex-col gap-2 border-t-2 border-foreground/10 pt-5 first:border-tape"
          >
            <span className="font-mono text-sm text-muted-foreground">
              0{i + 1}
            </span>
            <span className="font-wide text-lg">{step.title}</span>
            <span className="text-sm text-muted-foreground">{step.text}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}

/** "5 estimates · about ₹2.15 Cr likely in all" (only when every one is in one currency). */
function Totals({ estimates }: { estimates: QuickSummary[] }) {
  const priced = estimates.filter((e) => e.feasible && e.likely_paise);
  const currencies = new Set(priced.map((e) => e.currency));
  const total = priced.reduce((sum, e) => sum + (e.likely_paise ?? 0), 0);
  return (
    <p className="text-muted-foreground">
      {estimates.length} estimate{estimates.length === 1 ? "" : "s"}
      {priced.length > 0 && currencies.size === 1
        ? ` · ${short(total, priced[0].currency)} likely in all`
        : ""}
    </p>
  );
}

export function EstimatesHome() {
  const user = useCurrentUser();
  const loader = React.useCallback(() => api.listQuickEstimates(), []);
  const { state, reload } = useLoad(loader);
  const first = user.full_name.trim().split(/\s+/)[0];

  return (
    <div className="flex flex-col gap-8">
      <header className="settle flex flex-col gap-2 border-b pb-8">
        <p className="eyebrow">{first ? `Hello, ${first}` : "Welcome"}</p>
        <h1 className="font-wide text-[2rem] leading-tight sm:text-[2.5rem]">
          Your estimates
        </h1>
        {state.kind === "ready" && state.data.length > 0 ? (
          <Totals estimates={state.data} />
        ) : (
          <p className="max-w-xl text-muted-foreground">
            The cost of building, launching and running software, as a low,
            likely and high range.
          </p>
        )}
      </header>

      <StartStrip />

      {state.kind === "loading" ? <Loading /> : null}
      {state.kind === "error" ? <ErrorNotice message={state.message} /> : null}
      {state.kind === "ready" && state.data.length === 0 ? (
        <FirstSteps />
      ) : null}
      {state.kind === "ready" && state.data.length > 0 ? (
        <EstimateList estimates={state.data} onDelete={reload} />
      ) : null}

      <CalibrationCard />

      <p className="text-sm text-muted-foreground">
        Cost experts can use the{" "}
        <Link href="/projects/all" className="underline hover:text-foreground">
          detailed projects
        </Link>{" "}
        workspace.
      </p>
    </div>
  );
}
