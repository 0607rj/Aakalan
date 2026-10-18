"use client";

import * as React from "react";

import { ErrorNotice, Loading } from "@/components/status";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  api,
  errorText,
  type BidResult,
  type Outcome,
  type OutcomeIn,
} from "@/lib/api/client";
import { currencySymbol, formatPaise } from "@/lib/format";
import { useLoad } from "@/lib/use-load";
import { cn } from "@/lib/utils";

const MINOR_PER_MAJOR = 100; // paise per rupee, cents per dollar

const RESULTS: { value: BidResult; label: string }[] = [
  { value: "won", label: "Won" },
  { value: "lost", label: "Lost" },
  { value: "withdrawn", label: "Withdrawn" },
  { value: "not_bid", label: "Did not bid" },
];

type PriceKey = "our_price_paise" | "l1_price_paise" | "actual_cost_paise";

const PRICES: { key: PriceKey; label: (symbol: string) => string }[] = [
  { key: "our_price_paise", label: (c) => `Our quoted price (${c})` },
  { key: "l1_price_paise", label: (c) => `Winning (L1) price (${c})` },
  {
    key: "actual_cost_paise",
    label: (c) => `Actual final cost (${c}, if won and finished)`,
  },
];

function amountText(minor: number | null | undefined): string {
  return minor === null || minor === undefined
    ? ""
    : String(minor / MINOR_PER_MAJOR);
}

function priceError(text: string): string | null {
  if (text.trim() === "") return null;
  const n = Number(text);
  if (!Number.isFinite(n) || n < 0) return "Enter an amount.";
  return null;
}

function resultLabel(value: BidResult): string {
  return RESULTS.find((r) => r.value === value)?.label ?? value;
}

function SavedOutcome({
  outcome,
  currency,
  onEdit,
}: {
  outcome: Outcome;
  currency: string;
  onEdit: () => void;
}) {
  const parts = [
    resultLabel(outcome.bid_result),
    outcome.l1_price_paise != null
      ? `Winning price ${formatPaise(outcome.l1_price_paise, currency)}`
      : null,
    outcome.our_price_paise != null
      ? `Our price ${formatPaise(outcome.our_price_paise, currency)}`
      : null,
    outcome.actual_cost_paise != null
      ? `Actual cost ${formatPaise(outcome.actual_cost_paise, currency)}`
      : null,
  ].filter(Boolean);
  return (
    <div className="flex flex-col gap-2">
      <p className="font-medium">{parts.join(" · ")}</p>
      {outcome.notes ? (
        <p className="text-sm text-muted-foreground">{outcome.notes}</p>
      ) : null}
      <button
        type="button"
        onClick={onEdit}
        className="self-start text-sm text-primary underline hover:text-primary/80"
      >
        Edit
      </button>
    </div>
  );
}

function OutcomeForm({
  projectId,
  currency,
  initial,
  onSaved,
  onCancel,
}: {
  projectId: string;
  currency: string;
  initial: Outcome | null;
  onSaved: (outcome: Outcome) => void;
  onCancel: () => void;
}) {
  const [result, setResult] = React.useState<BidResult>(
    initial?.bid_result ?? "lost",
  );
  const [prices, setPrices] = React.useState<Record<PriceKey, string>>({
    our_price_paise: amountText(initial?.our_price_paise),
    l1_price_paise: amountText(initial?.l1_price_paise),
    actual_cost_paise: amountText(initial?.actual_cost_paise),
  });
  const [notes, setNotes] = React.useState(initial?.notes ?? "");
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const errors = Object.fromEntries(
    PRICES.map((p) => [p.key, priceError(prices[p.key])]),
  );
  const hasErrors = Object.values(errors).some(Boolean);

  async function save() {
    setSaving(true);
    setError(null);
    const body: OutcomeIn = { bid_result: result, notes: notes.trim() };
    for (const p of PRICES) {
      const text = prices[p.key].trim();
      if (text !== "") body[p.key] = Math.round(Number(text) * MINOR_PER_MAJOR);
    }
    try {
      onSaved(await api.recordOutcome(projectId, body));
    } catch (e) {
      setError(errorText(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 font-semibold">Result</legend>
        <div className="flex flex-wrap gap-3">
          {RESULTS.map((r) => (
            <label
              key={r.value}
              className={cn(
                "flex cursor-pointer items-center gap-2 rounded-lg border px-4 py-2",
                result === r.value
                  ? "border-primary bg-primary/5 ring-1 ring-primary"
                  : "hover:bg-muted/40",
              )}
            >
              <input
                type="radio"
                name="bid-result"
                checked={result === r.value}
                onChange={() => setResult(r.value)}
                className="size-4 accent-primary"
              />
              {r.label}
            </label>
          ))}
        </div>
      </fieldset>
      <div className="grid gap-4 sm:grid-cols-3">
        {PRICES.map((p) => (
          <div key={p.key} className="flex flex-col gap-2">
            <Label htmlFor={`outcome-${p.key}`}>
              {p.label(currencySymbol(currency))}
            </Label>
            <Input
              id={`outcome-${p.key}`}
              type="number"
              inputMode="decimal"
              min={0}
              value={prices[p.key]}
              onChange={(e) =>
                setPrices((current) => ({
                  ...current,
                  [p.key]: e.target.value,
                }))
              }
            />
            {errors[p.key] ? (
              <span className="text-sm text-destructive">{errors[p.key]}</span>
            ) : null}
          </div>
        ))}
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="outcome-notes">Notes</Label>
        <Input
          id="outcome-notes"
          value={notes}
          maxLength={2000}
          placeholder="e.g. L1 was a local firm; scope was reduced"
          onChange={(e) => setNotes(e.target.value)}
        />
      </div>
      <ErrorNotice message={error} />
      <div className="flex flex-wrap gap-3">
        <Button disabled={saving || hasErrors} onClick={save}>
          {saving ? "Saving…" : "Save result"}
        </Button>
        <Button variant="outline" disabled={saving} onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </div>
  );
}

export function BidResultCard({
  projectId,
  currency = "INR",
}: {
  projectId: string;
  currency?: string;
}) {
  const loader = React.useCallback(
    () => api.getOutcome(projectId),
    [projectId],
  );
  const { state, setData } = useLoad(loader);
  const [editing, setEditing] = React.useState(false);

  return (
    <section className="flex flex-col gap-4 rounded-2xl border bg-card px-6 py-6 shadow-sm sm:px-8">
      <div>
        <h2 className="text-lg font-semibold">Bid result</h2>
        <p className="text-sm text-muted-foreground">
          Recording results teaches the tool to estimate closer to real prices.
        </p>
      </div>
      {state.kind === "loading" ? <Loading /> : null}
      {state.kind === "error" ? <ErrorNotice message={state.message} /> : null}
      {state.kind === "ready" ? (
        editing ? (
          <OutcomeForm
            projectId={projectId}
            currency={currency}
            initial={state.data}
            onSaved={(outcome) => {
              setData(outcome);
              setEditing(false);
            }}
            onCancel={() => setEditing(false)}
          />
        ) : state.data ? (
          <SavedOutcome
            outcome={state.data}
            currency={currency}
            onEdit={() => setEditing(true)}
          />
        ) : (
          <Button
            variant="outline"
            className="self-start"
            onClick={() => setEditing(true)}
          >
            Record the bid result
          </Button>
        )
      ) : null}
    </section>
  );
}
