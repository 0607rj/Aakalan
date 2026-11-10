"use client";

import * as React from "react";
import {
  CaretRightIcon,
  ChartPieSliceIcon,
  ListChecksIcon,
} from "@phosphor-icons/react/dist/ssr";

import type { PricedOption, QuickSummary } from "@/lib/api/client";
import { formatApprox, formatRange } from "@/lib/format";
import {
  IconTile,
  type IconType,
  type Tone,
} from "@/components/site/illustrations";
import { cn } from "@/lib/utils";

import { PrerequisiteWarnings } from "../new/parts";
import { changeRange, NOT_INCLUDED_WHY, signed } from "./check";

type CostItem = QuickSummary["cost_items"][number];
type Money = (paise: number | null | undefined) => string;

function moneyOf(summary: QuickSummary): Money {
  return (paise) => formatApprox(paise ?? null, summary.currency);
}

function yearsText(years: number): string {
  return `${years} year${years === 1 ? "" : "s"}`;
}

/** A small right-pointing chevron (rotate it for other directions). */
export function Chevron({ className }: { className?: string }) {
  return (
    <CaretRightIcon
      size={14}
      weight="bold"
      aria-hidden="true"
      className={cn("inline-block align-[-2px]", className)}
    />
  );
}

/** A section heading of the result page, with its icon on a tinted tile. */
export function SectionTitle({
  icon,
  tone = "tape",
  children,
  className,
}: {
  icon: IconType;
  tone?: Tone;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span className="flex items-center gap-3">
      <IconTile icon={icon} tone={tone} size="sm" />
      <h2 className={cn("font-wide text-xl", className)}>{children}</h2>
    </span>
  );
}

