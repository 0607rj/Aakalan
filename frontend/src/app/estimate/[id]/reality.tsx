"use client";

import * as React from "react";

import { ErrorNotice } from "@/components/status";
import { Button } from "@/components/ui/button";
import {
  api,
  errorText,
  type QuickSummary,
  type SecondOpinionState,
} from "@/lib/api/client";
import { useLoad } from "@/lib/use-load";
import { cn } from "@/lib/utils";

const KIND_LABEL: Record<string, string> = {
  level_too_high: "Level may be too high",
  level_too_low: "Level may be too low",
  missing: "Possibly missing",
  not_needed: "May not be needed",
  unclear: "Unclear",
  other: "Worth checking",
};

function Verdict({ ok, text }: { ok: boolean; text: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium",
        ok ? "bg-ai-soft text-ai" : "bg-warning-muted text-warning",
      )}
    >
      <span aria-hidden>{ok ? "✓" : "!"}</span>
      {text}
    </span>
  );
}

function SecondOpinion({ estimateId }: { estimateId: string }) {
  const loader = React.useCallback(
    () => api.getSecondOpinion(estimateId),
    [estimateId],
  );
  const { state, setData } = useLoad<SecondOpinionState>(loader);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  if (state.kind !== "ready") return null;
  const { ai_available: available, opinion } = state.data;

  async function ask() {
    setBusy(true);
    setError(null);
    try {
      setData(await api.askSecondOpinion(estimateId));
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-3 border-t pt-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="font-medium">AI second opinion</h3>
          <p className="text-sm text-muted-foreground">
            An AI reviewer checks whether the features and their levels fit the
            project. It never changes the price; you decide what to edit.
          </p>
        </div>
        {available ? (
          <Button variant="outline" size="sm" onClick={ask} disabled={busy}>
            {busy
              ? "Reviewing…"
              : opinion
                ? "Ask again"
                : "Get a second opinion"}
          </Button>
        ) : (
          <span className="text-sm text-muted-foreground">
            Available once an AI key is added.
          </span>
        )}
      </div>
      {error ? <ErrorNotice message={error} /> : null}
      {opinion ? (
        <div className="flex flex-col gap-2">
          <Verdict
            ok={opinion.verdict === "looks_right"}
            text={
              opinion.verdict === "looks_right"
                ? "The scope looks right"
                : "Some things to check"
            }
          />
          {opinion.summary ? (
            <p className="text-sm">{opinion.summary}</p>
          ) : null}
          {opinion.flags.length > 0 ? (
            <ul className="flex flex-col gap-1.5 text-sm">
              {opinion.flags.map((f, i) => (
                <li key={i}>
                  <span className="font-medium">
                    {KIND_LABEL[f.kind] ?? f.kind}
                    {f.feature ? `: ${f.feature}` : ""}.
                  </span>{" "}
                  <span className="text-muted-foreground">{f.message}</span>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

/** "Does this price look real?" as one line in the price card; the checks open below it. */
export function RealityCheck({ summary }: { summary: QuickSummary }) {
  const reality = summary.reality;
  if (!reality) return null;
  const ok = reality.verdict === "realistic";
  const passed = reality.checks.filter((c) => c.ok).length;
  return (
    <details className="group/real text-sm">
      <summary className="flex w-fit cursor-pointer list-none gap-2 [&::-webkit-details-marker]:hidden">
        <span
          aria-hidden
          className={cn("font-semibold", ok ? "text-success" : "text-warning")}
        >
          {ok ? "✓" : "⚠"}
        </span>
        <span className={cn(!ok && "font-medium")}>
          {ok ? "Looks realistic" : "Worth a second look"}: {passed} of{" "}
          {reality.checks.length} checks pass{" "}
          <span className="text-primary group-open/real:hidden">
            how we checked
          </span>
        </span>
      </summary>
      <div className="mt-3 flex flex-col gap-3 pl-5">
        <ul className="flex flex-col gap-2">
          {reality.checks.map((c) => (
            <li key={c.key} className="flex gap-2">
              <span
                aria-hidden
                className={cn(
                  "mt-[0.5em] size-1.5 shrink-0 rounded-full",
                  c.ok ? "bg-success" : "bg-warning",
                )}
              />
              <span>
                <span className="font-medium">{c.title}.</span>{" "}
                <span className="text-muted-foreground">{c.detail}</span>
              </span>
            </li>
          ))}
        </ul>
        <SecondOpinion estimateId={summary.estimate_id} />
      </div>
    </details>
  );
}
