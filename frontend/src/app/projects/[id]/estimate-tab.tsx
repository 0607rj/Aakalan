"use client";

import * as React from "react";

import {
  ErrorNotice,
  Loading,
  SectionTitle,
  WarningNotice,
} from "@/components/status";
import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
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
  type CostLine,
  type Estimate,
  type EstimateSummary,
  type GroupTotal,
} from "@/lib/api/client";
import {
  formatDateTime,
  formatDecimal,
  formatPaise,
  formatPercent,
  formatValue,
  humanize,
} from "@/lib/format";
import { useLoad } from "@/lib/use-load";

import { ScenariosPanel } from "./scenarios-panel";
import { TracePanel } from "./trace-panel";

const CONFIDENCE_VARIANT: Record<string, BadgeProps["variant"]> = {
  high: "success",
  medium: "secondary",
  low: "destructive",
};

function Headline({ estimate }: { estimate: Estimate }) {
  const t = estimate.totals;
  const figures = [
    { label: "Low", sub: "P10", value: t?.p10_paise, strong: false },
    { label: "Likely", sub: "P50", value: t?.p50_paise, strong: true },
    { label: "High", sub: "P90", value: t?.p90_paise, strong: false },
  ];
  return (
    <Card>
      <CardContent className="flex flex-col gap-4 pt-6">
        <div className="flex flex-wrap items-center gap-2">
          <Badge
            variant={CONFIDENCE_VARIANT[estimate.confidence_detail.label]}
            className="capitalize"
          >
            {estimate.confidence_detail.label} confidence
          </Badge>
          {estimate.calibration.status === "uncalibrated" ? (
            <Badge
              variant="warning"
              title={estimate.calibration.placeholder_refs.join(", ")}
            >
              Uncalibrated — placeholder data
            </Badge>
          ) : (
            <Badge variant="success">Calibrated</Badge>
          )}
          <span className="text-xs text-muted-foreground">
            v{estimate.version} · rate card {estimate.rate_card_version} ·
            parameters {estimate.parameter_set_version} · catalog{" "}
            {estimate.catalog_version} · seed {estimate.seed} · engine{" "}
            {estimate.engine_version} · as of {estimate.as_of_date}
          </span>
        </div>
        {estimate.feasible && t ? (
          <>
            <div className="grid gap-3 sm:grid-cols-3">
              {figures.map((f) => (
                <div
                  key={f.label}
                  className={
                    f.strong
                      ? "rounded-lg border-2 border-primary bg-primary/5 p-4"
                      : "rounded-lg border p-4"
                  }
                >
                  <p className="text-xs font-medium text-muted-foreground">
                    {f.label} ({f.sub})
                  </p>
                  <p
                    className={
                      f.strong
                        ? "text-3xl font-semibold text-primary"
                        : "text-2xl font-semibold"
                    }
                  >
                    {formatPaise(f.value)}
                  </p>
                </div>
              ))}
            </div>
            <p className="text-sm text-muted-foreground">
              Base case (most-likely values):{" "}
              <span className="font-medium text-foreground">
                {formatPaise(t.likely_paise)}
              </span>{" "}
              · sum of line lows / highs {formatPaise(t.low_sum_paise)} /{" "}
              {formatPaise(t.high_sum_paise)}. Totals include GST
              {estimate.margin_visible ? " and margin" : ""}.
            </p>
            {estimate.top_drivers_text ? (
              <p className="text-sm">
                <span className="font-medium">Range drivers: </span>
                {estimate.top_drivers_text}
              </p>
            ) : null}
          </>
        ) : null}
      </CardContent>
    </Card>
  );
}

