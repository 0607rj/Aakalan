"use client";

import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { ErrorNotice, Loading } from "@/components/status";
import { Button } from "@/components/ui/button";
import { api, errorText, type QuickSummary } from "@/lib/api/client";
import {
  formatApprox,
  formatPaise,
  formatDate,
  formatDecimal,
  formatRange,
} from "@/lib/format";
import { useLoad } from "@/lib/use-load";

import { BidResultCard } from "./bid-result";
import { CompareOptions } from "./compare";
import { Downloads } from "./downloads";

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-lg font-semibold">{value}</span>
    </div>
  );
}

function Headline({ summary }: { summary: QuickSummary }) {
  const years = summary.support_years;
  const range = (low: number | null, high: number | null) =>
    formatRange(low, high, summary.currency);
  const approx = (paise: number | null) =>
    formatApprox(paise, summary.currency);
  return (
    <section className="flex flex-col gap-6 rounded-2xl border bg-card px-6 py-8 shadow-sm sm:px-10">
      <div className="flex flex-col gap-1">
        <span className="text-base text-muted-foreground">
          {summary.mode === "client"
            ? "Fair budget range"
            : "Estimated total price"}
        </span>
        <span className="text-4xl font-semibold tracking-tight text-primary sm:text-5xl">
          {range(summary.low_paise, summary.high_paise)}
        </span>
        <span className="text-base text-muted-foreground">
          Most likely {approx(summary.likely_paise)}. This is an estimate before
          the work starts, not a final bill.
        </span>
      </div>

      <div className="grid gap-3 border-t pt-5 sm:grid-cols-2">
        <div className="flex flex-col gap-1 rounded-xl border-2 border-primary/30 bg-primary/5 px-5 py-4">
          <span className="text-sm font-medium">
            Cost to build the software
          </span>
          <span className="text-2xl font-semibold tracking-tight tabular-nums">
            {range(summary.build_only_low_paise, summary.build_only_high_paise)}
          </span>
          <span className="text-sm text-muted-foreground">
            Most likely {approx(summary.build_only_paise)}. Before support,
            margin and tax.
          </span>
        </div>
        <div className="flex flex-col gap-1 rounded-xl border px-5 py-4">
          <span className="text-sm font-medium">
            {summary.mode === "client"
              ? "Estimated cost to budget"
              : "Full price you would quote"}
          </span>
          <span className="text-2xl font-semibold tracking-tight tabular-nums">
            {range(summary.low_paise, summary.high_paise)}
          </span>
          <span className="text-sm text-muted-foreground">
            {years > 0
              ? `${years} year${years === 1 ? "" : "s"} of support, margin and tax included`
              : "Build and launch only (no support after launch), margin and tax included"}
          </span>
        </div>
      </div>

      <div className="flex flex-wrap gap-x-10 gap-y-4">
        <Fact
          label="Time to build"
          value={`about ${formatDecimal(summary.build_months, 1)} months`}
        />
        {summary.project_size ? (
          <Fact
            label="Project size"
            value={
              summary.size_points
                ? `${summary.project_size} (${summary.size_points} feature points)`
                : summary.project_size
            }
          />
        ) : null}
        <Fact
          label="Support included"
          value={
            years > 0
              ? `${years} year${years === 1 ? "" : "s"} after launch`
              : "None (handed over after launch)"
          }
        />
      </div>
      {summary.client_pays.length > 0 ? (
        <p className="rounded-xl bg-muted/60 px-4 py-3 text-sm">
          <strong>Not included:</strong>{" "}
          {summary.client_pays_first_year_paise > 0
            ? `${approx(summary.client_pays_first_year_paise)} in the first year that the client pays directly`
            : "fees the client pays directly"}{" "}
          ({summary.client_pays.map((c) => c.label.toLowerCase()).join(", ")}).
          See &quot;Paid directly by the client&quot; below.
        </p>
      ) : null}
    </section>
  );
}

