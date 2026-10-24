"use client";

import * as React from "react";

import { ErrorNotice } from "@/components/status";
import { Button } from "@/components/ui/button";
import {
  api,
  errorText,
  type PricedOption,
  type QuickSummary,
} from "@/lib/api/client";
import {
  formatApprox,
  formatDate,
  formatDecimal,
  formatPaise,
} from "@/lib/format";
import { useLoad } from "@/lib/use-load";
import { cn } from "@/lib/utils";

import { Disclosure } from "./cost-summary";

/** True while the independent check asks for a look before the report can be exported. */
export function exportBlocked(summary: QuickSummary): boolean {
  const check = summary.independent_check;
  return Boolean(check?.needs_confirmation && !check.confirmed_at);
}

function Months({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-xl font-semibold tabular-nums">{value}</span>
    </div>
  );
}

/**
 * A second build estimate counted from what the document says the system contains, next to
 * the priced build. Far apart: export waits until someone confirms they checked the gap.
 * It never changes or hides the price.
 */
export function IndependentCheckCard({
  summary,
  onChange,
}: {
  summary: QuickSummary;
  onChange: (summary: QuickSummary) => void;
}) {
  const check = summary.independent_check;
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  if (!check?.available) return null;
  const warn = check.needs_confirmation && !check.confirmed_at;

  async function confirm() {
    setBusy(true);
    setError(null);
    try {
      onChange(await api.confirmCheck(summary.estimate_id));
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      className={cn("sheet", warn && "slab border-warning/50 px-6 pb-6")}
    >
      <div>
        <h2 className="text-xl font-semibold">Independent check</h2>
        <p className="text-sm text-muted-foreground">{check.note}</p>
      </div>
      <div className="flex flex-wrap gap-x-10 gap-y-3">
        <Months
          label="Priced build"
          value={`${formatDecimal(check.priced_months, 1)} person-months`}
        />
        <Months
          label="Counted from the document"
          value={`${formatDecimal(check.anchor_months, 1)} person-months`}
        />
        {check.band ? (
          <Months
            label={`Typical ${check.band.system_class.toLowerCase()} (${check.band.size})`}
            value={`${formatDecimal(check.band.low_months, 0)}–${formatDecimal(check.band.high_months, 0)} person-months`}
          />
        ) : null}
      </div>
      <p className={cn("text-sm", check.flagged && "font-medium")}>
        {check.message}
      </p>
      {check.emd_message ? (
        <p className="text-sm font-medium">{check.emd_message}</p>
      ) : null}
      {check.flagged && check.top_lines.length > 0 ? (
        <div className="text-sm">
          <span className="font-medium">Largest priced lines: </span>
          {check.top_lines
            .map(
              (l) =>
                `${l.label} (${formatPaise(l.amount_paise, summary.currency)})`,
            )
            .join(", ")}
        </div>
      ) : null}
      <details className="text-sm">
        <summary className="w-fit cursor-pointer list-none font-medium text-muted-foreground hover:text-foreground [&::-webkit-details-marker]:hidden">
          What was counted
        </summary>
        <ul className="mt-2 flex flex-col gap-1.5">
          {check.counts.map((c) => (
            <li key={c.key}>
              <span className="font-medium">
                {c.label}: {formatDecimal(c.count, 1)} ×{" "}
                {formatDecimal(c.pd_each, 1)} ={" "}
                {formatDecimal(c.person_days, 1)} person-days
              </span>
              {c.items.length > 0 ? (
                <span className="text-muted-foreground">
                  {" "}
                  ({c.items.join(", ")})
                </span>
              ) : null}
            </li>
          ))}
          {check.factors.map((f) => (
            <li key={f.label}>
              {f.label}: × {formatDecimal(f.value, 2)}
            </li>
          ))}
          {check.integrations_not_selected.length > 0 ? (
            <li className="text-muted-foreground">
              Not counted, provider not chosen yet:{" "}
              {check.integrations_not_selected.join(", ")}
            </li>
          ) : null}
        </ul>
      </details>
      {check.needs_confirmation ? (
        check.confirmed_at ? (
          <p className="text-sm text-muted-foreground">
            Gap checked on {formatDate(check.confirmed_at)}.
          </p>
        ) : (
          <div className="flex flex-wrap items-center gap-3 border-t pt-4">
            <p className="text-sm">
              Downloads open once someone checks this gap.
            </p>
            <Button size="sm" onClick={confirm} disabled={busy}>
              {busy ? "Saving…" : "I have checked the gap"}
            </Button>
          </div>
        )
      ) : null}
      <ErrorNotice message={error} />
    </section>
  );
}

/** "+₹ 16 L" / "−₹ 1 L": a rounded change to the most likely price. */
function signed(paise: number, currency: QuickSummary["currency"]): string {
  const amount = formatApprox(paise, currency).replace("about ", "");
  return paise > 0 ? `+${amount}` : amount;
}

export function changeRange(
  o: PricedOption,
  currency: QuickSummary["currency"],
) {
  const low = o.low_change_paise;
  const high = o.high_change_paise;
  if (low === null || high === null) return "";
  if (low === high) return signed(low, currency);
  return `${signed(low, currency)} to ${signed(high, currency)}`;
}

const NOT_INCLUDED_WHY: Record<
  QuickSummary["not_included"][number]["why"],
  string
> = {
  excluded_by_you: "marked not included",
  removed_by_you: "standard part left out on request",
  not_sure: "not decided yet, quoted separately",
  document_excluded: "the document rules it out",
  document_not_priced: "asked for in the document, not priced here",
};

/**
 * What the price rests on and leaves out: answers nobody gave (assumed, to change if wrong),
 * what is not included (with the "if required" price of what "Not sure" left out), and the
 * open answers with what each other answer would change. The PDF and Excel print the same.
 */
/** The open answers priced as options (loaded once for the page; empty until ready). */
export function usePricedOptions(estimateId: string): PricedOption[] {
  const loader = React.useCallback(
    () => api.getPricedOptions(estimateId),
    [estimateId],
  );
  const { state } = useLoad<PricedOption[]>(loader);
  return state.kind === "ready" ? state.data : [];
}

/** The open answer whose other answers move the price furthest past the range, if any
 * (options come largest swing first). */
export function biggestOpenAnswer(
  options: PricedOption[],
): PricedOption | undefined {
  return options.find((o) => o.beyond_range);
}

export function OpenAnswers({
  summary,
  options,
}: {
  summary: QuickSummary;
  options: PricedOption[];
}) {
  const open = options.filter((o) => o.why !== "left_out");
  const leftOut = new Map(
    options.filter((o) => o.why === "left_out").map((o) => [o.key, o]),
  );
  return (
    <>
      {summary.assumed.length > 0 ? (
        <Disclosure
          title="Assumed answers"
          hint={`${summary.assumed.length} answers nobody gave: check them`}
        >
          <ul className="flex flex-col gap-1.5 text-sm">
            {summary.assumed.map((a) => (
              <li key={a.key}>
                <span className="text-muted-foreground">{a.question}</span>{" "}
                <span className="font-medium">{a.answer}</span>
                {a.detail ? (
                  <span className="text-muted-foreground"> ({a.detail})</span>
                ) : null}
              </li>
            ))}
          </ul>
        </Disclosure>
      ) : null}
      {summary.not_included.length > 0 ? (
        <Disclosure
          title="Not included in this price"
          hint={`${summary.not_included.length} items`}
        >
          <ul className="flex flex-col gap-2 text-sm">
            {summary.not_included.map((item) => {
              const option = leftOut.get(item.question_key ?? "");
              return (
                <li key={item.label}>
                  <span className="font-medium">{item.label}</span>{" "}
                  <span className="text-muted-foreground">
                    ({NOT_INCLUDED_WHY[item.why]})
                  </span>
                  {option && option.low_change_paise !== null ? (
                    <span>
                      {" "}
                      If required: {changeRange(option, summary.currency)}
                      {option.usual_change_paise !== null &&
                      option.usual_change_paise !== undefined ? (
                        <span className="text-muted-foreground">
                          {" "}
                          ({signed(
                            option.usual_change_paise,
                            summary.currency,
                          )}{" "}
                          at the usual size)
                        </span>
                      ) : null}
                      .
                    </span>
                  ) : null}
                  {item.quote ? (
                    <span className="block text-muted-foreground">
                      “{item.quote}”
                    </span>
                  ) : null}
                </li>
              );
            })}
          </ul>
        </Disclosure>
      ) : null}
      {open.length > 0 ? (
        <Disclosure
          title="Open answers"
          hint={`${open.length} priced at the usual answer`}
        >
          <ul className="flex flex-col gap-2 text-sm">
            {open.map((o) => (
              <li key={o.key}>
                <span className="font-medium">{o.question}</span>{" "}
                <span className="text-muted-foreground">
                  ({o.why === "not_sure" ? "not sure" : "not in the document"}
                  ): priced as {o.priced_as}.
                </span>
                {o.options.length > 0 ? (
                  <span>
                    {" "}
                    Other answers {changeRange(o, summary.currency)}:{" "}
                    {o.options
                      .map((c) =>
                        c.change_paise === null
                          ? c.label
                          : `${c.label} ${signed(c.change_paise, summary.currency)}`,
                      )
                      .join("; ")}
                    .
                  </span>
                ) : null}
              </li>
            ))}
          </ul>
        </Disclosure>
      ) : null}
    </>
  );
}