function Infeasible({ estimate }: { estimate: Estimate }) {
  const inf = estimate.infeasibility;
  if (!inf) return null;
  return (
    <Card className="border-destructive/40">
      <CardHeader>
        <CardTitle className="text-base text-destructive">
          Not feasible at this deadline
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <p className="text-sm">{inf.message}</p>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Phase</TableHead>
              <TableHead>Components</TableHead>
              <TableHead className="text-right">Build effort (pd)</TableHead>
              <TableHead className="text-right">Natural duration</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {inf.phases.map((p) => (
              <TableRow key={p.phase}>
                <TableCell>Phase {p.phase}</TableCell>
                <TableCell>{p.component_instance_ids.length}</TableCell>
                <TableCell className="text-right">
                  {formatDecimal(p.build_effort_pd, 0)}
                </TableCell>
                <TableCell className="text-right">
                  {formatDecimal(p.natural_duration_months, 1)} months
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

function TimelineCard({ estimate }: { estimate: Estimate }) {
  const tl = estimate.timeline;
  // prettier-ignore
  const items: [string, string][] = [
    ["Status", humanize(tl.status)],
    ["Natural duration", `${formatDecimal(tl.natural_duration_months, 1)} months`],
    ["Delivery", `${formatDecimal(tl.delivery_duration_months, 1)} months`],
    ["Programme", `${formatDecimal(tl.programme_duration_months, 1)} months`],
    ["Deadline", tl.deadline_months ? `${formatDecimal(tl.deadline_months, 1)} months` : "—"],
    ["Compression ×", formatDecimal(tl.compression_multiplier, 3)],
    ["Build effort", `${formatDecimal(tl.build_effort_pd, 0)} pd`],
    ["Max team", formatDecimal(tl.max_team, 1)],
    ["Size band", humanize(tl.size_band)],
  ];
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Timeline</CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-3">
          {items.map(([k, v]) => (
            <div key={k}>
              <dt className="text-xs text-muted-foreground">{k}</dt>
              <dd className="font-medium">{v}</dd>
            </div>
          ))}
        </dl>
      </CardContent>
    </Card>
  );
}

function GroupTable({ title, rows }: { title: string; rows: GroupTotal[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead />
            <TableHead className="text-right">Low</TableHead>
            <TableHead className="text-right">Likely</TableHead>
            <TableHead className="text-right">High</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((g) => (
            <TableRow key={g.key}>
              <TableCell>{g.name}</TableCell>
              <TableCell className="text-right">
                {formatPaise(g.low_paise)}
              </TableCell>
              <TableCell className="text-right font-medium">
                {formatPaise(g.likely_paise)}
              </TableCell>
              <TableCell className="text-right">
                {formatPaise(g.high_paise)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  );
}

function LinesByBucket({
  estimate,
  onSelect,
}: {
  estimate: Estimate;
  onSelect: (line: CostLine) => void;
}) {
  const names = new Map(estimate.by_bucket.map((b) => [b.key, b.name]));
  const groups: [string, CostLine[]][] = [];
  for (const line of estimate.lines) {
    const last = groups[groups.length - 1];
    if (last && last[0] === line.bucket) last[1].push(line);
    else groups.push([line.bucket, [line]]);
  }
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">
          Cost lines ({estimate.lines.length})
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          Click any line to see its full trace back to the RFP clause.
        </p>
      </CardHeader>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Line</TableHead>
            <TableHead>Year</TableHead>
            <TableHead className="text-right">Low</TableHead>
            <TableHead className="text-right">Likely</TableHead>
            <TableHead className="text-right">High</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {groups.map(([bucket, lines]) => (
            <React.Fragment key={bucket}>
              <TableRow className="bg-muted/60 hover:bg-muted/60">
                <TableCell colSpan={5} className="text-xs font-semibold">
                  {names.get(bucket) ?? humanize(bucket)}
                </TableCell>
              </TableRow>
              {lines.map((line) => (
                <TableRow
                  key={line.id}
                  className="cursor-pointer"
                  tabIndex={0}
                  onClick={() => onSelect(line)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      onSelect(line);
                    }
                  }}
                >
                  <TableCell className="pl-6">
                    {line.label}
                    {line.derived ? (
                      <span className="ml-2 text-xs text-muted-foreground">
                        derived
                      </span>
                    ) : null}
                  </TableCell>
                  <TableCell>{line.year === 0 ? "Build" : line.year}</TableCell>
                  {line.redacted ? (
                    <TableCell colSpan={3} className="text-right">
                      <Badge variant="outline">restricted</Badge>
                    </TableCell>
                  ) : (
                    <>
                      <TableCell className="text-right">
                        {formatPaise(line.low_paise)}
                      </TableCell>
                      <TableCell className="text-right font-medium">
                        {formatPaise(line.likely_paise)}
                      </TableCell>
                      <TableCell className="text-right">
                        {formatPaise(line.high_paise)}
                      </TableCell>
                    </>
                  )}
                </TableRow>
              ))}
            </React.Fragment>
          ))}
        </TableBody>
      </Table>
    </Card>
  );
}

function Manpower({ estimate }: { estimate: Estimate }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Manpower</CardTitle>
      </CardHeader>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Role</TableHead>
            <TableHead>Stage</TableHead>
            <TableHead>Year</TableHead>
            <TableHead className="text-right">Person-days</TableHead>
            <TableHead className="text-right">Person-months</TableHead>
            <TableHead className="text-right">Avg FTE</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {estimate.manpower.map((m) => (
            <TableRow key={`${m.role}-${m.stage}-${m.year}`}>
              <TableCell>{humanize(m.role.replace(/^role\./, ""))}</TableCell>
              <TableCell>{humanize(m.stage)}</TableCell>
              <TableCell>{m.year === 0 ? "Build" : m.year}</TableCell>
              <TableCell className="text-right">
                {formatDecimal(m.person_days, 1)}
              </TableCell>
              <TableCell className="text-right">
                {formatDecimal(m.person_months, 2)}
              </TableCell>
              <TableCell className="text-right">
                {formatDecimal(m.average_fte, 2)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  );
}

function EstimateView({ estimate }: { estimate: Estimate }) {
  const [traceLine, setTraceLine] = React.useState<CostLine | null>(null);
  const drivers = estimate.top_drivers;
  return (
    <div className="flex flex-col gap-4">
      <Headline estimate={estimate} />
      {!estimate.feasible ? <Infeasible estimate={estimate} /> : null}
      {estimate.sanity_checks.map((c) =>
        c.status === "flag" ? (
          <WarningNotice key={c.key}>{c.message}</WarningNotice>
        ) : (
          <p key={c.key} className="text-sm text-muted-foreground">
            ✓ {c.message}
          </p>
        ),
      )}
      <TimelineCard estimate={estimate} />
      {estimate.feasible ? (
        <>
          {drivers.length ? (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Top range drivers</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-2">
                {drivers.map((d) => (
                  <div
                    key={d.bucket}
                    className="flex items-center gap-3 text-sm"
                  >
                    <span className="w-64 shrink-0">{d.name}</span>
                    <div className="h-2 flex-1 overflow-hidden rounded bg-muted">
                      <div
                        className="h-full bg-primary"
                        style={{ width: `${Number(d.variance_share) * 100}%` }}
                      />
                    </div>
                    <span className="w-14 text-right font-mono text-xs">
                      {formatPercent(d.variance_share)}
                    </span>
                  </div>
                ))}
              </CardContent>
            </Card>
          ) : null}
          <div className="grid gap-4 lg:grid-cols-2">
            <GroupTable title="By stage" rows={estimate.by_stage} />
            <GroupTable title="By year" rows={estimate.by_year} />
          </div>
          <LinesByBucket estimate={estimate} onSelect={setTraceLine} />
          <Manpower estimate={estimate} />
          <ScenariosPanel key={estimate.id} estimateId={estimate.id} />
        </>
      ) : null}
      <details className="rounded-lg border bg-card p-4">
        <summary className="cursor-pointer text-sm font-semibold">
          Assumptions ({estimate.assumptions.length})
        </summary>
        <ul className="mt-3 flex flex-col gap-1 text-sm">
          {estimate.assumptions.map((a) => (
            <li key={a.key} className="flex flex-wrap gap-2">
              <span className="font-mono text-xs">{a.key}</span>
              <span className="text-muted-foreground">{a.text}</span>
              <span className="text-xs">({formatValue(a.value)})</span>
            </li>
          ))}
        </ul>
      </details>
      <TracePanel
        estimateId={estimate.id}
        line={traceLine}
        onClose={() => setTraceLine(null)}
      />
    </div>
  );
}

function SelectedEstimate({ estimateId }: { estimateId: string }) {
  const load = React.useCallback(
    () => api.getEstimate(estimateId),
    [estimateId],
  );
  const { state } = useLoad(load);
  if (state.kind === "loading") return <Loading>Loading estimate…</Loading>;
  if (state.kind === "error") return <ErrorNotice message={state.message} />;
  return <EstimateView estimate={state.data} />;
}

export function EstimateTab({
  projectId,
  canEdit,
}: {
  projectId: string;
  canEdit: boolean;
}) {
  const load = React.useCallback(
    () => api.listEstimates(projectId),
    [projectId],
  );
  const { state, setData } = useLoad(load);
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState<"calculate" | "reprice" | null>(null);

  if (state.kind === "loading") return <Loading />;
  if (state.kind === "error") return <ErrorNotice message={state.message} />;
  const estimates: EstimateSummary[] = state.data;
  const current = selectedId ?? estimates[0]?.id ?? null;

  async function run(kind: "calculate" | "reprice") {
    setBusy(kind);
    setError(null);
    try {
      const created =
        kind === "calculate" || !current
          ? await api.createEstimate(projectId, {})
          : await api.repriceEstimate(current);
      setData(await api.listEstimates(projectId));
      setSelectedId(created.id);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <SectionTitle
        action={
          canEdit ? (
            <div className="flex gap-2">
              {current ? (
                <Button
                  variant="outline"
                  disabled={busy !== null}
                  onClick={() => run("reprice")}
                >
                  {busy === "reprice"
                    ? "Re-pricing…"
                    : "Re-price at current rates"}
                </Button>
              ) : null}
              <Button disabled={busy !== null} onClick={() => run("calculate")}>
                {busy === "calculate" ? "Calculating…" : "Calculate estimate"}
              </Button>
            </div>
          ) : null
        }
      >
        Estimate
      </SectionTitle>
      <ErrorNotice message={error} />
      {estimates.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            No estimates yet. Confirm requirements and the component mapping,
            then calculate.
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-2">
            <label htmlFor="estimate-version" className="text-sm font-medium">
              Version
            </label>
            <Select
              id="estimate-version"
              className="w-auto min-w-80"
              value={current ?? ""}
              onChange={(e) => setSelectedId(e.target.value)}
            >
              {estimates.map((e) => (
                <option key={e.id} value={e.id}>
                  v{e.version} · {formatDateTime(e.created_at)} · rate card{" "}
                  {e.rate_card_version}
                  {e.feasible
                    ? ` · P50 ${formatPaise(e.p50_paise)}`
                    : " · not feasible"}
                  {e.parent_estimate_id ? " · re-priced" : ""}
                </option>
              ))}
            </Select>
          </div>
          {current ? (
            <SelectedEstimate key={current} estimateId={current} />
          ) : null}
        </>
      )}
    </div>
  );
}