function AiComparison({ summary }: { summary: QuickSummary }) {
  const traditional = summary.traditional_paise;
  const likely = summary.likely_paise;
  if (traditional === null || likely === null) return null;
  const money = (paise: number | null) => formatApprox(paise, summary.currency);
  const saving = traditional - likely;
  return (
    <section className="flex flex-col gap-5 rounded-2xl border bg-card px-6 py-6 shadow-sm sm:px-8">
      <h2 className="text-lg font-semibold">With AI vs the traditional way</h2>
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="flex flex-col gap-1 rounded-xl border px-5 py-4">
          <span className="text-sm font-medium text-muted-foreground">
            Traditional price (team without AI tools)
          </span>
          <span className="text-2xl font-semibold tracking-tight text-muted-foreground tabular-nums">
            {money(traditional)}
          </span>
          <span className="text-sm text-muted-foreground">
            Build only: {money(summary.traditional_build_only_paise)}
          </span>
        </div>
        <div className="flex flex-col gap-1 rounded-xl border-2 border-primary/30 bg-primary/5 px-5 py-4">
          <span className="text-sm font-medium">
            AI-era price (this estimate)
          </span>
          <span className="text-2xl font-semibold tracking-tight text-primary tabular-nums">
            {money(likely)}
          </span>
          <span className="text-sm text-muted-foreground">
            Build only: {money(summary.build_only_paise)}
          </span>
        </div>
      </div>
      {summary.ai_saving_percent !== null && saving > 0 ? (
        <p className="rounded-xl bg-success/10 px-4 py-3 font-medium text-success">
          AI tools cut this project&apos;s cost by about{" "}
          {summary.ai_saving_percent}% ({money(saving)})
        </p>
      ) : null}
      <p className="text-sm text-muted-foreground">
        The traditional price is what this scope would cost if the team wrote
        everything by hand, as most vendors priced work before AI tools. It
        shows how much a fair AI-era quote should come down.
      </p>
    </section>
  );
}

/** 1234 -> "1,234". */
function hoursText(hours: number): string {
  return Math.round(hours).toLocaleString("en-IN");
}

