"use client";

import * as React from "react";
import Link from "next/link";

import {
  ArrowRightIcon,
  FileArrowUpIcon,
  FilePdfIcon,
  ListChecksIcon,
  PencilSimpleLineIcon,
  ReceiptIcon,
  TrashIcon,
  WarningCircleIcon,
} from "@phosphor-icons/react/dist/ssr";

import { useCurrentUser } from "@/components/auth-guard";
import {
  IconTile,
  type IconType,
  type Tone,
} from "@/components/site/illustrations";
import { FlowFigure } from "@/components/site/page-art";
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

const STEPS: { title: string; text: string; icon: IconType; tone: Tone }[] = [
  {
    title: "Upload or describe",
    text: "A PDF or Word requirement document, or a few lines about what the software should do.",
    icon: FilePdfIcon,
    tone: "plain",
  },
  {
    title: "Check and fill the gaps",
    text: "Untick anything wrong, add anything missing, and answer only what the document doesn't say.",
    icon: ListChecksIcon,
    tone: "tape",
  },
  {
    title: "See your cost",
    text: "A total with a likely range, and where the money goes.",
    icon: ReceiptIcon,
    tone: "ai",
  },
];

/** Search appears once the list is long enough to need it. */
const SEARCH_FROM = 6;

/** The two ways to begin: a requirement document, or a few lines of description. */
function StartCards() {
  const cards = [
    {
      href: "/estimate/new?via=upload",
      icon: FileArrowUpIcon,
      tone: "tape" as Tone,
      title: "Upload a requirement document",
      text: "PDF or Word. We find what it asks for, with page numbers, and you check it.",
      cta: "Upload",
    },
    {
      href: "/estimate/new?via=manual",
      icon: PencilSimpleLineIcon,
      tone: "ai" as Tone,
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
          <IconTile icon={card.icon} tone={card.tone} />
          <span className="text-lg font-semibold">{card.title}</span>
          <span className="text-sm text-muted-foreground">{card.text}</span>
          <span className="mt-1 inline-flex items-center gap-1.5 text-sm font-semibold text-primary">
            {card.cta}
            <ArrowRightIcon
              size={16}
              weight="bold"
              aria-hidden="true"
              className="transition-transform group-hover:translate-x-0.5"
            />
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
        <span className="flex min-w-0 items-center gap-3">
          <IconTile
            icon={summary.feasible ? ReceiptIcon : WarningCircleIcon}
            tone={summary.feasible ? "tape" : "warning"}
            size="sm"
          />
          <span className="flex min-w-0 flex-col gap-0.5">
            <span className="truncate font-semibold group-hover:text-primary">
              {summary.name}
            </span>
            <span className="text-xs text-muted-foreground">
              {formatDate(summary.created_at)}
            </span>
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
        <TrashIcon size={16} aria-hidden="true" className="sm:hidden" />
        <span className="max-sm:sr-only">
          {deleting ? "Deleting…" : "Delete"}
        </span>
      </button>
    </li>
  );
}

/** What to do first: three steps, each with its icon, joined by a dashed line. */
function FirstSteps() {
  return (
    <ol className="grid gap-6 sm:grid-cols-3">
      {STEPS.map((step, i) => (
        <li key={step.title} className="relative flex flex-col gap-2">
          <span className="flex items-center gap-3">
            <IconTile icon={step.icon} tone={step.tone} />
            {i < STEPS.length - 1 ? (
              <span
                aria-hidden="true"
                className="hidden flex-1 border-t border-dashed border-primary/30 sm:block"
              />
            ) : null}
          </span>
          <span className="font-semibold">
            <span className="mr-1.5 font-mono text-sm text-muted-foreground">
              {i + 1}
            </span>
            {step.title}
          </span>
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
        <div className="grid items-center gap-10 lg:grid-cols-[1.2fr_0.8fr]">
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
          <FlowFigure className="hidden w-full max-w-sm justify-self-end lg:flex" />
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
