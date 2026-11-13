"use client";

import * as React from "react";
import {
  HardDrivesIcon,
  ScalesIcon,
  TimerIcon,
  TreeStructureIcon,
} from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";
import { useParams } from "next/navigation";

import { AppHero } from "@/components/app-hero";
import { useCurrentUser } from "@/components/auth-guard";
import { ErrorNotice, Loading } from "@/components/status";
import { Button, buttonVariants } from "@/components/ui/button";
import { api, errorText, type QuickSummary } from "@/lib/api/client";
import {
  formatApprox,
  formatPaise,
  formatDate,
  formatDecimal,
  formatRange,
  monthsToWeeks,
  monthsToWeeksUp,
} from "@/lib/format";
import { useLoad } from "@/lib/use-load";

import { BidResultCard } from "./bid-result";
import { CompareOptions } from "./compare";
import { CompareQuotes } from "./quotes";
import {
  CheckBeforeSending,
  Chevron,
  CostSummary,
  Disclosure,
  IncludedList,
  SectionTitle,
} from "./cost-summary";
import {
  exportBlocked,
  IndependentCheckCard,
  SizeCheckCard,
  usePricedOptions,
} from "./check";
import { Downloads } from "./downloads";
import { RealityCheck } from "./reality";
import { FeatureStoriesSection } from "./stories";
import {
  AiSavingSources,
  RowSourcesNote,
  SourcesList,
  SourcesProvider,
} from "./sources";

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="figure-label">{label}</dt>
      <dd className="font-medium tabular-nums">{value}</dd>
    </div>
  );
}

/** "₹ 1.2 Cr": a rounded amount without the "about". */
function shortMoney(paise: number | null, currency: QuickSummary["currency"]) {
  return formatApprox(paise, currency).replace("about ", "");
}

/**
 * The range measured out on a ruler that starts at zero, so the band's width shows how sure
 * the price is. The band opens from the most likely mark.
 */
function RangeBand({ summary }: { summary: QuickSummary }) {
  const low = summary.low_paise;
  const high = summary.high_paise;
  const likely = summary.likely_paise;
  if (low === null || high === null || likely === null || high <= low)
    return null;
  const top = high * 1.08;
  const pos = (paise: number) => (100 * paise) / top;
  const at = (100 * (likely - low)) / (high - low);
  return (
    <div className="flex flex-col gap-2">
      <div className="relative h-9" aria-hidden="true">
        <div
          className="absolute inset-x-0 bottom-0 h-2 opacity-60"
          style={{
            backgroundImage:
              "repeating-linear-gradient(90deg, var(--input) 0 1px, transparent 1px 10%)",
          }}
        />
        <div className="absolute inset-x-0 bottom-0 h-px bg-input" />
        <div
          className="band-open absolute bottom-0 h-5 rounded-sm bg-tape-soft ring-1 ring-primary/40"
          style={
            {
              left: `${pos(low)}%`,
              width: `${pos(high) - pos(low)}%`,
              "--to-left": `${at}%`,
              "--to-right": `${100 - at}%`,
            } as React.CSSProperties
          }
        />
        <div
          className="mark-drop absolute bottom-0 h-9 w-1 -translate-x-1/2 rounded-full bg-warm"
          style={{ left: `${pos(likely)}%` }}
        />
      </div>
      <div className="flex justify-between gap-4 text-sm tabular-nums">
        <span>
          <span className="text-muted-foreground">Low </span>
          <span className="font-medium">
            {shortMoney(low, summary.currency)}
          </span>
        </span>
        <span>
          <span className="text-muted-foreground">High </span>
          <span className="font-medium">
            {shortMoney(high, summary.currency)}
          </span>
        </span>
      </div>
    </div>
  );
}