/** The build in hours: the same work without AI tools, with them, and what AI saved. */
function HoursOfWork({ summary }: { summary: QuickSummary }) {
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
    <section className="flex flex-col gap-5 rounded-2xl border bg-card px-6 py-6 shadow-sm sm:px-8">
      <div>
        <h2 className="text-lg font-semibold">Hours of work</h2>
        <p className="text-sm text-muted-foreground">
          The team&apos;s work to build and launch it, counted in hours (
          {h.hours_per_day} hours a working day), priced at each role&apos;s
          rate.
        </p>
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        {hasOld ? (
          <div className="flex flex-col gap-1 rounded-xl border px-4 py-3">
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
        <div className="flex flex-col gap-1 rounded-xl border-2 border-primary/30 bg-primary/5 px-4 py-3">
          <span className="text-sm font-medium">With AI tools</span>
          <span className="text-2xl font-semibold tabular-nums">
            {hoursText(h.with_ai)} h
          </span>
          <span className="text-sm text-muted-foreground">
            {money(h.team_cost_paise)}
          </span>
        </div>
        {hasOld && (h.saved ?? 0) > 0 ? (
          <div className="flex flex-col gap-1 rounded-xl bg-ai-soft px-4 py-3 text-ai">
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
      <div className="overflow-x-auto">
        <table className="w-full min-w-[34rem] text-sm">
          <thead>
            <tr className="border-b text-left text-muted-foreground">
              <th className="py-2 pr-4 font-medium">Role</th>
              {hasOld ? (
                <th className="py-2 pr-4 text-right font-medium">Without AI</th>
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
      <p className="text-sm text-muted-foreground">
        Hours are an estimate like the price: the real number depends on how
        deep each feature turns out to be. Servers, support after launch,
        services paid to others and tax are added separately below. Set your own
        rates in Settings.
      </p>
    </section>
  );
}

/** "about 3 people" / "part-time" from an average number of full-time people. */
function peopleText(people: number): string {
  if (people < 0.5) return "part-time";
  const n = Math.round(people);
  return `about ${n} ${n === 1 ? "person" : "people"}`;
}

/** Who is needed to build it: people by role over the build, with and without AI tools. */
function TeamNeeded({ summary }: { summary: QuickSummary }) {
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
    <section className="flex flex-col gap-4 rounded-2xl border bg-card px-6 py-6 shadow-sm sm:px-8">
      <div>
        <h2 className="text-lg font-semibold">Team needed to build it</h2>
        <p className="text-sm text-muted-foreground">
          About {Math.max(1, Math.round(total))} people working for{" "}
          {formatDecimal(months, 1)} months on average. Some roles are needed
          only part of the time.
          {hasOld && summary.traditional_build_months
            ? ` Without AI tools: about ${Math.max(1, Math.round(oldTotal))} people for ${formatDecimal(Number(summary.traditional_build_months), 1)} months.`
            : ""}
        </p>
      </div>
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
      {summary.support_team.length > 0 && summary.support_years > 0 ? (
        <p className="text-sm text-muted-foreground">
          <strong className="text-foreground">After launch</strong> (each year):{" "}
          {summary.support_team
            .map((r) => `${r.label} — ${peopleText(Number(r.people))}`)
            .join("; ")}
          .
        </p>
      ) : null}
      <p className="text-sm text-muted-foreground">
        One person-month is one person working full time for a month. A tight
        deadline needs more people at once.
      </p>
    </section>
  );
}

/** Building cost of each feature, with the team's AI tools and the traditional way. */
function FeatureCosts({ summary }: { summary: QuickSummary }) {
  if (summary.feature_costs.length === 0) return null;
  const money = (paise: number | null) => formatApprox(paise, summary.currency);
  const withAi = summary.feature_costs.reduce((s, f) => s + f.amount_paise, 0);
  const withoutAi = summary.feature_costs.every(
    (f) => f.traditional_paise !== null,
  )
    ? summary.feature_costs.reduce((s, f) => s + (f.traditional_paise ?? 0), 0)
    : null;
  return (
    <section className="flex flex-col gap-4 rounded-2xl border bg-card px-6 py-6 shadow-sm sm:px-8">
      <div>
        <h2 className="text-lg font-semibold">Building cost of each feature</h2>
        <p className="text-sm text-muted-foreground">
          The team&apos;s work on each feature (most likely). Launch, running,
          management, margin and tax are listed further down.
        </p>
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
                <td className="py-2 pr-4">{f.label}</td>
                <td className="py-2 pr-4 text-muted-foreground">
                  {f.level ?? "—"}
                </td>
                {withoutAi !== null ? (
                  <td className="py-2 pr-4 text-right text-muted-foreground tabular-nums">
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
      <p className="text-sm text-muted-foreground">
        With AI tools the team writes code, tests and documents faster; the
        price already includes the extra time people spend checking what the AI
        wrote.
      </p>
    </section>
  );
}

function MoneyBreakdown({ summary }: { summary: QuickSummary }) {
  const risk = summary.risk_allowance_paise;
  const money = (paise: number | null) => formatApprox(paise, summary.currency);
  return (
    <section className="flex flex-col gap-5 rounded-2xl border bg-card px-6 py-6 shadow-sm sm:px-8">
      <h2 className="text-lg font-semibold">Where the money goes</h2>
      <ul className="flex flex-col gap-4">
        {summary.parts.map((part) => (
          <li key={part.key} className="flex flex-col gap-1.5">
            <div className="flex flex-wrap items-baseline justify-between gap-x-4">
              <span className="font-medium">{part.label}</span>
              <span className="tabular-nums">
                <span className="font-semibold">
                  {formatRange(
                    part.low_paise,
                    part.high_paise,
                    summary.currency,
                  )}
                </span>{" "}
                <span className="text-sm text-muted-foreground">
                  ({part.share_percent}%)
                </span>
              </span>
            </div>
            <div className="h-3 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary"
                style={{ width: `${Math.max(0, part.share_percent)}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
      {risk !== null && risk > 0 ? (
        <p className="border-t pt-4 text-sm text-muted-foreground">
          Planned cost{" "}
          <strong className="text-foreground">
            {money(summary.planned_paise)}
          </strong>{" "}
          + allowance for risks{" "}
          <strong className="text-foreground">{money(risk)}</strong> = most
          likely{" "}
          <strong className="text-foreground">
            {money(summary.likely_paise)}
          </strong>
        </p>
      ) : null}
    </section>
  );
}

function CostItems({ summary }: { summary: QuickSummary }) {
  const [open, setOpen] = React.useState(false);
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
    <section className="flex flex-col gap-4 rounded-2xl border bg-card px-6 py-6 shadow-sm sm:px-8">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h2 className="text-lg font-semibold">
            What&apos;s inside the price
          </h2>
          <p className="text-sm text-muted-foreground">
            Every cost item: people&apos;s time, AI tools, licences, servers,
            services, margin and tax — and what each would cost if the team used
            no AI tools.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="text-sm font-medium text-primary hover:underline"
        >
          {open ? "Hide items" : `Show all ${summary.cost_items.length} items`}
        </button>
      </div>
      {open ? (
        <div className="flex flex-col gap-5">
          {groups.map((group) => (
            <div key={group.label} className="flex flex-col">
              <h3 className="border-b pb-1 text-sm font-semibold text-muted-foreground">
                {group.label} ·{" "}
                {range(
                  group.items.reduce((s, i) => s + i.low_paise, 0),
                  group.items.reduce((s, i) => s + i.high_paise, 0),
                )}
              </h3>
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
            Each item shows its own range. The total range is narrower than
            adding up every low or every high figure, because not everything
            turns out cheap or expensive at the same time.
          </p>
        </div>
      ) : null}
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

function ClientPays({ summary }: { summary: QuickSummary }) {
  if (summary.client_pays.length === 0) return null;
  const range = (low?: number | null, high?: number | null) =>
    formatRange(low, high, summary.currency);
  const years = summary.support_years;
  return (
    <section className="flex flex-col gap-4 rounded-2xl border bg-card px-6 py-6 shadow-sm sm:px-8">
      <div>
        <h2 className="text-lg font-semibold">
          {summary.mode === "client"
            ? "Also budget for (paid to other providers)"
            : "Paid directly by the client"}
        </h2>
        <p className="text-sm text-muted-foreground">
          Not in the price above. The client pays these to the providers
          themselves, so tell them to budget for it.
        </p>
      </div>
      <ul className="flex flex-col divide-y">
        {summary.client_pays.map((item) => (
          <li
            key={item.key}
            className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 py-3"
          >
            <div className="flex flex-col">
              <span className="font-medium">{item.label}</span>
              {item.note ? (
                <span className="text-sm text-muted-foreground">
                  {item.note}
                </span>
              ) : null}
            </div>
            {item.first_year_paise !== null ? (
              <span className="text-right tabular-nums">
                <span className="font-semibold">
                  {range(item.first_year_low_paise, item.first_year_high_paise)}
                </span>
                <span className="text-sm text-muted-foreground">
                  {" "}
                  first year
                </span>
                {item.total_paise !== null &&
                item.total_paise !== item.first_year_paise ? (
                  <span className="block text-sm text-muted-foreground">
                    {range(item.total_low_paise, item.total_high_paise)} over{" "}
                    {years} year
                    {years === 1 ? "" : "s"}
                  </span>
                ) : null}
              </span>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}

const CLIENT_TYPES: Record<string, string> = {
  government: "Government / PSU",
  private: "Private company",
  small_business: "Startup / small business",
};

/** Client mode: where bids stop looking realistic. */
function BidCheckCard({ summary }: { summary: QuickSummary }) {
  const check = summary.bid_check;
  if (!check) return null;
  const approx = (paise: number) => formatApprox(paise, summary.currency);
  return (
    <section className="flex flex-col gap-4 rounded-2xl border-2 border-primary/30 bg-card px-6 py-6 shadow-sm sm:px-8">
      <h2 className="text-lg font-semibold">Bid check</h2>
      <ul className="grid gap-3 sm:grid-cols-3">
        <li className="flex flex-col gap-1 rounded-xl bg-warning-muted px-4 py-3">
          <span className="text-sm font-medium text-warning">
            Probably too low
          </span>
          <span className="text-xl font-semibold tabular-nums">
            below {approx(check.too_low_below_paise).replace("about ", "")}
          </span>
        </li>
        <li className="flex flex-col gap-1 rounded-xl bg-success/10 px-4 py-3">
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
    <section className="flex flex-col gap-4 rounded-2xl border bg-card px-6 py-6 shadow-sm sm:px-8">
      <div>
        <h2 className="text-lg font-semibold">Similar real projects</h2>
        <p className="text-sm text-muted-foreground">
          What clients actually paid for comparable work (published prices, in
          today&apos;s money). Use them to sanity-check this estimate.
        </p>
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

function SummaryView({ summary }: { summary: QuickSummary }) {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <Link
          href="/projects"
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          ← Your estimates
        </Link>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">
          {summary.name}
        </h1>
        <p className="text-sm text-muted-foreground">
          Estimated on {formatDate(summary.created_at)}
        </p>
      </div>

      <div className="flex flex-wrap items-start gap-3">
        <Downloads estimateId={summary.estimate_id} name={summary.name} />
        <SaveTemplate summary={summary} />
      </div>

      {summary.indicative ? (
        <p className="rounded-xl border border-warning/30 bg-warning-muted px-4 py-3 text-sm text-warning">
          These figures use public market prices and typical effort, not your
          company’s own costs, so treat them as a guide.
        </p>
      ) : null}

      {summary.accuracy_note ? (
        <section className="rounded-xl border bg-muted/40 px-4 py-3 text-sm">
          <h2 className="font-medium">How accurate is this?</h2>
          <p className="mt-0.5 text-muted-foreground">
            {summary.accuracy_note}
          </p>
        </section>
      ) : null}

      {summary.feasible ? (
        <>
          <Headline summary={summary} />
          {summary.not_sure.length > 0 ? (
            <section className="rounded-xl border border-warning/30 bg-warning-muted px-4 py-3 text-sm text-warning">
              <h2 className="font-medium">
                The range is wider because you were not sure about:
              </h2>
              <ul className="mt-1 list-disc pl-5">
                {summary.not_sure.map((q) => (
                  <li key={q}>{q}</li>
                ))}
              </ul>
              <p className="mt-1">
                Find out these answers and calculate again to get a narrower
                range.
              </p>
            </section>
          ) : null}
          <HoursOfWork summary={summary} />
          <TeamNeeded summary={summary} />
          <BidCheckCard summary={summary} />
          <AiComparison summary={summary} />
          <FeatureCosts summary={summary} />
          <MoneyBreakdown summary={summary} />
          <CostItems summary={summary} />
          <ClientPays summary={summary} />
          <SimilarProjects summary={summary} />
          <CompareOptions
            estimateId={summary.estimate_id}
            currency={summary.currency}
            country={summary.country}
          />
          {summary.biggest_uncertainty ? (
            <section className="rounded-2xl border border-primary/20 bg-primary/5 px-6 py-5">
              <h2 className="font-semibold">What could change the price</h2>
              <p className="mt-1 text-muted-foreground">
                {summary.biggest_uncertainty}
              </p>
            </section>
          ) : null}
        </>
      ) : (
        <section className="flex flex-col items-start gap-4 rounded-2xl border bg-card px-6 py-8 shadow-sm sm:px-10">
          <h2 className="text-xl font-semibold">
            The deadline is too short to give a price
          </h2>
          <p className="max-w-2xl text-muted-foreground">{summary.message}</p>
          <Link
            href="/estimate/new"
            className="inline-flex h-11 items-center rounded-lg bg-primary px-5 font-medium text-primary-foreground hover:bg-primary/90"
          >
            Change the deadline
          </Link>
        </section>
      )}

      <BidResultCard
        projectId={summary.project_id}
        currency={summary.currency}
      />

      <section className="rounded-2xl border bg-card px-6 py-6 shadow-sm sm:px-8">
        <h2 className="text-lg font-semibold">What you asked for</h2>
        <ul className="mt-3 grid gap-2 sm:grid-cols-2">
          {summary.features.map((feature) => (
            <li key={feature} className="flex items-start gap-2">
              <span className="text-primary">✓</span>
              <span>{feature}</span>
            </li>
          ))}
        </ul>
      </section>

      <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
        <Link
          href="/estimate/new"
          className="inline-flex h-11 items-center rounded-lg bg-primary px-5 font-medium text-primary-foreground hover:bg-primary/90"
        >
          Start another estimate
        </Link>
        <Link
          href={`/projects/${summary.project_id}?tab=estimate`}
          className="text-sm text-muted-foreground underline hover:text-foreground"
        >
          See detailed breakdown (for experts)
        </Link>
      </div>
    </div>
  );
}

export function EstimateResult() {
  const params = useParams<{ id: string }>();
  const estimateId = params.id;
  const loader = React.useCallback(
    () => api.getEstimateSummary(estimateId),
    [estimateId],
  );
  const { state } = useLoad(loader);
  if (state.kind === "loading")
    return <Loading>Loading your estimate…</Loading>;
  if (state.kind === "error") return <ErrorNotice message={state.message} />;
  return <SummaryView summary={state.data} />;
}
