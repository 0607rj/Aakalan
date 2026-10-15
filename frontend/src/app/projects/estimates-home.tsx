"use client";

import * as React from "react";
import Link from "next/link";

import { ErrorNotice, Loading } from "@/components/status";
import { api, type QuickSummary } from "@/lib/api/client";
import { formatDate, formatPaise } from "@/lib/format";
import { useLoad } from "@/lib/use-load";

const STEPS = [
  {
    title: "Tell us what to build",
    text: "Tick the features you need, in plain words.",
  },
  {
    title: "Answer a few questions",
    text: "How many users, how long to support it, and a deadline if any.",
  },
  {
    title: "See your cost",
    text: "A total with a likely range, and where the money goes.",
  },
];

function EstimateCard({ summary }: { summary: QuickSummary }) {
  return (
    <Link
      href={`/estimate/${summary.estimate_id}`}
      className="group flex flex-col gap-2 rounded-xl border bg-card p-5 shadow-sm transition-colors hover:border-primary/40 hover:bg-muted/40"
    >
      <span className="font-semibold group-hover:text-primary">
        {summary.name}
      </span>
      {summary.feasible ? (
        <>
          <span className="text-2xl font-semibold tracking-tight">
            {formatPaise(summary.likely_paise)}
          </span>
          <span className="text-sm text-muted-foreground">
            most likely · range {formatPaise(summary.low_paise)} –{" "}
            {formatPaise(summary.high_paise)}
          </span>
        </>
      ) : (
        <span className="text-sm text-warning">
          Deadline too short — no price yet
        </span>
      )}
      <span className="text-xs text-muted-foreground">
        {formatDate(summary.created_at)}
      </span>
    </Link>
  );
}

export function EstimatesHome() {
  const loader = React.useCallback(() => api.listQuickEstimates(), []);
  const { state } = useLoad(loader);

  return (
    <div className="flex flex-col gap-10">
      <section className="flex flex-col items-start gap-4 rounded-2xl border bg-card px-6 py-10 shadow-sm sm:px-10">
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
          What will your software cost?
        </h1>
        <p className="max-w-2xl text-base text-muted-foreground">
          Describe the software in plain words and get a total cost — building
          it, launching it and running it for the years you need — with a likely
          range.
        </p>
        <Link
          href="/estimate/new"
          className="mt-2 inline-flex h-12 items-center rounded-lg bg-primary px-6 text-base font-medium text-primary-foreground shadow-sm hover:bg-primary/90"
        >
          Start a new estimate
        </Link>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold">Your estimates</h2>
        {state.kind === "loading" ? <Loading /> : null}
        {state.kind === "error" ? (
          <ErrorNotice message={state.message} />
        ) : null}
        {state.kind === "ready" && state.data.length === 0 ? (
          <ol className="grid gap-4 sm:grid-cols-3">
            {STEPS.map((step, i) => (
              <li key={step.title} className="rounded-xl border bg-card p-5">
                <span className="text-sm font-medium text-primary">
                  Step {i + 1}
                </span>
                <p className="mt-1 font-semibold">{step.title}</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  {step.text}
                </p>
              </li>
            ))}
          </ol>
        ) : null}
        {state.kind === "ready" && state.data.length > 0 ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {state.data.map((summary) => (
              <EstimateCard key={summary.estimate_id} summary={summary} />
            ))}
          </div>
        ) : null}
      </section>

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