function Headline({ summary }: { summary: QuickSummary }) {
  const years = summary.support_years;
  const approx = (paise: number | null) =>
    formatApprox(paise, summary.currency);
  const risk = summary.risk_allowance_paise;
  const tax = summary.currency === "INR" ? "GST" : "tax";
  // a description is quoted as vendors quote (build, then running, + tax); a tender bids the
  // whole contract, so its total leads
  const quoteFirst =
    !summary.from_document && (summary.quote_build_paise ?? 0) > 0;
  return (
    <section
      aria-labelledby="estimate-heading"
      className="slab app-rise flex flex-col gap-8 px-6 py-8 sm:px-10 sm:py-10"
    >
      <div className="flex flex-wrap items-end justify-between gap-x-10 gap-y-4">
        {quoteFirst ? (
          // like a vendor's quote (OPEN_QUESTIONS 208): the build, then running, both + tax
          <div className="settle flex flex-col gap-1">
            <h2 id="estimate-heading" className="figure-label">
              {summary.mode === "client"
                ? "Fair budget to build and launch"
                : "Price to build and launch"}
              , most likely
            </h2>
            <span className="font-wide mt-1 text-[clamp(3rem,7vw,4.5rem)] leading-none text-tape-bright tabular-nums">
              {shortMoney(summary.quote_build_paise ?? null, summary.currency)}
              <span className="ml-2 align-baseline text-xl text-muted-foreground">
                + {tax}
              </span>
            </span>
            {summary.quote_running_per_year_paise ? (
              <span className="text-base tabular-nums">
                Then running:{" "}
                {shortMoney(
                  summary.quote_running_per_year_paise,
                  summary.currency,
                )}{" "}
                a year + {tax}
              </span>
            ) : null}
          </div>
        ) : (
          <div className="settle flex flex-col gap-1">
            <h2 id="estimate-heading" className="figure-label">
              {summary.mode === "client"
                ? "Fair budget, most likely"
                : "Most likely price"}
              , with {tax}
            </h2>
            <span className="font-wide mt-1 text-[clamp(3rem,7vw,4.5rem)] leading-none text-tape-bright tabular-nums">
              {shortMoney(summary.likely_paise, summary.currency)}
            </span>
            {summary.likely_without_tax_paise ? (
              <span className="text-sm text-muted-foreground tabular-nums">
                {shortMoney(summary.likely_without_tax_paise, summary.currency)}{" "}
                without {tax}
                {summary.quote_build_paise
                  ? `: ${shortMoney(summary.quote_build_paise, summary.currency)} to build and launch`
                  : ""}
              </span>
            ) : null}
          </div>
        )}
        <p className="settle max-w-xs text-sm text-muted-foreground [--d:2]">
          An early estimate, not a quotation.{" "}
          {quoteFirst
            ? "Includes margin and a safety buffer."
            : summary.support_term_open
              ? "Includes one year of support, margin and tax."
              : years > 0
                ? `Includes ${years} year${years === 1 ? "" : "s"} of support, margin and tax.`
                : "Building and launch only, with margin and tax."}
        </p>
      </div>

      <div className="flex flex-col gap-1">
        <p className="text-sm text-muted-foreground">
          {quoteFirst
            ? `Whole price with ${
                summary.support_term_open || years === 1
                  ? "one year"
                  : `${years} years`
              } of running and ${tax}: most likely `
            : "Most likely "}
          <span className="font-medium text-foreground tabular-nums">
            {shortMoney(summary.likely_paise, summary.currency)}
          </span>
          , and it could be anywhere in this range:
        </p>
        <RangeBand summary={summary} />
      </div>

      {summary.deadline_priced_months && summary.deadline_asked_months ? (
        <p className="settle rounded-lg bg-warning-muted px-4 py-3 text-sm text-warning">
          Your deadline of{" "}
          {monthsToWeeks(Number(summary.deadline_asked_months))} weeks is
          shorter than the fastest possible: more people would not finish
          sooner. This is priced for{" "}
          {monthsToWeeksUp(Number(summary.deadline_priced_months))} weeks, with
          the biggest team that still helps. To keep your date, launch the most
          important features first and the rest later.
        </p>
      ) : null}

      <dl className="settle grid grid-cols-2 gap-x-8 gap-y-5 border-t pt-6 [--d:4] sm:grid-cols-3">
        <Fact
          label="Time to build"
          value={`${formatDecimal(summary.build_months, 1)} months`}
        />
        {summary.team.length > 0 ? (
          <Fact
            label="Team"
            value={`${Math.max(1, Math.round(Number(summary.team_people ?? 0)))} people`}
          />
        ) : null}
        {summary.peak_online ? (
          // how heavily it is used sets the servers; the build size does not
          <Fact
            label="Use"
            value={`${summary.peak_online.toLocaleString("en-IN")} online at once`}
          />
        ) : null}
      </dl>

      <div className="flex flex-col gap-2 border-t pt-5">
        <AiSaving summary={summary} />
        <RealityCheck summary={summary} />
        <SizeCheckCard summary={summary} />
      </div>

      <details className="fold group text-sm">
        <summary className="w-fit cursor-pointer list-none rounded font-medium text-muted-foreground transition-colors hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none [&::-webkit-details-marker]:hidden">
          How this is worked out <Chevron />
        </summary>
        <div className="mt-3 flex max-w-2xl flex-col gap-2 text-muted-foreground">
          <p>
            Every feature&apos;s work is counted in hours and priced at each
            role&apos;s rate; support, hosting, services, margin and tax are
            added. The project is then run thousands of times with different
            amounts of work: 1 in 10 runs came out below the low end (
            {approx(summary.low_paise)}), half below the most likely, 1 in 10
            above the high end ({approx(summary.high_paise)}).
          </p>
          {risk !== null && risk > 0 ? (
            <p>
              Planned {approx(summary.planned_paise)} + expected overrun{" "}
              {approx(risk)} = most likely {approx(summary.likely_paise)}.
            </p>
          ) : null}
          {summary.accuracy_note ? <p>{summary.accuracy_note}</p> : null}
        </div>
      </details>
    </section>
  );
}

