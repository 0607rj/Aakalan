"use client";

import * as React from "react";

import { SealCheckIcon } from "@phosphor-icons/react/dist/ssr";

import {
  api,
  type EstimateSources,
  type PriceSource,
  type RowSources,
} from "@/lib/api/client";
import { currencySymbol, formatDecimal } from "@/lib/format";
import { useLoad } from "@/lib/use-load";
import { cn } from "@/lib/utils";

import { Disclosure } from "./cost-summary";

/**
 * Where every price comes from (OPEN_QUESTIONS 226): read from the engine's trace of each line,
 * so it holds for any project. Each row of the breakdown gets "Where this comes from"; the
 * numbered list says of every source whether it is published, worked out from published
 * prices, or our estimate not yet checked.
 */
const Sources = React.createContext<EstimateSources | null>(null);

export function SourcesProvider({
  estimateId,
  children,
}: {
  estimateId: string;
  children: React.ReactNode;
}) {
  const loader = React.useCallback(
    () => api.getSources(estimateId),
    [estimateId],
  );
  const { state } = useLoad(loader);
  return (
    <Sources.Provider value={state.kind === "ready" ? state.data : null}>
      {children}
    </Sources.Provider>
  );
}

const STATUS: Record<PriceSource["status"], { label: string; tone: string }> = {
  published: {
    label: "Published source",
    tone: "bg-success/10 text-success",
  },
  worked_out: {
    label: "Worked out from published prices",
    tone: "bg-tape-soft text-foreground",
  },
  estimate: {
    label: "Our estimate, not yet checked",
    tone: "bg-warning/10 text-warning",
  },
  your_choice: {
    label: "Project details you gave",
    tone: "bg-primary/10 text-primary",
  },
};

function StatusTag({ status }: { status: PriceSource["status"] }) {
  const s = STATUS[status];
  return (
    <span
      className={cn(
        "inline-flex rounded-full px-2 py-0.5 text-xs font-medium",
        s.tone,
      )}
    >
      {s.label}
    </span>
  );
}

function SourceRef({ source }: { source: PriceSource }) {
  return (
    <a
      href={`#source-${source.n}`}
      title={`${source.title} · ${STATUS[source.status].label}`}
      className={cn(
        "rounded px-1 font-mono text-xs tabular-nums hover:underline",
        source.status === "estimate" ? "text-warning" : "text-primary",
      )}
    >
      [{source.n}]
    </a>
  );
}

function rateText(rate: RowSources["rates"][number]): string {
  const amount = Number(rate.amount).toLocaleString(
    rate.currency === "INR" ? "en-IN" : "en-US",
    { maximumFractionDigits: 2 },
  );
  const symbol = currencySymbol(rate.currency);
  return `${rate.label}: ${symbol}${amount}`;
}

/** "Where this comes from" for one row: what asked for it, the work, the rates, the AI saving
 * on its tasks and its sources by number. Nothing is shown before the sources load. */
export function RowSourcesNote({ row }: { row: string }) {
  const data = React.useContext(Sources);
  const found = data?.rows.find((r) => r.row === row);
  if (!data || !found) return null;
  const byN = new Map(data.sources.map((s) => [s.n, s]));
  const refs = found.sources
    .map((n) => byN.get(n))
    .filter((s): s is PriceSource => s !== undefined);
  const guesses = refs.filter((s) => s.status === "estimate").length;
  return (
    <details className="group/src mt-1 text-sm">
      <summary className="w-fit cursor-pointer list-none text-primary hover:underline [&::-webkit-details-marker]:hidden">
        Where this comes from
      </summary>
      <div className="mt-2 flex flex-col gap-2 rounded-lg bg-panel-2 px-3 py-2 text-muted-foreground">
        {found.asked.length > 0 ? (
          <div>
            <p className="font-medium text-foreground">Asked for by</p>
            <ul className="flex flex-col gap-1">
              {found.asked.slice(0, 5).map((a, i) => (
                <li key={i}>
                  {a.page ? (
                    <span className="font-mono text-xs">
                      Page {a.page}
                      {a.clause ? ` · ${a.clause}` : ""}:{" "}
                    </span>
                  ) : null}
                  “{a.text}”
                </li>
              ))}
              {found.asked.length > 5 ? (
                <li>… and {found.asked.length - 5} more</li>
              ) : null}
            </ul>
          </div>
        ) : null}
        {found.person_days ? (
          <p>
            <span className="font-medium text-foreground">Work:</span> about{" "}
            {formatDecimal(found.person_days, 0)} person-days
            {found.rates.length > 0 ? ", at these rates:" : ""}
          </p>
        ) : null}
        {found.rates.length > 0 ? (
          <ul className="flex flex-wrap gap-x-4 gap-y-1">
            {found.rates.map((r, i) => (
              <li key={`${r.label}-${i}`} className="tabular-nums">
                {rateText(r)}
              </li>
            ))}
          </ul>
        ) : null}
        {found.ai_tasks.some((t) => t.saving_percent > 0) ? (
          <p>
            <span className="font-medium text-foreground">AI tools save:</span>{" "}
            {found.ai_tasks
              .filter((t) => t.saving_percent > 0)
              .map((t) => `${t.task.toLowerCase()} ${t.saving_percent}%`)
              .join(", ")}
            .
          </p>
        ) : null}
        <p>
          <span className="font-medium text-foreground">Sources:</span>{" "}
          {refs.map((s) => (
            <SourceRef key={s.n} source={s} />
          ))}
          {guesses > 0 ? (
            <span className="ml-1 text-xs">
              ({guesses} of {refs.length} are our estimates, not yet checked)
            </span>
          ) : null}
        </p>
      </div>
    </details>
  );
}

