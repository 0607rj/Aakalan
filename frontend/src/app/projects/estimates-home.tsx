"use client";

import * as React from "react";
import Link from "next/link";

import { useCurrentUser } from "@/components/auth-guard";
import { ErrorNotice, Loading } from "@/components/status";
import { Input } from "@/components/ui/input";
import { api, errorText, type QuickSummary } from "@/lib/api/client";
import {
  formatApprox,
  formatDate,
  formatDecimal,
  formatRange,
} from "@/lib/format";
import { useLoad } from "@/lib/use-load";

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

/** Tick marks of a measuring tape: small every 8px, tall every 40px. */
const TICKS: React.CSSProperties = {
  backgroundImage:
    "linear-gradient(90deg, rgb(11 120 184 / 0.4) 1px, transparent 1px), linear-gradient(90deg, rgb(11 120 184 / 0.2) 1px, transparent 1px)",
  backgroundSize: "40px 100%, 8px 45%",
  backgroundRepeat: "repeat-x",
};

function Arrow() {
  return (
    <svg
      viewBox="0 0 16 16"
      aria-hidden="true"
      className="size-4 transition-transform group-hover:translate-x-0.5"
    >
      <path
        d="M3 8h9M8.5 4l4 4-4 4"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function DocIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="size-5">
      <path
        d="M6 2.75h8.5L19.25 7.5v13.75H6zM14.5 2.75V7.5h4.75M9 12h7M9 15.5h7"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function PenIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="size-5">
      <path
        d="M4 20l1-4.5L16.5 4a1.8 1.8 0 012.5 0l1 1a1.8 1.8 0 010 2.5L8.5 19zM14.5 6l3.5 3.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** The two ways to begin: a requirement document, or a few lines of description. */
function StartCards() {
  const cards = [
    {
      href: "/estimate/new?via=upload",
      icon: <DocIcon />,
      title: "Upload a requirement document",
      text: "PDF or Word. We find what it asks for, with page numbers, and you check it.",
      cta: "Upload",
    },
    {
      href: "/estimate/new?via=manual",
      icon: <PenIcon />,
      title: "Describe it or tick features",
      text: "No document? Say what the software should do and we price each feature.",
      cta: "Start",
    },
  ];
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {cards.map((card, i) => (
        <Link
          key={card.href}
          href={card.href}
          className="slab settle group flex flex-col gap-3 p-5 transition-colors hover:border-primary/50 sm:p-6"
          style={{ "--d": i + 1 } as React.CSSProperties}
        >
          <span className="flex size-10 items-center justify-center rounded-lg bg-tape-soft text-primary">
            {card.icon}
          </span>
          <span className="text-lg font-semibold">{card.title}</span>
          <span className="text-sm text-muted-foreground">{card.text}</span>
          <span className="mt-1 inline-flex items-center gap-1.5 text-sm font-semibold text-primary">
            {card.cta}
            <Arrow />
          </span>
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
    <section className="flex flex-col gap-2 rounded-2xl border border-primary/20 bg-primary/5 px-6 py-5">
      <h2 className="font-semibold">How close are our estimates?</h2>
      <p className="text-muted-foreground">{report.message}</p>
      {share !== null ? (
        <p className="text-sm text-muted-foreground">
          Winning prices fell inside our range in {formatDecimal(share, 0)}% of
          projects ({report.with_l1} with a winning price recorded).
        </p>
      ) : null}
      <p className="text-xs text-muted-foreground">
        Based on {report.outcomes} recorded bid result
        {report.outcomes === 1 ? "" : "s"}.
      </p>
    </section>
  );
}

function EstimateRow({
  summary,
  onDelete,
}: {
  summary: QuickSummary;
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
    <li className="group flex items-center rounded-xl border bg-card shadow-[0_1px_2px_rgb(27_36_51/0.04)] transition-colors hover:border-primary/40">
      <Link
        href={`/estimate/${summary.estimate_id}`}
        className="grid min-w-0 flex-1 gap-x-8 gap-y-3 rounded-xl p-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center sm:p-5"
      >
        <span className="flex min-w-0 flex-col gap-0.5">
          <span className="truncate font-semibold group-hover:text-primary">
            {summary.name}
          </span>
          <span className="text-xs text-muted-foreground">
            {formatDate(summary.created_at)}
          </span>
        </span>
        {summary.feasible ? (
          <span className="flex flex-col sm:items-end">
            <span className="text-xl font-semibold tracking-tight text-primary tabular-nums">
              {formatApprox(summary.likely_paise, summary.currency).replace(
                "about ",
                "",
              )}
            </span>
            <span className="text-xs text-muted-foreground tabular-nums">
              range{" "}
              {formatRange(
                summary.low_paise,
                summary.high_paise,
                summary.currency,
              )}
            </span>
          </span>
        ) : (
          <span className="text-sm text-warning sm:justify-self-end">
            Deadline too short, no price yet
          </span>
        )}
      </Link>
      <button
        type="button"
        onClick={remove}
        disabled={deleting}
        className="mr-3 shrink-0 self-start rounded-md px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none sm:mr-4 sm:self-center"
        aria-label={`Delete ${summary.name}`}
      >
        {deleting ? "Deleting…" : "Delete"}
      </button>
    </li>
  );
}

/** What to do first: three numbered stops along a line. */
function FirstSteps() {
  return (
    <ol className="grid gap-6 sm:grid-cols-3">
      {STEPS.map((step, i) => (
        <li key={step.title} className="relative flex flex-col gap-2">
          <span className="flex items-center gap-3">
            <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
              {i + 1}
            </span>
            {i < STEPS.length - 1 ? (
              <span
                aria-hidden="true"
                className="hidden h-2 flex-1 rounded-sm border bg-panel-2 sm:block"
                style={TICKS}
              />
            ) : null}
          </span>
          <span className="font-semibold">{step.title}</span>
          <span className="text-sm text-muted-foreground">{step.text}</span>
        </li>
      ))}
    </ol>
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
  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold">All your estimates</h2>
          <p className="text-sm text-muted-foreground">
            {estimates.length} saved, newest first.
          </p>
        </div>
        {estimates.length >= SEARCH_FROM ? (
          <Input
            type="search"
            aria-label="Search your estimates"
            placeholder="Search your estimates"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="h-10 w-full rounded-lg sm:w-64"
          />
        ) : null}
      </div>
      {shown.length === 0 ? (
        <p className="rounded-xl border border-dashed px-5 py-8 text-center text-sm text-muted-foreground">
          No estimate matches &quot;{query}&quot;.
        </p>
      ) : (
        <ul className="flex flex-col gap-3">
          {shown.map((summary) => (
            <EstimateRow
              key={summary.estimate_id}
              summary={summary}
              onDelete={onDelete}
            />
          ))}
        </ul>
      )}
    </section>
  );
}

export function EstimatesHome() {
  const user = useCurrentUser();
  const loader = React.useCallback(() => api.listQuickEstimates(), []);
  const { state, reload } = useLoad(loader);
  const first = user.full_name.trim().split(/\s+/)[0];

  return (
    <div className="flex flex-col gap-12">
      <section className="flex flex-col gap-8">
        <div className="settle flex flex-col gap-3">
          <p className="eyebrow">{first ? `Hello, ${first}` : "Welcome"}</p>
          <h1 className="font-display max-w-3xl text-4xl sm:text-5xl">
            What will your software cost?
          </h1>
          <p className="max-w-2xl text-lg text-muted-foreground">
            Get a total for building it, launching it and running it for the
            years you need, as a low, likely and high range.
          </p>
        </div>
        <StartCards />
      </section>

      {state.kind === "loading" ? <Loading /> : null}
      {state.kind === "error" ? <ErrorNotice message={state.message} /> : null}
      {state.kind === "ready" && state.data.length === 0 ? (
        <section className="flex flex-col gap-6 border-t pt-10">
          <div>
            <h2 className="text-xl font-semibold">How it works</h2>
            <p className="text-sm text-muted-foreground">
              Your estimates will appear here.
            </p>
          </div>
          <FirstSteps />
        </section>
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