/** What real projects of this size were bought for: an outside benchmark, not a check. */
function MarketBox({ summary }: { summary: QuickSummary }) {
  const market = summary.market;
  if (!market) return null;
  const range = (low: number | null, high: number | null) =>
    formatRange(low, high, summary.currency);
  const approx = (paise: number | null) =>
    formatApprox(paise, summary.currency);
  return (
    <div className="flex flex-col gap-1">
      <h3 className="text-sm font-medium">
        What real {market.project_size.toLowerCase()} projects were bought for
      </h3>
      <span className="text-xl font-semibold tracking-tight tabular-nums">
        {range(market.low_paise, market.high_paise)}
      </span>
      {market.basis === "published_prices" ? (
        <span className="text-sm text-muted-foreground">
          The middle half of the published prices of {market.projects} real
          Indian {market.sizes.join(" and ").toLowerCase()} projects (
          {market.first_year}&ndash;{market.last_year}, in today&apos;s money
          with GST; median {approx(market.mid_paise)}), as published, not
          adjusted to this project. Sources:{" "}
          {market.sources.map((s) => `${s.label} (${s.projects})`).join(", ")}.
          These are prices, not hours: they do not check this estimate. Real
          contracts also carry the vendor&apos;s pricing and work a feature list
          does not show (years of operations, staff on site, hardware).
        </span>
      ) : (
        <span className="text-sm text-muted-foreground">
          {market.projects > 0
            ? `The middle half of ${market.projects} real Indian projects of this size, scaled to this one. `
            : "Between the two nearest sizes of real Indian projects, scaled to this one. "}
          Our estimate is what the work should cost from its hours. Real
          contracts also carry the vendor&apos;s pricing and work a feature list
          does not show (years of operations, staff on site, hardware).
        </span>
      )}
    </div>
  );
}

/** The AI saving in one line; how it is worked out opens below it. */
function AiSaving({ summary }: { summary: QuickSummary }) {
  const withAi = summary.likely_paise;
  const withoutAi = summary.traditional_paise;
  const saved =
    withAi !== null && withoutAi !== null && withoutAi > withAi
      ? withoutAi - withAi
      : (summary.ai_saving?.identified_paise ?? null);
  if (saved === null || saved <= 0) return null;
  const percent = summary.ai_saving_percent ?? summary.ai_saving?.percent;
  const passed = !summary.ai_saving || summary.ai_saving.passed_percent >= 100;
  return (
    <div className="flex flex-col gap-1 text-sm">
      <p className="flex gap-2">
        <span aria-hidden className="font-semibold text-success">
          ✓
        </span>
        <span>
          AI tools save {formatApprox(saved, summary.currency)}
          {percent ? ` (${percent}%)` : ""}:{" "}
          {passed
            ? "already taken off this price"
            : "partly taken off this price"}
          , after the cost of the tools and of checking their work.
        </span>
      </p>
      <div className="pl-5">
        <AiSavingSources />
      </div>
    </div>
  );
}

/** 1234 -> "1,234". */
function hoursText(hours: number): string {
  return Math.round(hours).toLocaleString("en-IN");
}

