"use client";

import * as React from "react";

import type { PricedOption, QuickSummary } from "@/lib/api/client";
import { formatApprox } from "@/lib/format";
import { cn } from "@/lib/utils";

import { biggestOpenAnswer, changeRange } from "./check";

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
    <svg
      aria-hidden="true"
      viewBox="0 0 16 16"
      className={cn("inline-block size-3.5 align-[-2px]", className)}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M6 3.5 10.5 8 6 12.5" />
    </svg>
  );
}

/** A collapsed section: the title (and a one-line hint) stays visible, the rest opens on click. */
export function Disclosure({
  title,
  hint,
  defaultOpen = false,
  children,
}: {
  title: string;
  hint?: React.ReactNode;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  return (
    <details className="fold group border-t" open={defaultOpen}>
      <summary className="flex cursor-pointer list-none items-center justify-between gap-4 py-6 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none [&::-webkit-details-marker]:hidden">
        <span className="flex flex-col gap-0.5">
          <h2 className="text-xl font-semibold transition-colors group-hover:text-primary">
            {title}
          </h2>
          {hint ? (
            <span className="text-sm text-muted-foreground">{hint}</span>
          ) : null}
        </span>
        <span className="flex size-9 shrink-0 items-center justify-center rounded-full border text-muted-foreground transition-[transform,color,border-color] duration-300 group-open:rotate-90 group-hover:border-foreground/40 group-hover:text-foreground">
          <Chevron />
        </span>
      </summary>
      <div className="flex flex-col gap-10 pt-2 pb-10">{children}</div>
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

/** Shades for the price categories: blues for the work, saffron for support, greys after. */
const SHADES = [
  "var(--primary)",
  "#4fa9de",
  "#a6d8f5",
  "#f2a541",
  "#556070",
  "#a5afbc",
  "#d5dbe2",
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

/** The quote in a few plain categories that add up to the most likely price. */
export function CostSummary({ summary }: { summary: QuickSummary }) {
  const money = moneyOf(summary);
  const years = summary.support_years;
  const risk = summary.risk_allowance_paise;
  const items = summary.cost_items;

  // Older estimates have no item list: show the stored plain parts as they are.
  const rows: {
    key: string;
    label: string;
    amount: number;
    when: Category["when"] | null;
  }[] =
    items.length > 0
      ? CATEGORIES.map((c) => ({
          key: c.key,
          label: c.label,
          amount: sum(items.filter((i) => categoryOf(i) === c.key)),
          when: c.when,
        })).filter((r) => r.amount > 0)
      : summary.parts.map((p) => ({
          key: p.key,
          label: p.label,
          amount: p.amount_paise,
          when: null,
        }));

  return (
    <section className="sheet">
      <div>
        <h2 className="text-xl font-semibold">What the price is made of</h2>
      </div>
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
              {money(r.amount)}
            </span>
          </li>
        ))}
        {risk !== null && risk > 0 ? (
          <li className="flex flex-wrap items-start justify-between gap-x-6 gap-y-1 py-3">
            <span className="flex max-w-xl flex-col gap-1">
              <span className="font-medium">Expected overrun (risk)</span>
              <span className="text-sm text-muted-foreground">
                How far work usually runs over the plan, from simulation.
              </span>
            </span>
            <span className="font-semibold tabular-nums">{money(risk)}</span>
          </li>
        ) : null}
        <li className="flex flex-wrap items-baseline justify-between gap-x-6 py-3">
          <span className="font-semibold">Most likely price</span>
          <span className="text-lg font-semibold text-primary tabular-nums">
            {money(summary.likely_paise)}
          </span>
        </li>
      </ul>
      {summary.client_pays.length > 0 ? (
        <p className="text-sm text-muted-foreground">
          <strong className="text-foreground">Not in this price:</strong>{" "}
          {summary.client_pays_first_year_paise > 0
            ? `${money(summary.client_pays_first_year_paise)} in the first year that the client pays providers directly`
            : "fees the client pays providers directly"}{" "}
          ({summary.client_pays.map((c) => c.label.toLowerCase()).join(", ")}).
        </p>
      ) : null}
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

/** What the quote covers, what the client pays separately, and what still needs checking. */
export function WhatsIncluded({
  summary,
  options = [],
}: {
  summary: QuickSummary;
  options?: PricedOption[];
}) {
  const money = moneyOf(summary);
  const open = biggestOpenAnswer(options);
  const years = summary.support_years;
  const scopeItems = summary.scope_items ?? [];
  const priced = scopeItems.filter((s) => !s.partly_priced);
  const partly = scopeItems.filter((s) => s.partly_priced);
  const launch = summary.cost_items.filter((i) => i.group === "launch");
  const has = (key: string) =>
    summary.cost_items.some((i) => i.key.split(".")[0] === key);
  const usage = summary.cost_items.filter((i) =>
    USAGE_BASED.has(i.key.split(".")[0]),
  );

  const included: React.ReactNode[] = [
    summary.features.length > 0 ? (
      <>
        <span className="font-medium">
          {summary.features.length} feature
          {summary.features.length === 1 ? "" : "s"} you confirmed
        </span>
        <span className="text-muted-foreground">
          {summary.features.join(", ")}
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

  const separate: React.ReactNode[] = summary.client_pays.map((c) => (
    <>
      <span className="font-medium">{c.label}</span>
      <span className="text-muted-foreground">
        {c.first_year_paise !== null
          ? `${money(c.first_year_paise)} in the first year.`
          : "Not estimated: depends on use."}
        {c.note ? ` ${c.note}` : ""}
      </span>
    </>
  ));

  const confirm: React.ReactNode[] = [
    ...partly.map((s) => (
      <>
        <span className="font-medium">{s.label} (partly priced)</span>
        <span className="text-muted-foreground">
          {s.amount_paise > 0 ? `${money(s.amount_paise)} added. ` : ""}
          {s.note}
        </span>
      </>
    )),
    ...(summary.researched ?? []).map((r) => (
      <>
        <span className="font-medium">
          {r.name} (
          {r.method === "web"
            ? "hours from published sources"
            : "hours from similar catalog blocks"}
          )
        </span>
        <span className="text-muted-foreground">
          Not in the catalog; low confidence, confirm the scope.
          {r.sources
            .filter((s) => s.url)
            .map((s, i) => (
              <a
                key={`${s.url}-${i}`}
                href={s.url ?? undefined}
                target="_blank"
                rel="noopener noreferrer"
                className="ml-1 underline underline-offset-2"
              >
                Source {i + 1}
              </a>
            ))}
        </span>
      </>
    )),
    ...summary.not_sure.map((q) => (
      <>
        <span className="font-medium">{q}</span>
        <span className="text-muted-foreground">
          Answered &quot;Not sure&quot;.
        </span>
      </>
    )),
    usage.length > 0 ? (
      <>
        <span className="font-medium">Usage-based bills</span>
        <span className="text-muted-foreground">
          {usage.map((i) => i.label).join(", ")}: priced from expected use; the
          real bill follows real use.
        </span>
      </>
    ) : null,
    open || summary.biggest_uncertainty ? (
      <>
        <span className="font-medium">What could change the price most</span>
        <span className="text-muted-foreground">
          {open
            ? `Your answer to "${open.question}" (priced as ${open.priced_as}): another answer changes the price by ${changeRange(open, summary.currency)}, past the range shown. `
            : ""}
          {summary.biggest_uncertainty}
        </span>
      </>
    ) : null,
  ];

  return (
    <Disclosure
      title="What's included and what's not"
      hint={`${included.filter(Boolean).length} included · ${separate.length} paid separately · ${confirm.filter(Boolean).length} to confirm`}
    >
      <div className="grid gap-6 md:grid-cols-3">
        <ListGroup
          title="Included in this estimate"
          tone="included"
          empty={null}
          entries={included}
        />
        <ListGroup
          title="Paid separately by the client"
          tone="separate"
          empty="Nothing found that the client pays providers directly."
          entries={separate}
        />
        <ListGroup
          title="Needs confirmation"
          tone="confirm"
          empty="No open points were recorded for this estimate."
          entries={confirm}
        />
      </div>
    </Disclosure>
  );
}

function Tile({
  label,
  value,
  note,
  strong = false,
}: {
  label: string;
  value: string;
  note: string;
  strong?: boolean;
}) {
  return (
    <div
      className={cn(
        "flex flex-col gap-1 border-l pl-4",
        strong && "border-primary",
      )}
    >
      <span className="figure-label">{label}</span>
      <span
        className={cn(
          "text-xl font-semibold tracking-tight tabular-nums",
          strong && "text-primary",
        )}
      >
        {value}
      </span>
      {note ? (
        <span className="text-xs text-muted-foreground">{note}</span>
      ) : null}
    </div>
  );
}

/** One-time vs running costs and the total cost of ownership over the support years. */
export function OngoingCosts({ summary }: { summary: QuickSummary }) {
  const items = summary.cost_items;
  if (items.length === 0 || summary.likely_paise === null) return null;
  const money = moneyOf(summary);
  const years = summary.support_years;
  const running = items.filter(isRecurring);
  const fixed = running.filter((i) => !USAGE_BASED.has(i.key.split(".")[0]));
  const usage = running.filter((i) => USAGE_BASED.has(i.key.split(".")[0]));
  const oneTime = items.filter(
    (i) => !isRecurring(i) && categoryOf(i) !== "charges",
  );
  const runningTotal = sum(running);
  const perYear = years > 0 ? runningTotal / years : null;
  const sized = summary.client_pays.filter((c) => c.total_paise !== null);
  const unsized = summary.client_pays.filter((c) => c.total_paise === null);
  const clientTotal = sized.reduce((s, c) => s + (c.total_paise ?? 0), 0);
  const ownership = summary.likely_paise + clientTotal;

  return (
    <section className="sheet">
      <div>
        <h2 className="text-xl font-semibold">One-time and running costs</h2>
        <p className="figure-label">Before margin, risk buffer and tax</p>
      </div>
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <Tile
          label="One-time: build and launch"
          value={money(sum(oneTime))}
          note=""
        />
        <Tile
          label="Running cost per year"
          value={perYear !== null ? money(perYear) : "Not included"}
          note={perYear !== null ? `Average of ${yearsText(years)}` : ""}
        />
        <Tile
          label="Running cost per month"
          value={perYear !== null ? money(perYear / 12) : "Not included"}
          note=""
        />
        <Tile
          strong
          label={
            years > 0
              ? `Total cost over ${yearsText(years)}`
              : "Total cost with client-paid items"
          }
          value={money(ownership)}
          note={
            clientTotal > 0
              ? `Includes ${money(clientTotal)} paid to providers`
              : ""
          }
        />
      </div>
      {running.length > 0 ? (
        <dl className="grid gap-x-8 gap-y-3 text-sm sm:grid-cols-2">
          {fixed.length > 0 ? (
            <div>
              <dt className="font-medium">
                Fixed every year ({money(sum(fixed))} over {yearsText(years)})
              </dt>
              <dd className="text-muted-foreground">
                {fixed.map((i) => i.label).join(", ")}
              </dd>
            </div>
          ) : null}
          {usage.length > 0 ? (
            <div>
              <dt className="font-medium">
                Depends on use ({money(sum(usage))} over {yearsText(years)})
              </dt>
              <dd className="text-muted-foreground">
                {usage.map((i) => i.label).join(", ")}
              </dd>
            </div>
          ) : null}
        </dl>
      ) : null}
      {unsized.length > 0 ? (
        <p className="text-sm text-muted-foreground">
          Not counted in the total because it depends on use:{" "}
          {unsized.map((c) => c.label.toLowerCase()).join(", ")}.
        </p>
      ) : null}
    </section>
  );
}