/** A collapsed section: the title (and a one-line hint) stays visible, the rest opens on click. */
export function Disclosure({
  title,
  icon,
  tone,
  hint,
  defaultOpen = false,
  children,
}: {
  title: string;
  icon: IconType;
  tone?: Tone;
  hint?: React.ReactNode;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  return (
    <details
      className="fold group rounded-[24px] bg-card px-[clamp(22px,3vw,32px)] shadow-[0_1px_2px_rgb(0_0_0/0.05),0_18px_40px_-24px_rgb(0_0_0/0.28)]"
      open={defaultOpen}
    >
      <summary className="flex cursor-pointer list-none items-center justify-between gap-4 py-6 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none [&::-webkit-details-marker]:hidden">
        <span className="flex flex-col gap-1">
          <SectionTitle
            icon={icon}
            tone={tone}
            className="transition-colors group-hover:text-primary"
          >
            {title}
          </SectionTitle>
          {hint ? (
            <span className="pl-11 text-sm text-muted-foreground">{hint}</span>
          ) : null}
        </span>
        <span className="flex size-9 shrink-0 items-center justify-center rounded-full border text-muted-foreground transition-[transform,color,border-color] duration-300 group-open:rotate-90 group-hover:border-foreground/40 group-hover:text-foreground">
          <Chevron />
        </span>
      </summary>
      <div className="flex flex-col gap-10 border-t pt-8 pb-8">{children}</div>
    </details>
  );
}

/*
 * The plain categories of the cost summary. Every "What's inside the price" item (they sum to
 * the planned cost) goes into exactly one category by its config key, so the categories add up
 * to the planned cost without re-allocating anything.
 */
interface Category {
  key: string;
  label: string;
  covers: string;
  when: "once" | "recurring" | "mixed" | "charges";
}

const CATEGORIES: Category[] = [
  {
    key: "development",
    label: "Software development",
    covers:
      "Design, building every feature, testing, documents and project management.",
    when: "once",
  },
  {
    key: "launch",
    label: "Launch and deployment",
    covers:
      "Security audit, certification, training and help right after go-live.",
    when: "once",
  },
  {
    key: "support",
    label: "Support and maintenance",
    covers:
      "Bug fixes, security updates, small changes and any helpdesk after launch.",
    when: "recurring",
  },
  {
    key: "hosting",
    label: "Hosting and infrastructure",
    covers:
      "Live servers, database, storage, backups, test servers and any hardware.",
    when: "mixed",
  },
  {
    key: "tools",
    label: "AI services and third-party tools",
    covers:
      "AI usage, SMS / email and other paid services, licences and the team's tool subscriptions.",
    when: "mixed",
  },
  {
    key: "charges",
    label: "Margin, risk buffer and tax",
    covers:
      "Profit margin, buffer for unknowns, cost of money, handover and GST.",
    when: "charges",
  },
];

const ITEM_CATEGORY: Record<string, string> = {
  ai_review: "development",
  team_design: "development",
  team_build: "development",
  team_ai: "development",
  team_test: "development",
  translation: "development",
  pm: "development",
  governance: "development",
  security_audit: "launch",
  certification: "launch",
  training: "launch",
  hypercare: "launch",
  support_team: "support",
  helpdesk: "support",
  onsite: "support",
  annual_audit: "support",
  hosting: "hosting",
  ssl_domain: "hosting",
  test_servers: "hosting",
  hardware: "hosting",
  ai_coding: "tools",
  dev_tools: "tools",
  ai_usage: "tools",
  services: "tools",
  licences: "tools",
  margin: "charges",
  buffer: "charges",
  finance: "charges",
  exit: "charges",
  tax: "charges",
};

/** Items the backend could not place ("Other") fall back to their group / stage. */
const GROUP_CATEGORY: Record<string, string> = {
  pre_build: "development",
  build: "development",
  programme: "development",
  management: "development",
  go_live: "launch",
  launch: "launch",
  run: "support",
  commercial: "charges",
};

function categoryOf(item: CostItem): string {
  const base = item.key.split(".")[0];
  return ITEM_CATEGORY[base] ?? GROUP_CATEGORY[item.group] ?? "development";
}

/** Recurring items paid for by use (the bill moves with traffic), not a fixed monthly cost. */
const USAGE_BASED = new Set(["ai_usage", "services"]);

function isRecurring(item: CostItem): boolean {
  return item.group === "run";
}

function sum(items: CostItem[]): number {
  return items.reduce((s, i) => s + i.amount_paise, 0);
}

/** Running cost per year after launch (before margin, risk buffer and tax): the average of the
 * support years, or null without support. */
export function runningPerYear(summary: QuickSummary): number | null {
  const years = summary.support_years;
  return years > 0 ? sum(summary.cost_items.filter(isRecurring)) / years : null;
}

/** Low and high ends of items: each item's share of the price's range, so they add up. */
function sumRange(items: CostItem[]): [number, number] {
  return [
    items.reduce((s, i) => s + i.low_paise, 0),
    items.reduce((s, i) => s + i.high_paise, 0),
  ];
}

function WhenBadge({ when, years }: { when: Category["when"]; years: number }) {
  const text =
    when === "once"
      ? "One-time"
      : when === "recurring"
        ? years > 0
          ? `Yearly, ${yearsText(years)} included`
          : "Not included"
        : when === "mixed"
          ? "One-time and yearly"
          : "On the whole price";
  return (
    <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
      {text}
    </span>
  );
}

/** Shades for the price categories, from the palette: the accent for the work, the likely
 * mark and green next, greys after. */
const SHADES = [
  "var(--primary)",
  "var(--tape-2)",
  "var(--warm)",
  "var(--ai)",
  "var(--muted-foreground)",
  "var(--input)",
  "var(--border)",
];

/** The categories as one bar, each part as wide as its share of the price. */
function ShareBar({ rows }: { rows: { key: string; amount: number }[] }) {
  const total = rows.reduce((s, r) => s + r.amount, 0);
  if (total <= 0) return null;
  return (
    <div
      aria-hidden="true"
      className="band-open flex h-3 w-full gap-0.5 overflow-hidden rounded-sm [--to-left:0%] [--to-right:100%]"
    >
      {rows.map((r, i) => (
        <span
          key={r.key}
          style={{
            width: `${(100 * r.amount) / total}%`,
            background: SHADES[i % SHADES.length],
          }}
        />
      ))}
    </div>
  );
}

/** The quote in a few plain categories, each a range: its share of the price's range. */
export function CostSummary({ summary }: { summary: QuickSummary }) {
  const money = moneyOf(summary);
  const range = (low: number | null, high: number | null) =>
    formatRange(low, high, summary.currency);
  const years = summary.support_years;
  const items = summary.cost_items;

  // Older estimates have no item list: show the stored plain parts as they are.
  const rows: {
    key: string;
    label: string;
    amount: number;
    low: number;
    high: number;
    when: Category["when"] | null;
  }[] =
    items.length > 0
      ? CATEGORIES.map((c) => {
          const mine = items.filter((i) => categoryOf(i) === c.key);
          const [low, high] = sumRange(mine);
          return {
            key: c.key,
            label: c.label,
            amount: sum(mine),
            low,
            high,
            when: c.when,
          };
        }).filter((r) => r.amount > 0)
      : summary.parts.map((p) => ({
          key: p.key,
          label: p.label,
          amount: p.amount_paise,
          low: p.low_paise,
          high: p.high_paise,
          when: null,
        }));

  return (
    <section className="sheet">
      <SectionTitle icon={ChartPieSliceIcon}>
        What the price is made of
      </SectionTitle>
      <ShareBar rows={rows} />
      <ul className="flex flex-col divide-y">
        {rows.map((r) => (
          <li
            key={r.key}
            className="flex flex-wrap items-start justify-between gap-x-6 gap-y-1 py-3"
          >
            <span className="flex max-w-xl flex-col gap-1">
              <span className="flex flex-wrap items-center gap-2 font-medium">
                <span
                  aria-hidden="true"
                  className="size-2.5 rounded-sm"
                  style={{
                    background: SHADES[rows.indexOf(r) % SHADES.length],
                  }}
                />
                {r.label}
                {r.when ? <WhenBadge when={r.when} years={years} /> : null}
              </span>
            </span>
            <span className="font-semibold tabular-nums">
              {range(r.low, r.high)}
            </span>
          </li>
        ))}
        <li className="flex flex-wrap items-baseline justify-between gap-x-6 py-3">
          <span className="flex flex-col">
            <span className="font-semibold">Total</span>
            <span className="text-sm text-muted-foreground">
              Most likely {money(summary.likely_paise)}
            </span>
          </span>
          <span className="text-lg font-semibold text-primary tabular-nums">
            {range(summary.low_paise, summary.high_paise)}
          </span>
        </li>
      </ul>
      <p className="text-sm text-muted-foreground">
        No one can know the exact cost in advance, so every part is a range: its
        share of the total range. The parts add up to the total.
      </p>
    </section>
  );
}

function ListGroup({
  title,
  tone,
  empty,
  entries,
}: {
  title: string;
  tone: "included" | "separate" | "confirm";
  empty: string | null;
  entries: React.ReactNode[];
}) {
  const items = entries.filter(Boolean);
  if (items.length === 0 && empty === null) return null;
  const markClass =
    tone === "included"
      ? "bg-success"
      : tone === "separate"
        ? "bg-muted-foreground"
        : "bg-warning";
  return (
    <div className="flex flex-col gap-2">
      <h3 className="border-b pb-2 font-semibold">{title}</h3>
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">{empty}</p>
      ) : (
        <ul className="flex flex-col gap-2 text-sm">
          {items.map((child, i) => (
            <li key={i} className="flex items-start gap-2">
              <span
                aria-hidden="true"
                className={`mt-[0.55em] size-1.5 shrink-0 rounded-full ${markClass}`}
              />
              <span className="flex flex-col">{child}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** What the price covers: features, parts the features need, launch, support and charges
 * (inside "More details"). */
export function IncludedList({ summary }: { summary: QuickSummary }) {
  const money = moneyOf(summary);
  const years = summary.support_years;
  const priced = (summary.scope_items ?? []).filter((s) => !s.partly_priced);
  const launch = summary.cost_items.filter((i) => i.group === "launch");
  const has = (key: string) =>
    summary.cost_items.some((i) => i.key.split(".")[0] === key);
  // the user's own features are priced from a general size block: said so, in client words
  const custom = new Set(summary.custom_features ?? []);
  const listed = summary.features.filter((f) => !custom.has(f));
  const own = summary.features.filter((f) => custom.has(f));
  const included: React.ReactNode[] = [
    listed.length > 0 ? (
      <>
        <span className="font-medium">
          {listed.length} feature{listed.length === 1 ? "" : "s"} from our price
          list
        </span>
        <span className="text-muted-foreground">{listed.join(", ")}</span>
      </>
    ) : null,
    own.length > 0 ? (
      <>
        <span className="font-medium">
          {own.length} custom feature{own.length === 1 ? "" : "s"}
        </span>
        <span className="text-muted-foreground">
          {own.join(", ")}. Priced from a general size estimate, so less
          certain.
        </span>
      </>
    ) : null,
    ...priced.map((s) => (
      <>
        <span className="font-medium">{s.label}</span>
        <span className="text-muted-foreground">
          {s.amount_paise > 0
            ? `Adds ${money(s.amount_paise)} of building work.`
            : "Already covered by another building block, so nothing was added."}
        </span>
      </>
    )),
    launch.length > 0 ? (
      <>
        <span className="font-medium">Launch</span>
        <span className="text-muted-foreground">
          {launch.map((i) => i.label).join(", ")}
        </span>
      </>
    ) : null,
    years > 0 ? (
      <>
        <span className="font-medium">
          Support for {yearsText(years)} after launch
        </span>
        <span className="text-muted-foreground">
          {has("hosting")
            ? "Including hosting the live system."
            : "Hosting the live system is not in this price."}
        </span>
      </>
    ) : null,
    <span key="charges" className="font-medium">
      {has("pm")
        ? "Project management, margin, risk buffer and tax"
        : "Margin, risk buffer and tax"}
    </span>,
  ];
  return (
    <ListGroup
      title="What's included"
      tone="included"
      empty={null}
      entries={included}
    />
  );
}

/** One answer the price rests on: what it was priced as, and what other answers change. */
interface AnswerRow {
  key: string;
  question: string;
  answer: string;
  why: string | null;
  option: PricedOption | null;
}

function AnswerLine({
  row,
  currency,
}: {
  row: AnswerRow;
  currency: QuickSummary["currency"];
}) {
  const others =
    row.option?.options.filter(
      (c) => c.change_paise !== null && c.change_paise !== 0,
    ) ?? [];
  return (
    <li className="flex flex-col gap-0.5 py-2.5 text-sm">
      <span>
        <span className="text-muted-foreground">{row.question}</span>{" "}
        <span className="font-medium">{row.answer}</span>
        {row.why ? (
          <span className="ml-2 text-xs text-muted-foreground">
            ({row.why})
          </span>
        ) : null}
      </span>
      {others.length > 0 ? (
        <span className="text-muted-foreground">
          If not:{" "}
          {others
            .slice(0, 3)
            .map((c) => `${c.label} ${signed(c.change_paise ?? 0, currency)}`)
            .join(" · ")}
        </span>
      ) : null}
    </li>
  );
}

const SHOWN_ANSWERS = 4;

/**
 * Everything to check before the price is sent, in one place: the answers nobody gave
 * (largest price effect first, each with what another answer would change), what is not in
 * the price, what the client pays providers itself, what still needs confirming, and
 * features that usually need something not ticked.
 */
export function CheckBeforeSending({
  summary,
  options,
}: {
  summary: QuickSummary;
  options: PricedOption[];
}) {
  const money = moneyOf(summary);
  const byKey = new Map(options.map((o) => [o.key, o]));
  const open = options.filter((o) => o.why !== "left_out");
  const openKeys = new Set(open.map((o) => o.key));
  const assumed = new Map(summary.assumed.map((a) => [a.key, a]));
  const answers: AnswerRow[] = [
    ...open.map((o) => ({
      key: o.key,
      question: o.question,
      answer: assumed.get(o.key)?.answer ?? o.priced_as,
      why: o.why === "not_sure" ? "you said not sure" : null,
      option: o,
    })),
    ...summary.assumed
      .filter((a) => !openKeys.has(a.key))
      .map((a) => ({
        key: a.key,
        question: a.question,
        answer: a.answer,
        why: null,
        option: null,
      })),
  ];
  const top = answers.slice(0, SHOWN_ANSWERS);
  const more = answers.slice(SHOWN_ANSWERS);

  const notIncluded = summary.not_included.map((item) => {
    const option = byKey.get(item.question_key ?? "");
    return (
      <>
        <span className="font-medium">{item.label}</span>
        <span className="text-muted-foreground">
          {NOT_INCLUDED_WHY[item.why]}
          {option?.why === "left_out" && option.low_change_paise !== null
            ? `. If required: ${changeRange(option, summary.currency)}`
            : ""}
        </span>
      </>
    );
  });
  const clientPays = summary.client_pays.map((c) => (
    <>
      <span className="font-medium">{c.label}</span>
      <span className="text-muted-foreground">
        {c.first_year_paise !== null
          ? `${money(c.first_year_paise)} in the first year`
          : "Depends on use"}
      </span>
    </>
  ));
  const usage = summary.cost_items.filter((i) =>
    USAGE_BASED.has(i.key.split(".")[0]),
  );
  const confirm: React.ReactNode[] = [
    ...(summary.scope_items ?? [])
      .filter((s) => s.partly_priced)
      .map((s) => (
        <>
          <span className="font-medium">{s.label} (partly priced)</span>
          <span className="text-muted-foreground">{s.note}</span>
        </>
      )),
    ...(summary.researched ?? []).map((r) => (
      <>
        <span className="font-medium">{r.name}</span>
        <span className="text-muted-foreground">
          Not in our price list: priced from{" "}
          {r.method === "web" ? "published sources" : "similar features"}.
          Confirm what it includes.
        </span>
      </>
    )),
    usage.length > 0 ? (
      <>
        <span className="font-medium">Bills that follow use</span>
        <span className="text-muted-foreground">
          {usage.map((i) => i.label).join(", ")}: the real bill follows real
          use.
        </span>
      </>
    ) : null,
  ].filter(Boolean);
  const warnings = summary.prerequisites ?? [];
  const lists = notIncluded.length + clientPays.length + confirm.length;
  if (answers.length + lists + warnings.length === 0) return null;

  return (
    <section className="sheet">
      <div>
        <SectionTitle icon={ListChecksIcon} tone="warning">
          Check before you send
        </SectionTitle>
        <p className="pl-11 text-sm text-muted-foreground">
          The price rests on these. If one is wrong, change it and price it
          again.
        </p>
      </div>
      {answers.length > 0 ? (
        <div className="flex flex-col">
          <h3 className="font-semibold">
            Answers we assumed{" "}
            <span className="font-normal text-muted-foreground">
              ({answers.length}
              {open.length > 0 ? ", biggest effect first" : ""})
            </span>
          </h3>
          <ul className="flex flex-col divide-y">
            {top.map((r) => (
              <AnswerLine key={r.key} row={r} currency={summary.currency} />
            ))}
          </ul>
          {more.length > 0 ? (
            <details className="text-sm">
              <summary className="w-fit cursor-pointer list-none py-1 font-medium text-primary hover:underline [&::-webkit-details-marker]:hidden">
                Show {more.length} more
              </summary>
              <ul className="flex flex-col divide-y">
                {more.map((r) => (
                  <AnswerLine key={r.key} row={r} currency={summary.currency} />
                ))}
              </ul>
            </details>
          ) : null}
        </div>
      ) : null}
      {lists > 0 ? (
        <div className="grid gap-6 md:grid-cols-3">
          <ListGroup
            title="Not in this price"
            tone="separate"
            empty={null}
            entries={notIncluded}
          />
          <ListGroup
            title={
              summary.mode === "client"
                ? "Also budget for (other providers)"
                : "The client pays providers directly"
            }
            tone="separate"
            empty={null}
            entries={clientPays}
          />
          <ListGroup
            title="To confirm"
            tone="confirm"
            empty={null}
            entries={confirm}
          />
        </div>
      ) : null}
      <PrerequisiteWarnings items={warnings} />
    </section>
  );
}
