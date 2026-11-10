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
  published: { label: "Published", tone: "bg-success/10 text-success" },
  worked_out: {
    label: "Worked out from published prices",
    tone: "bg-tape-soft text-foreground",
  },
  estimate: { label: "Our estimate", tone: "bg-warning/10 text-warning" },
  your_choice: { label: "Your answers", tone: "bg-primary/10 text-primary" },
};

function StatusTag({ status }: { status: PriceSource["status"] }) {
  const s = STATUS[status];
  return (
    <span
      className={cn(
        "inline-flex w-fit shrink-0 rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap",
        s.tone,
      )}
    >
      {s.label}
    </span>
  );
}

/** "payscale.com" from a link. */
function site(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

/** A source's name in a few words: "Cleveroad CRM role table (UI/UX 380 h)" -> "Cleveroad
 * CRM role table". */
function shortName(text: string): string {
  const head = text.split(/ \(|: |; | — /)[0].trim();
  return head.length > 60 ? `${head.slice(0, 57)}…` : head;
}

/** Where a source comes from, in a few words, linked where there is a page. */
function From({ source }: { source: PriceSource }) {
  const links = source.cites.filter((c) => c.text);
  if (source.kind !== "rate" && links.length > 0) {
    return (
      <span className="flex flex-wrap gap-x-3 gap-y-0.5">
        {links.slice(0, 3).map((c, i) =>
          c.url ? (
            <a
              key={i}
              href={c.url}
              target="_blank"
              rel="noreferrer"
              className="text-primary hover:underline"
            >
              {shortName(c.text)}
            </a>
          ) : (
            <span key={i}>{shortName(c.text)}</span>
          ),
        )}
        {links.length > 3 ? <span>+{links.length - 3} more</span> : null}
      </span>
    );
  }
  if (source.url) {
    return (
      <a
        href={source.url}
        target="_blank"
        rel="noreferrer"
        title={source.detail}
        className="text-primary hover:underline"
      >
        {site(source.url)}
      </a>
    );
  }
  if (source.status === "estimate") return <span>Reasoned by us</span>;
  return <span title={source.detail}>{shortName(source.detail)}</span>;
}

/** A source's name where a row of the breakdown cites it: links to its line in the list. */
function SourceRef({ source }: { source: PriceSource }) {
  return (
    <a
      href={`#source-${source.n}`}
      title={STATUS[source.status].label}
      className={cn(
        "hover:underline",
        source.status === "estimate" ? "text-warning" : "text-primary",
      )}
    >
      {source.title}
    </a>
  );
}

function rateText(rate: RowSources["rates"][number]): string {
  if (rate.label.includes("of the amount"))
    return `${rate.label}: ${formatDecimal(Number(rate.amount) * 100, 2)}%`;
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
  // the rules and the project's answers are in the Excel download, not the page's list
  const shown = refs.filter((s) => LISTED.has(s.kind));
  const guesses = shown.filter((s) => s.status === "estimate").length;
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
        {shown.length > 0 ? (
          <p>
            <span className="font-medium text-foreground">From:</span>{" "}
            {shown.map((s, i) => (
              <React.Fragment key={s.n}>
                {i > 0 ? ", " : ""}
                <SourceRef source={s} />
              </React.Fragment>
            ))}
            {guesses > 0 ? (
              <span className="ml-1 text-xs">
                ({guesses} of {shown.length} are our estimates)
              </span>
            ) : null}
          </p>
        ) : null}
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
    <details className="group/ai text-sm">
      <summary className="w-fit cursor-pointer list-none text-primary hover:underline [&::-webkit-details-marker]:hidden">
        How the AI saving is worked out
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

/** The kinds of source the page lists; rules and answers are in the Excel download. */
const LISTED = new Set<PriceSource["kind"]>([
  "rate",
  "hours",
  "margin",
  "ai_saving",
]);

function amountText(source: PriceSource): string {
  if (source.amount === null || source.amount === undefined) return "";
  if (source.title.includes("of the amount"))
    return `${formatDecimal(Number(source.amount) * 100, 2)}%`;
  const currency = (source.currency ?? "INR") as Parameters<
    typeof currencySymbol
  >[0];
  const amount = Number(source.amount).toLocaleString(
    currency === "INR" ? "en-IN" : "en-US",
    { maximumFractionDigits: Number(source.amount) >= 100 ? 0 : 2 },
  );
  return `${currencySymbol(currency)}${amount}`;
}

/** One row: what it is, its value, where it comes from, and whether that is published. */
function Row({ source, value }: { source: PriceSource; value?: string }) {
  return (
    <li
      id={`source-${source.n}`}
      className="grid scroll-mt-24 gap-x-6 gap-y-1 py-2.5 text-sm sm:grid-cols-[minmax(0,1.3fr)_minmax(0,0.6fr)_minmax(0,1.4fr)_auto] sm:items-baseline"
    >
      <span className="font-medium">
        {source.title.replace(/^Hours for /, "")}
      </span>
      <span className="tabular-nums">{value ?? ""}</span>
      <span className="text-muted-foreground">
        <From source={source} />
      </span>
      <StatusTag status={source.status} />
    </li>
  );
}

function Group({
  title,
  note,
  sources,
  value,
}: {
  title: string;
  note?: string;
  sources: PriceSource[];
  value?: (s: PriceSource) => string;
}) {
  if (sources.length === 0) return null;
  return (
    <div className="flex flex-col gap-1">
      <h3 className="font-semibold">{title}</h3>
      {note ? <p className="text-sm text-muted-foreground">{note}</p> : null}
      <ul className="flex flex-col divide-y">
        {sources.map((s) => (
          <Row key={s.n} source={s} value={value?.(s)} />
        ))}
      </ul>
    </div>
  );
}

/** Where the price comes from, in four plain groups: the team's day rates, the prices of
 * services and hardware, the hours each feature takes, and the profit and AI saving. Each
 * row says whether it is published or our own estimate; the rules and settings behind them
 * are in the Excel download (sheet "Sources"). */
export function SourcesList() {
  const data = React.useContext(Sources);
  if (!data || data.sources.length === 0) return null;
  const listed = data.sources.filter((s) => LISTED.has(s.kind));
  if (listed.length === 0) return null;
  const published = listed.filter((s) => s.status !== "estimate").length;
  const ours = listed.length - published;
  const rates = listed.filter((s) => s.kind === "rate");
  const margin = listed.find((s) => s.kind === "margin");
  const ai = listed.find((s) => s.kind === "ai_saving");
  return (
    <Disclosure
      title="Where the price comes from"
      icon={SealCheckIcon}
      hint={`${published} of ${listed.length} from published prices and studies${ours > 0 ? ` · ${ours} our own estimates` : ""}`}
    >
      <p className="max-w-3xl text-sm text-muted-foreground">
        The price is the hours of work × each person&rsquo;s day rate, plus the
        prices below, worked out by fixed rules. The AI never sets a number.
        &ldquo;Our estimate&rdquo; marks figures we worked out ourselves, still
        being replaced with published ones.
      </p>
      <Group
        title="Day rate of each person"
        note="What one day of each person's work costs."
        sources={rates.filter((s) => s.role)}
        value={amountText}
      />
      <Group
        title="Hours of work for each feature"
        note="How long each feature takes to build, from published project data."
        sources={listed.filter((s) => s.kind === "hours")}
      />
      <Group
        title="Prices of services and hardware"
        sources={rates.filter((s) => !s.role)}
        value={amountText}
      />
      <Group
        title="Profit and AI saving"
        sources={[margin, ai].filter((s): s is PriceSource => s !== undefined)}
        value={(s) =>
          s.kind === "margin"
            ? (s.values[0] ?? "").replace(/^profit = /, "")
            : ""
        }
      />
      <p className="text-sm text-muted-foreground">
        The rules behind these (e.g. extra work for complex features) and every
        value used are in the Excel download, sheet &ldquo;Sources&rdquo;.
      </p>
    </Disclosure>
  );
}
