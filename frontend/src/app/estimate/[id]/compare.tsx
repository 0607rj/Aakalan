"use client";

import * as React from "react";

import { ErrorNotice } from "@/components/status";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  api,
  errorText,
  type Scenario,
  type ScenarioResult,
} from "@/lib/api/client";
import { formatPaise } from "@/lib/format";
import { cn } from "@/lib/utils";

interface Preset {
  id: string;
  label: string;
  overrides: Record<string, string | number | boolean>;
  /** Only offered for these countries (all when omitted). */
  countries?: string[];
}

// Hosting comparisons put hosting in the cost, on each kind of server.
const PRESETS: Preset[] = [
  {
    id: "indian_cloud",
    label: "We host it on a government-approved Indian cloud",
    overrides: { hosting_in_scope: true, hosting_provider: "indian_cloud" },
    countries: ["india"],
  },
  {
    id: "aws",
    label: "We host it on Amazon cloud",
    overrides: { hosting_in_scope: true, hosting_provider: "aws" },
  },
  {
    id: "on_prem",
    label: "We supply servers for the client's own server room",
    overrides: { hosting_in_scope: true, hosting_provider: "on_prem" },
  },
  {
    id: "helpdesk_office",
    label: "Dedicated helpdesk, office hours",
    overrides: { helpdesk_in_scope: true, support_sla: "8x5" },
  },
  {
    id: "helpdesk_24x7",
    label: "Dedicated helpdesk, round the clock",
    overrides: { helpdesk_in_scope: true, support_sla: "24x7" },
  },
  {
    id: "five_years",
    label: "5 years of support",
    overrides: { om_years: 5 },
  },
];

const PREFERRED_DEFAULTS = ["indian_cloud", "aws", "five_years"];
const DEADLINE = "deadline";

/** Difference from the current estimate, from two integer minor-unit values. */
function versus(
  result: ScenarioResult,
  baseline: ScenarioResult,
  currency: string,
): string {
  const mine = result.totals?.p50_paise;
  const base = baseline.totals?.p50_paise;
  if (mine === undefined || base === undefined) return "—";
  const diff = mine - base;
  if (diff === 0) return "Same";
  return diff < 0
    ? `${formatPaise(-diff, currency)} cheaper`
    : `${formatPaise(diff, currency)} more`;
}

export function CompareOptions({
  estimateId,
  currency = "INR",
  country = "india",
}: {
  estimateId: string;
  currency?: string;
  country?: string;
}) {
  const presets = PRESETS.filter(
    (p) => !p.countries || p.countries.includes(country),
  );
  const [selected, setSelected] = React.useState<string[]>(() =>
    PREFERRED_DEFAULTS.filter((id) => presets.some((p) => p.id === id)).slice(
      0,
      2,
    ),
  );
  const [deadline, setDeadline] = React.useState("");
  const [results, setResults] = React.useState<ScenarioResult[] | null>(null);
  const [running, setRunning] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const deadlineOn = selected.includes(DEADLINE);
  const deadlineMonths = Number(deadline);
  const deadlineValid =
    !deadlineOn ||
    (deadline.trim() !== "" &&
      Number.isInteger(deadlineMonths) &&
      deadlineMonths >= 1 &&
      deadlineMonths <= 60);
  const canCompare = selected.length > 0 && deadlineValid;

  function toggle(id: string) {
    setSelected((current) =>
      current.includes(id) ? current.filter((x) => x !== id) : [...current, id],
    );
  }

  async function compare() {
    const scenarios: Scenario[] = presets
      .filter((p) => selected.includes(p.id))
      .map((p) => ({ name: p.label, overrides: p.overrides }));
    if (deadlineOn) {
      scenarios.push({
        name: `Deadline of ${deadlineMonths} months`,
        overrides: { deadline_months: deadlineMonths },
      });
    }
    setRunning(true);
    setError(null);
    try {
      const out = await api.runScenarios(estimateId, scenarios);
      setResults(out.results);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setRunning(false);
    }
  }

  const baseline = results?.[0];

  return (
    <section className="flex flex-col gap-5 rounded-2xl border bg-card px-6 py-6 shadow-sm sm:px-8">
      <div>
        <h2 className="text-lg font-semibold">Compare options</h2>
        <p className="text-sm text-muted-foreground">
          See how the price changes if you choose differently. Your estimate is
          not changed.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {presets.map((preset) => {
          const on = selected.includes(preset.id);
          return (
            <label
              key={preset.id}
              className={cn(
                "flex cursor-pointer items-center gap-2 rounded-full border px-4 py-2 text-sm transition-colors",
                on
                  ? "border-primary bg-primary/5 ring-1 ring-primary"
                  : "hover:border-primary/40 hover:bg-muted/40",
              )}
            >
              <input
                type="checkbox"
                checked={on}
                onChange={() => toggle(preset.id)}
                className="size-4 accent-primary"
              />
              {preset.label}
            </label>
          );
        })}
        <label
          className={cn(
            "flex cursor-pointer items-center gap-2 rounded-full border px-4 py-1.5 text-sm transition-colors",
            deadlineOn
              ? "border-primary bg-primary/5 ring-1 ring-primary"
              : "hover:border-primary/40 hover:bg-muted/40",
          )}
        >
          <input
            type="checkbox"
            checked={deadlineOn}
            onChange={() => toggle(DEADLINE)}
            className="size-4 accent-primary"
          />
          Shorter deadline:
          <Input
            type="number"
            inputMode="numeric"
            min={1}
            max={60}
            value={deadline}
            onChange={(e) => {
              setDeadline(e.target.value);
              if (!deadlineOn) toggle(DEADLINE);
            }}
            className="h-8 w-16"
            aria-label="Deadline in months"
          />
          months
        </label>
      </div>
      {!deadlineValid ? (
        <span className="text-sm text-destructive">
          Enter a whole number of months between 1 and 60.
        </span>
      ) : null}

      <div>
        <Button
          size="lg"
          className="h-11"
          disabled={!canCompare || running}
          onClick={compare}
        >
          {running ? "Comparing…" : "Compare"}
        </Button>
      </div>
      <ErrorNotice message={error} />

      {results && baseline ? (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[32rem] text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="py-2 pr-4 font-medium">Option</th>
                <th className="py-2 pr-4 font-medium">Most likely</th>
                <th className="py-2 pr-4 font-medium">Range</th>
                <th className="py-2 font-medium">vs your estimate</th>
              </tr>
            </thead>
            <tbody>
              {results.map((result, i) => (
                <tr
                  key={`${result.name}-${i}`}
                  className={cn(
                    "border-b last:border-0",
                    i === 0 && "bg-muted/40",
                  )}
                >
                  <td className="py-3 pr-4 font-medium">
                    {i === 0 ? "Your estimate" : result.name}
                  </td>
                  {result.feasible && result.totals ? (
                    <>
                      <td className="py-3 pr-4 font-semibold tabular-nums">
                        {formatPaise(result.totals.p50_paise, currency)}
                      </td>
                      <td className="py-3 pr-4 text-muted-foreground tabular-nums">
                        {formatPaise(result.totals.p10_paise, currency)} –{" "}
                        {formatPaise(result.totals.p90_paise, currency)}
                      </td>
                      <td className="py-3 tabular-nums">
                        {i === 0 ? "—" : versus(result, baseline, currency)}
                      </td>
                    </>
                  ) : (
                    <td colSpan={3} className="py-3 text-muted-foreground">
                      Not possible in that time
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
