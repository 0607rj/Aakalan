"use client";

import * as React from "react";

import { ErrorNotice, SectionTitle } from "@/components/status";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  api,
  errorText,
  type Scenario,
  type ScenarioResult,
} from "@/lib/api/client";
import { formatDecimal, formatPaise } from "@/lib/format";
import { cn } from "@/lib/utils";

type Preset = { id: string; group: string; name: string; scenario: Scenario };

// prettier-ignore
const PRESETS: Preset[] = [
  { id: "aws", group: "Hosting", name: "AWS", scenario: { name: "AWS", overrides: { hosting_provider: "aws" } } },
  { id: "indian_cloud", group: "Hosting", name: "Indian cloud", scenario: { name: "Indian cloud (MeitY)", overrides: { hosting_provider: "indian_cloud" } } },
  { id: "on_prem", group: "Hosting", name: "On-prem", scenario: { name: "On-prem", overrides: { hosting_provider: "on_prem" } } },
  { id: "api", group: "AI runtime", name: "LLM API", scenario: { name: "LLM API", overrides: { ai_runtime_mode: "api" } } },
  { id: "gpu", group: "AI runtime", name: "Self-hosted GPU", scenario: { name: "Self-hosted GPU", overrides: { ai_runtime_mode: "self_hosted_gpu" } } },
  { id: "open_source", group: "Software", name: "Open source", scenario: { name: "Open source", overrides: { licensing: "open_source" } } },
  { id: "licensed", group: "Software", name: "Licensed", scenario: { name: "Licensed products", overrides: { licensing: "licensed" } } },
];

const MAX_SCENARIOS = 8;

export function ScenariosPanel({ estimateId }: { estimateId: string }) {
  const [selected, setSelected] = React.useState<string[]>([
    "indian_cloud",
    "gpu",
  ]);
  const [deadline, setDeadline] = React.useState("");
  const [results, setResults] = React.useState<ScenarioResult[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [running, setRunning] = React.useState(false);

  function toggle(id: string) {
    setSelected((s) =>
      s.includes(id) ? s.filter((x) => x !== id) : [...s, id],
    );
  }

  async function compare() {
    const scenarios = PRESETS.filter((p) => selected.includes(p.id)).map(
      (p) => p.scenario,
    );
    const months = Number(deadline);
    if (deadline.trim()) {
      if (!Number.isFinite(months) || months <= 0) {
        setError("Deadline must be a positive number of months.");
        return;
      }
      scenarios.push({
        name: `Deadline ${months} months`,
        overrides: { deadline_months: months },
      });
    }
    if (scenarios.length === 0) {
      setError("Pick at least one scenario.");
      return;
    }
    setError(null);
    setRunning(true);
    try {
      const out = await api.runScenarios(
        estimateId,
        scenarios.slice(0, MAX_SCENARIOS),
      );
      setResults(out.results);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setRunning(false);
    }
  }

  const groups = [...new Set(PRESETS.map((p) => p.group))];

  return (
    <div className="flex flex-col gap-3">
      <SectionTitle>Scenarios</SectionTitle>
      <p className="text-sm text-muted-foreground">
        Re-price this estimate&apos;s snapshot with different choices. Results
        are not saved.
      </p>
      <Card>
        <CardContent className="flex flex-col gap-4 pt-6">
          <div className="flex flex-wrap gap-6">
            {groups.map((group) => (
              <div key={group} className="flex flex-col gap-1.5">
                <span className="text-xs font-medium text-muted-foreground">
                  {group}
                </span>
                <div className="flex gap-1">
                  {PRESETS.filter((p) => p.group === group).map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      aria-pressed={selected.includes(p.id)}
                      onClick={() => toggle(p.id)}
                      className={cn(
                        "rounded-md border px-3 py-1.5 text-xs font-medium transition-colors",
                        selected.includes(p.id)
                          ? "border-primary bg-primary text-primary-foreground"
                          : "bg-card hover:bg-muted",
                      )}
                    >
                      {p.name}
                    </button>
                  ))}
                </div>
              </div>
            ))}
            <div className="flex flex-col gap-1.5">
              <Label
                htmlFor="scenario-deadline"
                className="text-xs text-muted-foreground"
              >
                Deadline (months, optional)
              </Label>
              <Input
                id="scenario-deadline"
                type="number"
                min={1}
                step="any"
                className="h-8 w-28"
                value={deadline}
                onChange={(e) => setDeadline(e.target.value)}
              />
            </div>
          </div>
          <div>
            <Button onClick={compare} disabled={running}>
              {running ? "Comparing…" : "Compare"}
            </Button>
          </div>
          <ErrorNotice message={error} />
        </CardContent>
      </Card>

      {results ? (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Scenario</TableHead>
                <TableHead className="text-right">Low (P10)</TableHead>
                <TableHead className="text-right">Likely (P50)</TableHead>
                <TableHead className="text-right">High (P90)</TableHead>
                <TableHead>Timeline</TableHead>
                <TableHead>Confidence</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {results.map((r) => (
                <TableRow key={r.name}>
                  <TableCell className="font-medium">{r.name}</TableCell>
                  {r.feasible && r.totals ? (
                    <>
                      <TableCell className="text-right">
                        {formatPaise(r.totals.p10_paise)}
                      </TableCell>
                      <TableCell className="text-right font-semibold">
                        {formatPaise(r.totals.p50_paise)}
                      </TableCell>
                      <TableCell className="text-right">
                        {formatPaise(r.totals.p90_paise)}
                      </TableCell>
                    </>
                  ) : (
                    <TableCell colSpan={3} className="whitespace-normal">
                      <Badge variant="destructive">Not feasible</Badge>{" "}
                      <span className="text-xs text-muted-foreground">
                        {r.message}
                      </span>
                    </TableCell>
                  )}
                  <TableCell className="text-xs">
                    {formatDecimal(r.timeline.delivery_duration_months, 1)} mo ·{" "}
                    {r.timeline.status.replace("_", " ")}
                  </TableCell>
                  <TableCell className="capitalize">
                    {r.confidence.label}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      ) : null}
    </div>
  );
}
