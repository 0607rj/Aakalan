"use client";

import * as React from "react";

import { ErrorNotice, Loading } from "@/components/status";
import { Badge } from "@/components/ui/badge";
import { Sheet } from "@/components/ui/sheet";
import { api, type CostLine } from "@/lib/api/client";
import {
  formatDecimal,
  formatPaise,
  formatPaiseExact,
  formatPercent,
  formatValue,
} from "@/lib/format";
import { useLoad } from "@/lib/use-load";

function SourceBadge({ source }: { source: string }) {
  if (source === "placeholder") {
    return <Badge variant="warning">placeholder</Badge>;
  }
  return (
    <Badge variant="outline" className="max-w-48 truncate" title={source}>
      {source}
    </Badge>
  );
}

function Step({
  n,
  title,
  children,
  empty,
}: {
  n: number;
  title: string;
  children: React.ReactNode;
  empty?: boolean;
}) {
  return (
    <section className="relative flex gap-3 pb-5">
      <div className="flex flex-col items-center">
        <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
          {n}
        </span>
        <span className="mt-1 w-px flex-1 bg-border" />
      </div>
      <div className="flex min-w-0 flex-1 flex-col gap-2">
        <h3 className="text-sm font-semibold">{title}</h3>
        {empty ? (
          <p className="text-xs text-muted-foreground">None for this line.</p>
        ) : (
          children
        )}
      </div>
    </section>
  );
}

function TraceBody({
  estimateId,
  lineId,
}: {
  estimateId: string;
  lineId: string;
}) {
  const load = React.useCallback(
    () => api.getTrace(estimateId, lineId),
    [estimateId, lineId],
  );
  const { state } = useLoad(load);
  if (state.kind === "loading") return <Loading>Loading trace…</Loading>;
  if (state.kind === "error") return <ErrorNotice message={state.message} />;
  const { line, trace, gst_percent: gst } = state.data;

  if (!trace) {
    return (
      <p className="text-sm text-muted-foreground">
        This line is restricted to finance and admin users.
      </p>
    );
  }

  return (
    <div className="flex flex-col">
      <Step
        n={1}
        title="RFP clauses → requirements"
        empty={!trace.requirements.length}
      >
        <ul className="flex flex-col gap-2">
          {trace.requirements.map((r) => (
            <li key={r.id} className="rounded-md border p-2 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-xs">{r.code}</span>
                <Badge variant="outline">
                  §{r.clause_ref ?? "?"}
                  {r.page ? `, p. ${r.page}` : ""}
                </Badge>
              </div>
              <p className="mt-1 text-muted-foreground">{r.text}</p>
            </li>
          ))}
        </ul>
      </Step>

      <Step n={2} title="Component instance" empty={!trace.component}>
        {trace.component ? (
          <p className="text-sm">
            <span className="font-medium">{trace.component.name}</span>{" "}
            <span className="text-muted-foreground">
              ({trace.component.catalog_key}) · size {trace.component.size} ·{" "}
              {trace.component.complexity.replace("_", " ")} complexity · qty{" "}
              {trace.component.quantity}
            </span>
          </p>
        ) : null}
      </Step>

      <Step n={3} title="Driver values" empty={!trace.drivers.length}>
        <ul className="flex flex-col gap-1 text-sm">
          {trace.drivers.map((d) => (
            <li key={d.key} className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-xs">{d.key}</span>=
              <span className="font-medium">{formatValue(d.value)}</span>
              <Badge variant={d.source === "user" ? "success" : "warning"}>
                {d.source === "user" ? "answered" : "default"}
              </Badge>
              {d.requirement_ids.length ? (
                <span className="text-xs text-muted-foreground">
                  cites {d.requirement_ids.length} requirement
                  {d.requirement_ids.length > 1 ? "s" : ""}
                </span>
              ) : null}
            </li>
          ))}
        </ul>
      </Step>

      <Step n={4} title="Rate-card entries" empty={!trace.rate_items.length}>
        <ul className="flex flex-col gap-1 text-sm">
          {trace.rate_items.map((r) => (
            <li key={r.key} className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-xs">{r.key}</span>
              <span className="font-medium">
                {r.currency} {formatDecimal(r.amount, 4)}
              </span>
              <span className="text-xs text-muted-foreground">
                {r.unit} · rate card {r.rate_card_version}
              </span>
              <SourceBadge source={r.source} />
            </li>
          ))}
        </ul>
      </Step>

      <Step n={5} title="Parameters" empty={!trace.parameters.length}>
        <ul className="flex flex-col gap-1 text-sm">
          {trace.parameters.map((p) => (
            <li key={p.path} className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-xs">{p.path}</span>=
              <span className="max-w-full truncate font-medium">
                {formatValue(p.value)}
              </span>
              <span className="text-xs text-muted-foreground">
                set {p.parameter_set_version}
              </span>
              <SourceBadge source={p.source} />
            </li>
          ))}
        </ul>
      </Step>

      <Step n={6} title="Formula">
        <p className="font-mono text-xs text-muted-foreground">
          {trace.formula_id}
        </p>
        <p className="rounded-md bg-muted p-2 font-mono text-xs">
          {trace.formula}
        </p>
      </Step>

      <Step n={7} title="Steps" empty={!trace.steps.length}>
        <ol className="flex flex-col gap-1.5 text-xs">
          {trace.steps.map((s, i) => (
            <li key={i} className="rounded-md border p-2">
              <div className="flex justify-between gap-2">
                <span className="font-medium">{s.label}</span>
                <span className="font-mono">{formatDecimal(s.value, 4)}</span>
              </div>
              <p className="mt-0.5 font-mono break-all text-muted-foreground">
                {s.expression}
              </p>
            </li>
          ))}
        </ol>
      </Step>

      <Step n={8} title="Value">
        <div className="grid grid-cols-3 gap-2 text-sm">
          {(
            [
              ["Low", line.low_paise],
              ["Likely", line.likely_paise],
              ["High", line.high_paise],
            ] as const
          ).map(([label, v]) => (
            <div key={label} className="rounded-md border p-2">
              <p className="text-xs text-muted-foreground">{label}</p>
              <p className="font-semibold">{formatPaise(v)}</p>
              <p className="text-xs text-muted-foreground">
                {formatPaiseExact(v)}
              </p>
            </div>
          ))}
        </div>
        <p className="text-xs text-muted-foreground">
          Spread −{formatPercent(trace.spread.down)} / +
          {formatPercent(trace.spread.up)} · GST {formatPercent(gst)}
        </p>
        {trace.spread.factors.length ? (
          <ul className="flex flex-col gap-0.5 text-xs">
            {trace.spread.factors.map((f, i) => (
              <li key={i} className="flex justify-between gap-2">
                <span>{f.name}</span>
                <span className="font-mono">
                  −{formatPercent(f.down)} / +{formatPercent(f.up)}
                </span>
              </li>
            ))}
          </ul>
        ) : null}
      </Step>
    </div>
  );
}

export function TracePanel({
  estimateId,
  line,
  onClose,
}: {
  estimateId: string;
  line: CostLine | null;
  onClose: () => void;
}) {
  return (
    <Sheet
      open={line !== null}
      onClose={onClose}
      title={line ? line.label : "Trace"}
      description={
        line ? (
          <span className="font-mono text-xs">
            {line.line_key} · year {line.year}
          </span>
        ) : null
      }
    >
      {line ? (
        <TraceBody key={line.id} estimateId={estimateId} lineId={line.id} />
      ) : null}
    </Sheet>
  );
}