/** How the AI saving was worked out: each task's saving, how sure it is, and the studies. */
export function AiSavingSources() {
  const data = React.useContext(Sources);
  const ai = data?.sources.find((s) => s.kind === "ai_saving");
  if (!ai) return null;
  return (
    <details className="group/ai rounded-2xl border bg-card px-5 py-4 text-sm">
      <summary className="cursor-pointer list-none font-medium [&::-webkit-details-marker]:hidden">
        How the AI saving is worked out{" "}
        <span className="text-primary group-open/ai:hidden">show</span>
      </summary>
      <div className="mt-3 flex flex-col gap-3 text-muted-foreground">
        <p>
          Each kind of work saves a different share, from published studies.
          Planning, review and security testing save little or nothing, and the
          extra checking of AI-written code is priced as its own item.
        </p>
        {ai.values.length > 0 ? (
          <ul className="grid gap-x-6 gap-y-1 sm:grid-cols-2">
            {ai.values.map((v) => (
              <li key={v}>{v}</li>
            ))}
          </ul>
        ) : null}
        <ul className="flex flex-col gap-1.5">
          {ai.cites.map((c) => (
            <li key={c.text}>
              {c.url ? (
                <a
                  href={c.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-foreground hover:underline"
                >
                  {c.text}
                </a>
              ) : (
                <span className="text-foreground">{c.text}</span>
              )}{" "}
              {c.year ? `(${c.year})` : ""}{" "}
              <span className="text-xs">
                {c.checked ? "· checked on the page" : "· not checked yet"}
              </span>
            </li>
          ))}
        </ul>
        <p className="text-xs">
          <SourceRef source={ai} /> in the list of sources.
        </p>
      </div>
    </details>
  );
}

function SourceItem({ source }: { source: PriceSource }) {
  return (
    <li
      id={`source-${source.n}`}
      className="flex scroll-mt-24 flex-col gap-1 py-3"
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-xs text-muted-foreground tabular-nums">
          [{source.n}]
        </span>
        <span className="font-medium">{source.title}</span>
        <StatusTag status={source.status} />
        {source.confidence ? (
          <span className="text-xs text-muted-foreground">
            confidence: {source.confidence.replace("_", "-")}
          </span>
        ) : null}
      </div>
      {source.detail ? (
        <p className="text-sm text-muted-foreground">{source.detail}</p>
      ) : null}
      {source.url ? (
        <a
          href={source.url}
          target="_blank"
          rel="noreferrer"
          className="w-fit max-w-full truncate text-sm text-primary hover:underline"
        >
          {source.url}
        </a>
      ) : null}
      {source.cites.length > 0 &&
      (source.kind === "hours" || source.kind === "margin") ? (
        <ul className="flex flex-col gap-0.5 text-sm text-muted-foreground">
          {source.cites.map((c, i) => (
            <li key={i}>
              {c.url ? (
                <a
                  href={c.url}
                  target="_blank"
                  rel="noreferrer"
                  className="hover:underline"
                >
                  {c.text}
                </a>
              ) : (
                c.text
              )}
            </li>
          ))}
        </ul>
      ) : null}
      {source.values.length > 0 ? (
        <details className="text-sm text-muted-foreground">
          <summary className="w-fit cursor-pointer list-none hover:text-foreground [&::-webkit-details-marker]:hidden">
            Values used in this estimate ({source.values.length})
          </summary>
          <ul className="mt-1 flex flex-col gap-0.5 font-mono text-xs">
            {source.values.map((v) => (
              <li key={v}>{v}</li>
            ))}
          </ul>
        </details>
      ) : null}
      <p className="text-xs text-muted-foreground">{source.version}</p>
    </li>
  );
}

/** Every source this estimate used, numbered, with what each one is. */
export function SourcesList() {
  const data = React.useContext(Sources);
  if (!data || data.sources.length === 0) return null;
  const c = data.counts;
  return (
    <Disclosure
      title="Where every price comes from"
      icon={SealCheckIcon}
      hint={`${data.sources.length} sources: ${c.published ?? 0} published, ${c.worked_out ?? 0} worked out from published prices, ${c.estimate ?? 0} our estimates, plus the project details you gave`}
    >
      <p className="max-w-3xl text-sm text-muted-foreground">
        Every number in this estimate is worked out by fixed rules from the
        sources below, the same for everyone; the AI only reads documents and
        never sets a price. The builder&rsquo;s profit and the AI saving are
        shown openly: nothing is kept back out of sight. &ldquo;Our estimate,
        not yet checked&rdquo; marks figures we reasoned out ourselves and are
        still replacing with published ones.
      </p>
      <ol className="flex flex-col divide-y">
        {data.sources.map((s) => (
          <SourceItem key={s.n} source={s} />
        ))}
      </ol>
    </Disclosure>
  );
}
