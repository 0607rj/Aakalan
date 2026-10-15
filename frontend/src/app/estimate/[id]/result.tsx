"use client";

import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { ErrorNotice, Loading } from "@/components/status";
import { api, type QuickSummary } from "@/lib/api/client";
import { formatDate, formatDecimal, formatPaise } from "@/lib/format";
import { useLoad } from "@/lib/use-load";

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-lg font-semibold">{value}</span>
    </div>
  );
}

function Headline({ summary }: { summary: QuickSummary }) {
  const years = summary.support_years;
  return (
    <section className="flex flex-col gap-6 rounded-2xl border bg-card px-6 py-8 shadow-sm sm:px-10">
      <div className="flex flex-col gap-1">
        <span className="text-base text-muted-foreground">
          Most likely total cost
        </span>
        <span className="text-5xl font-semibold tracking-tight text-primary sm:text-6xl">
          {formatPaise(summary.likely_paise)}
        </span>
        <span className="text-base text-muted-foreground">
          Could range from{" "}
          <strong className="text-foreground">
            {formatPaise(summary.low_paise)}
          </strong>{" "}
          to{" "}
          <strong className="text-foreground">
            {formatPaise(summary.high_paise)}
          </strong>
        </span>
      </div>
      <div className="flex flex-wrap gap-x-10 gap-y-4 border-t pt-5">
        <Fact
          label="Time to build"
          value={`about ${formatDecimal(summary.build_months, 1)} months`}
        />
        <Fact
          label="Support included"
          value={`${years} year${years === 1 ? "" : "s"} after launch`}
        />
        <Fact
          label="Cost to build the software only"
          value={formatPaise(summary.build_only_paise)}
        />
      </div>
    </section>
  );
}

function MoneyBreakdown({ summary }: { summary: QuickSummary }) {
  const risk = summary.risk_allowance_paise;
  return (
    <section className="flex flex-col gap-5 rounded-2xl border bg-card px-6 py-6 shadow-sm sm:px-8">
      <h2 className="text-lg font-semibold">Where the money goes</h2>
      <ul className="flex flex-col gap-4">
        {summary.parts.map((part) => (
          <li key={part.key} className="flex flex-col gap-1.5">
            <div className="flex flex-wrap items-baseline justify-between gap-x-4">
              <span className="font-medium">{part.label}</span>
              <span className="tabular-nums">
                <span className="font-semibold">
                  {formatPaise(part.amount_paise)}
                </span>{" "}
                <span className="text-sm text-muted-foreground">
                  ({part.share_percent}%)
                </span>
              </span>
            </div>
            <div className="h-3 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary"
                style={{ width: `${Math.max(0, part.share_percent)}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
      {risk !== null && risk > 0 ? (
        <p className="border-t pt-4 text-sm text-muted-foreground">
          Planned cost{" "}
          <strong className="text-foreground">
            {formatPaise(summary.planned_paise)}
          </strong>{" "}
          + allowance for risks{" "}
          <strong className="text-foreground">{formatPaise(risk)}</strong> ={" "}
          most likely{" "}
          <strong className="text-foreground">
            {formatPaise(summary.likely_paise)}
          </strong>
        </p>
      ) : null}
      <p className="text-sm text-muted-foreground">
        The cost to build the software only, before running costs, taxes and
        margin, is{" "}
        <strong className="text-foreground">
          {formatPaise(summary.build_only_paise)}
        </strong>
        .
      </p>
    </section>
  );
}

function SummaryView({ summary }: { summary: QuickSummary }) {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <Link
          href="/projects"
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          ← Your estimates
        </Link>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">
          {summary.name}
        </h1>
        <p className="text-sm text-muted-foreground">
          Estimated on {formatDate(summary.created_at)}
        </p>
      </div>

      {summary.indicative ? (
        <p className="rounded-xl border border-warning/30 bg-warning-muted px-4 py-3 text-sm text-warning">
          These figures use sample prices, so treat them as a rough guide.
        </p>
      ) : null}

      {summary.feasible ? (
        <>
          <Headline summary={summary} />
          <MoneyBreakdown summary={summary} />
          {summary.biggest_uncertainty ? (
            <section className="rounded-2xl border border-primary/20 bg-primary/5 px-6 py-5">
              <h2 className="font-semibold">What could change the price</h2>
              <p className="mt-1 text-muted-foreground">
                {summary.biggest_uncertainty}
              </p>
            </section>
          ) : null}
        </>
      ) : (
        <section className="flex flex-col items-start gap-4 rounded-2xl border bg-card px-6 py-8 shadow-sm sm:px-10">
          <h2 className="text-xl font-semibold">
            The deadline is too short to give a price
          </h2>
          <p className="max-w-2xl text-muted-foreground">{summary.message}</p>
          <Link
            href="/estimate/new"
            className="inline-flex h-11 items-center rounded-lg bg-primary px-5 font-medium text-primary-foreground hover:bg-primary/90"
          >
            Change the deadline
          </Link>
        </section>
      )}

      <section className="rounded-2xl border bg-card px-6 py-6 shadow-sm sm:px-8">
        <h2 className="text-lg font-semibold">What you asked for</h2>
        <ul className="mt-3 grid gap-2 sm:grid-cols-2">
          {summary.features.map((feature) => (
            <li key={feature} className="flex items-start gap-2">
              <span className="text-primary">✓</span>
              <span>{feature}</span>
            </li>
          ))}
        </ul>
      </section>

      <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
        <Link
          href="/estimate/new"
          className="inline-flex h-11 items-center rounded-lg bg-primary px-5 font-medium text-primary-foreground hover:bg-primary/90"
        >
          Start another estimate
        </Link>
        <Link
          href={`/projects/${summary.project_id}?tab=estimate`}
          className="text-sm text-muted-foreground underline hover:text-foreground"
        >
          See detailed breakdown (for experts)
        </Link>
      </div>
    </div>
  );
}

export function EstimateResult() {
  const params = useParams<{ id: string }>();
  const estimateId = params.id;
  const loader = React.useCallback(
    () => api.getEstimateSummary(estimateId),
    [estimateId],
  );
  const { state } = useLoad(loader);
  if (state.kind === "loading")
    return <Loading>Loading your estimate…</Loading>;
  if (state.kind === "error") return <ErrorNotice message={state.message} />;
  return <SummaryView summary={state.data} />;
}