/** The build in hours: the same work without AI tools, with them, and what AI saved. */
function HoursOfWork({
  summary,
  byRole,
}: {
  summary: QuickSummary;
  byRole: boolean;
}) {
  const h = summary.hours;
  if (!h || h.rows.length === 0) return null;
  const money = (paise: number | null | undefined) =>
    formatApprox(paise ?? null, summary.currency);
  const hasOld = h.without_ai !== null && h.without_ai !== undefined;
  const savedShare =
    hasOld && h.without_ai
      ? Math.round((100 * (h.saved ?? 0)) / h.without_ai)
      : null;
  return (
    <section className="flex flex-col gap-5">
      <div>
        <h3 className="text-base font-semibold">Hours of work</h3>
        <p className="figure-label">{h.hours_per_day} hours a working day</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        {hasOld ? (
          <div className="flex flex-col gap-1 border-l pl-4">
            <span className="text-sm text-muted-foreground">
              Without AI tools
            </span>
            <span className="text-2xl font-semibold text-muted-foreground tabular-nums">
              {hoursText(h.without_ai ?? 0)} h
            </span>
            <span className="text-sm text-muted-foreground">
              {money(h.team_cost_without_ai_paise)}
            </span>
          </div>
        ) : null}
        <div className="flex flex-col gap-1 border-l border-primary pl-4">
          <span className="text-sm font-medium">With AI tools</span>
          <span className="text-2xl font-semibold tabular-nums">
            {hoursText(h.with_ai)} h
          </span>
          <span className="text-sm text-muted-foreground">
            {money(h.team_cost_paise)}
          </span>
        </div>
        {hasOld && (h.saved ?? 0) > 0 ? (
          <div className="flex flex-col gap-1 border-l pl-4 text-ai">
            <span className="text-sm font-medium">Saved by AI tools</span>
            <span className="text-2xl font-semibold tabular-nums">
              {hoursText(h.saved ?? 0)} h
            </span>
            <span className="text-sm">
              {savedShare}% fewer hours, after checking the AI&apos;s work
            </span>
          </div>
        ) : null}
      </div>
      {byRole ? (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[34rem] text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="py-2 pr-4 font-medium">Role</th>
                {hasOld ? (
                  <th className="py-2 pr-4 text-right font-medium">
                    Without AI
                  </th>
                ) : null}
                <th className="py-2 pr-4 text-right font-medium">With AI</th>
                <th className="py-2 text-right font-medium">Rate per hour</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {h.rows.map((r) => (
                <tr key={r.role}>
                  <td className="py-2 pr-4">{r.label}</td>
                  {hasOld ? (
                    <td className="py-2 pr-4 text-right text-muted-foreground tabular-nums">
                      {hoursText(r.hours_without_ai ?? 0)} h
                    </td>
                  ) : null}
                  <td className="py-2 pr-4 text-right font-medium tabular-nums">
                    {hoursText(r.hours_with_ai)} h
                  </td>
                  <td className="py-2 text-right text-muted-foreground tabular-nums">
                    {formatPaise(
                      Math.round(Number(r.rupees_per_hour)) * 100,
                      summary.currency,
                    )}
                    /h
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}

/** Hours and people in total; the split by role (for a bid's price schedule) on request. */
function TeamAndHours({ summary }: { summary: QuickSummary }) {
  const [byRole, setByRole] = React.useState(false);
  const roles =
    summary.team.length > 0 || (summary.hours?.rows.length ?? 0) > 0;
  return (
    <>
      <HoursOfWork summary={summary} byRole={byRole} />
      <TeamNeeded summary={summary} byRole={byRole} />
      {roles ? (
        <button
          type="button"
          className="w-fit rounded text-sm font-medium text-primary hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
          onClick={() => setByRole((now) => !now)}
        >
          {byRole ? "Hide the split by role" : "Show the split by role"}
        </button>
      ) : null}
    </>
  );
}

/** "about 3 people" / "part-time" from an average number of full-time people. */
function peopleText(people: number): string {
  if (people < 0.5) return "part-time";
  const n = Math.round(people);
  return `about ${n} ${n === 1 ? "person" : "people"}`;
}

/** Who is needed to build it: people by role over the build, with and without AI tools. */
function TeamNeeded({
  summary,
  byRole,
}: {
  summary: QuickSummary;
  byRole: boolean;
}) {
  if (summary.team.length === 0) return null;
  const months = Number(summary.build_months);
  const total = Number(summary.team_people ?? 0);
  const hasOld = summary.team.some((r) => r.traditional_people != null);
  const oldTotal = summary.team.reduce(
    (sum, r) => sum + Number(r.traditional_people ?? 0),
    0,
  );
  const pm = (value: string | number | null | undefined) =>
    `${formatDecimal(Number(value ?? 0), 1)} person-months`;
  return (
    <section className="flex flex-col gap-4">
      <div>
        <h3 className="text-base font-semibold">Team needed to build it</h3>
        <p className="text-sm text-muted-foreground">
          About {Math.max(1, Math.round(total))} people working for{" "}
          {formatDecimal(months, 1)} months.
          {hasOld && summary.traditional_build_months
            ? ` Without AI tools: ${Math.max(1, Math.round(oldTotal))} people, ${formatDecimal(Number(summary.traditional_build_months), 1)} months.`
            : ""}
        </p>
      </div>
      {byRole ? (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[32rem] text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="py-2 pr-4 font-medium">Role</th>
                <th className="py-2 pr-4 font-medium">People</th>
                <th className="py-2 pr-4 text-right font-medium">Work</th>
                {hasOld ? (
                  <th className="py-2 text-right font-medium">
                    Without AI tools
                  </th>
                ) : null}
              </tr>
            </thead>
            <tbody className="divide-y">
              {summary.team.map((r) => (
                <tr key={r.role}>
                  <td className="py-2 pr-4">{r.label}</td>
                  <td className="py-2 pr-4 font-medium">
                    {peopleText(Number(r.people))}
                  </td>
                  <td className="py-2 pr-4 text-right text-muted-foreground tabular-nums">
                    {pm(r.person_months)}
                  </td>
                  {hasOld ? (
                    <td className="py-2 text-right text-muted-foreground tabular-nums">
                      {pm(r.traditional_person_months)}
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      <LeftOut summary={summary} />
      {summary.support_team.length > 0 && summary.support_years > 0 ? (
        <p className="text-sm text-muted-foreground">
          <strong className="text-foreground">After launch</strong> (each year):{" "}
          {byRole
            ? summary.support_team
                .map((r) => `${r.label} — ${peopleText(Number(r.people))}`)
                .join("; ")
            : peopleText(
                summary.support_team.reduce((s, r) => s + Number(r.people), 0),
              )}
          .
        </p>
      ) : null}
    </section>
  );
}

/** Roles with too little work to book: someone already on the team does it, a little slower
 * (OPEN_QUESTIONS 229). Roles with no work at all are simply not on the team. */
function LeftOut({ summary }: { summary: QuickSummary }) {
  const rows = summary.team_left_out ?? [];
  if (rows.length === 0) return null;
  const days = (v: string | number) => formatDecimal(Number(v), 1);
  return (
    <div className="flex flex-col gap-1.5 text-sm">
      <p className="font-medium">Not booked for this project</p>
      <ul className="flex flex-col gap-1 text-muted-foreground">
        {rows.map((r) => (
          <li key={r.role}>
            <span className="text-foreground">{r.label}</span>: only{" "}
            {days(r.work_days)} days of work, less than the{" "}
            {days(r.min_booking_days)} days one is booked for, so the{" "}
            {r.done_by_label.toLowerCase()} does it (a little slower).
          </li>
        ))}
      </ul>
    </div>
  );
}

/** What to buy for own servers (OPEN_QUESTIONS 231): sizes and quantities worked out from the
 * people online at once, the uptime and the data kept. A list only: no prices yet. */
function HardwareList({ summary }: { summary: QuickSummary }) {
  const hw = summary.hardware;
  if (!hw) return null;
  const money = (paise: number | null | undefined) =>
    formatApprox(paise ?? null, summary.currency);
  const priced = hw.once_paise != null;
  const free = priced ? hw.items.filter((i) => !i.unit_paise) : [];
  const shown = hw.items.filter((i) => !free.includes(i));
  const freeNames = [...new Set(free.map((i) => i.label))];
  const sites = [
    { key: "main", title: "Main site" },
    {
      key: "standby",
      title: "Standby site (takes over if the main one fails)",
    },
  ].filter((s) => shown.some((i) => i.site === s.key));
  const who =
    hw.who_buys === "client_buys"
      ? "The client buys these, so they are not in the price."
      : priced
        ? "This is in the price."
        : "The servers and storage are in the price; the rest is not priced yet.";
  return (
    <section className="flex flex-col gap-4">
      {priced ? (
        <p>
          <strong>{money(hw.once_paise)}</strong> to buy, once
          {hw.yearly_paise ? (
            <>
              , then <strong>{money(hw.yearly_paise)}</strong> a year for
              licences
            </>
          ) : null}{" "}
          <span className="text-sm text-muted-foreground">(before tax)</span>
        </p>
      ) : null}
      <p className="text-sm text-muted-foreground">
        {who} Our estimate from the number of users and the uptime. If the
        tender lists its own hardware, use that instead.
      </p>
      {sites.map((site) => (
        <div key={site.key} className="flex flex-col gap-2">
          {sites.length > 1 ? (
            <h3 className="text-base font-semibold">{site.title}</h3>
          ) : null}
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="py-2 pr-4 font-medium">Item</th>
                <th className="py-2 pr-4 text-right font-medium">How many</th>
                {priced ? (
                  <th className="py-2 text-right font-medium">Price</th>
                ) : null}
              </tr>
            </thead>
            <tbody className="divide-y">
              {shown
                .filter((i) => i.site === site.key)
                .map((i) => (
                  <tr key={`${i.site}-${i.key}`}>
                    <td className="py-2 pr-4">{i.label}</td>
                    <td className="py-2 pr-4 text-right tabular-nums">
                      {i.quantity}
                    </td>
                    {priced ? (
                      <td className="py-2 text-right whitespace-nowrap tabular-nums">
                        {money(i.amount_paise)}
                        {i.yearly ? " a year" : ""}
                      </td>
                    ) : null}
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      ))}
      {freeNames.length > 0 ? (
        <p className="text-sm text-muted-foreground">
          Free, no licence fee: {freeNames.join(", ").toLowerCase()}.
        </p>
      ) : null}
      {hw.client_costs.length > 0 ? (
        <p className="text-sm text-muted-foreground">
          Not in the price, paid by the client:{" "}
          {hw.client_costs.join("; ").toLowerCase()}.
        </p>
      ) : null}
      <p className="text-sm text-muted-foreground">
        Sizes and the reason for each item are in the Excel download.
      </p>
    </section>
  );
}

/** Building cost of each feature, with the team's AI tools and the traditional way. */
function FeatureCosts({ summary }: { summary: QuickSummary }) {
  const [showOld, setShowOld] = React.useState(false);
  if (summary.feature_costs.length === 0) return null;
  const money = (paise: number | null) => formatApprox(paise, summary.currency);
  const withAi = summary.feature_costs.reduce((s, f) => s + f.amount_paise, 0);
  const oldTotal = summary.feature_costs.every(
    (f) => f.traditional_paise !== null,
  )
    ? summary.feature_costs.reduce((s, f) => s + (f.traditional_paise ?? 0), 0)
    : null;
  const canCompare = oldTotal !== null && oldTotal !== withAi;
  const withoutAi = canCompare && showOld ? oldTotal : null;
  return (
    <section className="flex flex-col gap-4">
      <div>
        <h3 className="text-base font-semibold">
          Building cost of each feature
        </h3>
        {canCompare ? (
          <button
            type="button"
            className="mt-1 rounded text-sm font-medium text-primary hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
            onClick={() => setShowOld((now) => !now)}
          >
            {showOld ? "Hide without AI" : "Show without AI"}
          </button>
        ) : null}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[32rem] text-sm">
          <thead>
            <tr className="border-b text-left text-muted-foreground">
              <th className="py-2 pr-4 font-medium">Feature</th>
              <th className="py-2 pr-4 font-medium">Level</th>
              {withoutAi !== null ? (
                <th className="py-2 pr-4 text-right font-medium">
                  Without AI tools
                </th>
              ) : null}
              <th className="py-2 text-right font-medium">With AI tools</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {summary.feature_costs.map((f) => (
              <tr key={f.label}>
                <td className="py-2 pr-4 align-top">
                  {f.label}
                  <RowSourcesNote row={`feature:${f.label}`} />
                </td>
                <td className="py-2 pr-4 text-muted-foreground">
                  {f.level ?? "—"}
                </td>
                {withoutAi !== null ? (
                  <td className="py-2 pr-4 text-right text-muted-foreground tabular-nums line-through">
                    {money(f.traditional_paise)}
                  </td>
                ) : null}
                <td className="py-2 text-right font-medium tabular-nums">
                  {money(f.amount_paise)}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t font-semibold">
              <td className="py-2 pr-4" colSpan={2}>
                Total building work
              </td>
              {withoutAi !== null ? (
                <td className="py-2 pr-4 text-right text-muted-foreground tabular-nums">
                  {money(withoutAi)}
                </td>
              ) : null}
              <td className="py-2 text-right tabular-nums">{money(withAi)}</td>
            </tr>
          </tfoot>
        </table>
      </div>
      {(summary.scope_items ?? []).length > 0 ? (
        <div className="flex flex-col gap-2">
          <h3 className="font-medium">What else you asked for</h3>
          <ul className="flex flex-col gap-2 text-sm">
            {(summary.scope_items ?? []).map((item) => (
              <li key={item.key} className="flex flex-col gap-0.5">
                <span className="flex flex-wrap justify-between gap-x-4">
                  <span>{item.label}</span>
                  <span className="font-medium tabular-nums">
                    {item.amount_paise > 0
                      ? `+${money(item.amount_paise)}`
                      : "Already included"}
                  </span>
                </span>
                <span className="text-muted-foreground">
                  {item.amount_paise > 0
                    ? `${item.partly_priced ? "Partly priced. " : ""}${item.note}`
                    : "Its building block was already part of this project, so nothing was added."}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

function CostItems({ summary }: { summary: QuickSummary }) {
  if (summary.cost_items.length === 0) return null;
  const range = (low: number, high: number) =>
    formatRange(low, high, summary.currency);
  const groups: { label: string; items: QuickSummary["cost_items"] }[] = [];
  for (const item of summary.cost_items) {
    const last = groups[groups.length - 1];
    if (last && last.label === item.group_label) last.items.push(item);
    else groups.push({ label: item.group_label, items: [item] });
  }
  return (
    <section className="flex flex-col gap-4">
      <div>
        <h3 className="text-base font-semibold">Every cost item</h3>
      </div>
      {
        <div className="flex flex-col gap-5">
          {groups.map((group) => (
            <div key={group.label} className="flex flex-col">
              <h4 className="border-b pb-1 text-sm font-semibold text-muted-foreground">
                {group.label} ·{" "}
                {range(
                  group.items.reduce((s, i) => s + i.low_paise, 0),
                  group.items.reduce((s, i) => s + i.high_paise, 0),
                )}
              </h4>
              <ul className="flex flex-col divide-y">
                {group.items.map((item) => (
                  <li
                    key={item.key}
                    className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-0.5 py-2"
                  >
                    <span className="flex flex-col">
                      <span>{item.label}</span>
                      {item.person_days ? (
                        <span className="text-sm text-muted-foreground">
                          {workRange(item)} of work
                        </span>
                      ) : null}
                      <RowSourcesNote row={`item:${item.group}:${item.key}`} />
                    </span>
                    <span className="flex flex-col items-end">
                      <span className="font-medium tabular-nums">
                        {range(item.low_paise, item.high_paise)}
                      </span>
                      {item.traditional_paise !== null &&
                      item.traditional_paise !== undefined &&
                      item.traditional_paise !== item.amount_paise ? (
                        <span className="text-xs text-muted-foreground tabular-nums">
                          Without AI tools:{" "}
                          {item.traditional_paise === 0
                            ? "not needed"
                            : formatApprox(
                                item.traditional_paise,
                                summary.currency,
                              )}
                        </span>
                      ) : null}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
          <p className="text-sm text-muted-foreground">
            Each item&apos;s range is its share of the total range, so the items
            add up to it.
          </p>
        </div>
      }
    </section>
  );
}

/** "about 10 – 15 person-days" (or "about 12 person-days" when the ends meet). */
function workRange(item: QuickSummary["cost_items"][number]): string {
  const round = (n: number) =>
    n >= 20 ? Math.round(n / 5) * 5 : Math.round(n);
  const low = round(item.person_days_low ?? item.person_days ?? 0);
  const high = round(item.person_days_high ?? item.person_days ?? 0);
  const fmt = (n: number) => n.toLocaleString("en-IN");
  return low === high
    ? `about ${fmt(low)} person-days`
    : `about ${fmt(low)} – ${fmt(high)} person-days`;
}

const CLIENT_TYPES: Record<string, string> = {
  government: "Government / PSU",
  private: "Private company",
  small_business: "Startup / small business",
};

/** Client mode: where vendors' quotes stop looking realistic. */
function BidCheckCard({ summary }: { summary: QuickSummary }) {
  const check = summary.bid_check;
  if (!check) return null;
  const approx = (paise: number) => formatApprox(paise, summary.currency);
  return (
    <section className="sheet">
      <SectionTitle icon={ScalesIcon} tone="warning">
        Quote check
      </SectionTitle>
      {/* the fair range comes into focus first, then the two sides */}
      <ul className="focus-row grid gap-3 [--fd:1] sm:grid-cols-3">
        <li className="flex flex-col gap-1 rounded-xl bg-warning-muted px-4 py-3">
          <span className="text-sm font-medium text-warning">
            Probably too low
          </span>
          <span className="text-xl font-semibold tabular-nums">
            below {approx(check.too_low_below_paise).replace("about ", "")}
          </span>
        </li>
        <li className="flex flex-col gap-1 rounded-xl bg-success/10 px-4 py-3 [--fd:0]">
          <span className="text-sm font-medium text-success">Fair range</span>
          <span className="text-xl font-semibold tabular-nums">
            {formatRange(
              check.fair_low_paise,
              check.fair_high_paise,
              summary.currency,
            )}
          </span>
        </li>
        <li className="flex flex-col gap-1 rounded-xl bg-muted px-4 py-3">
          <span className="text-sm font-medium">Probably too high</span>
          <span className="text-xl font-semibold tabular-nums">
            above {approx(check.too_high_above_paise).replace("about ", "")}
          </span>
        </li>
      </ul>
      <p className="text-sm text-muted-foreground">{check.note}</p>
    </section>
  );
}

/** Real projects with published prices that are close to this one. */
function SimilarProjects({ summary }: { summary: QuickSummary }) {
  if (summary.similar_projects.length === 0) return null;
  return (
    <section className="flex flex-col gap-4">
      <div>
        <h3 className="text-base font-semibold">Similar real projects</h3>
        <p className="figure-label">Published prices, in today&apos;s money</p>
      </div>
      <ul className="flex flex-col divide-y">
        {summary.similar_projects.map((p) => (
          <li
            key={`${p.title}-${p.year}`}
            className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 py-3"
          >
            <span className="flex max-w-xl flex-col">
              <span className="font-medium">{p.title}</span>
              <span className="text-sm text-muted-foreground">
                {CLIENT_TYPES[p.client_type] ?? p.client_type}
                {p.size
                  ? ` · ${p.size.replace("_", " to ")} project`
                  : ""} · {p.year} · {p.match_percent}% match ·{" "}
                <a
                  href={p.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="underline hover:text-foreground"
                >
                  source
                </a>
              </span>
            </span>
            <span className="font-medium tabular-nums">
              {p.low_paise > 0
                ? formatRange(p.low_paise, p.high_paise, summary.currency)
                : `up to ${formatApprox(p.high_paise, summary.currency).replace("about ", "")}`}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** Save this estimate's answers as a starting point for future estimates. */
function SaveTemplate({ summary }: { summary: QuickSummary }) {
  const [message, setMessage] = React.useState<string | null>(null);
  async function save() {
    const name = window.prompt("Name for this template", summary.name);
    if (!name || name.trim() === "") return;
    try {
      await api.createTemplate(summary.project_id, name.trim());
      setMessage(
        `Saved as template "${name.trim()}". Find it under "Start a new estimate".`,
      );
    } catch (e) {
      setMessage(errorText(e));
    }
  }
  return (
    <div className="flex flex-col gap-1">
      <Button variant="outline" onClick={save}>
        Save as template
      </Button>
      {message ? (
        <span role="status" className="text-sm text-muted-foreground">
          {message}
        </span>
      ) : null}
    </div>
  );
}

function SummaryView({
  summary,
  onChange,
}: {
  summary: QuickSummary;
  onChange: (summary: QuickSummary) => void;
}) {
  const user = useCurrentUser();
  const options = usePricedOptions(summary.estimate_id);
  const hasTeam =
    (summary.hours?.rows.length ?? 0) > 0 || summary.team.length > 0;
  const hasMarket =
    Boolean(summary.market) || summary.similar_projects.length > 0;
  return (
    <SourcesProvider estimateId={summary.estimate_id}>
      <div className="flex flex-col gap-5">
        <AppHero overlap>
          <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-6">
            <div>
              <Link
                href="/projects"
                className="group inline-flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
              >
                <span
                  aria-hidden="true"
                  className="inline-block rotate-180 transition-transform group-hover:-translate-x-0.5"
                >
                  <Chevron />
                </span>
                Your estimates
              </Link>
              <h1 className="font-display mt-4 max-w-3xl text-[clamp(2.2rem,5vw,3.5rem)] leading-[1.02] text-balance">
                {summary.name}
              </h1>
              <p className="mt-3 text-sm text-muted-foreground">
                {formatDate(summary.created_at)}
                {summary.indicative
                  ? " · Based on market prices and typical effort, not your own costs: a guide."
                  : ""}
              </p>
            </div>
            <div className="flex flex-wrap items-start gap-3">
              <Downloads
                estimateId={summary.estimate_id}
                name={summary.name}
                blocked={exportBlocked(summary)}
              />
            </div>
          </div>
        </AppHero>

        {summary.feasible ? (
          <>
            <Headline summary={summary} />
            <IndependentCheckCard summary={summary} onChange={onChange} />
            <BidCheckCard summary={summary} />
            <CheckBeforeSending summary={summary} options={options} />
            <CostSummary summary={summary} />
            <SourcesList />
            <CompareQuotes
              estimateId={summary.estimate_id}
              name={summary.name}
            />

            {summary.hardware ? (
              <Disclosure
                title="Hardware to buy"
                icon={HardDrivesIcon}
                hint={
                  summary.hardware.who_buys === "client_buys"
                    ? "Servers, network and licences the client buys"
                    : "Servers, network and licences for your own server room"
                }
              >
                <HardwareList summary={summary} />
              </Disclosure>
            ) : null}

            <Disclosure
              title="More details"
              icon={TreeStructureIcon}
              hint="Each feature, the team and hours, every cost item, and other choices compared"
            >
              <IncludedList summary={summary} />
              <FeatureCosts summary={summary} />
              <FeatureStoriesSection
                summary={summary}
                onChange={onChange}
                bare
              />
              {hasTeam ? (
                <section className="flex flex-col gap-4">
                  <TeamAndHours summary={summary} />
                </section>
              ) : null}
              <CostItems summary={summary} />
              {hasMarket ? (
                <section className="flex flex-col gap-4">
                  <MarketBox summary={summary} />
                  <SimilarProjects summary={summary} />
                </section>
              ) : null}
              <CompareOptions
                estimateId={summary.estimate_id}
                currency={summary.currency}
                country={summary.country}
              />
            </Disclosure>
          </>
        ) : (
          <section className="slab app-rise flex flex-col items-start gap-4 px-6 py-8 sm:px-10">
            <SectionTitle icon={TimerIcon} tone="warning">
              The deadline is too short to give a price
            </SectionTitle>
            <p className="max-w-2xl text-muted-foreground">{summary.message}</p>
            <Link
              href="/estimate/new"
              className={buttonVariants({ size: "lg" })}
            >
              Change the deadline
            </Link>
          </section>
        )}

        {user.is_owner ? (
          <BidResultCard
            projectId={summary.project_id}
            currency={summary.currency}
          />
        ) : null}

        <div className="flex flex-wrap items-center gap-x-6 gap-y-3 pt-6">
          <Link href="/estimate/new" className={buttonVariants({ size: "lg" })}>
            Start another estimate
          </Link>
          <SaveTemplate summary={summary} />
          <Link
            href={`/projects/${summary.project_id}?tab=estimate`}
            className="text-sm text-muted-foreground underline hover:text-foreground"
          >
            Expert view
          </Link>
        </div>
      </div>
    </SourcesProvider>
  );
}

export function EstimateResult() {
  const params = useParams<{ id: string }>();
  const estimateId = params.id;
  const loader = React.useCallback(
    () => api.getEstimateSummary(estimateId),
    [estimateId],
  );
  const { state, setData } = useLoad(loader);
  if (state.kind === "loading")
    return <Loading fullPage>Loading your estimate…</Loading>;
  if (state.kind === "error") return <ErrorNotice message={state.message} />;
  return <SummaryView summary={state.data} onChange={setData} />;
}
