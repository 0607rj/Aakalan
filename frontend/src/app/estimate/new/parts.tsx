"use client";

import * as React from "react";

import {
  api,
  type Evidence,
  type QuestionImpact,
  type QuickQuestion,
  type QuickRequest,
} from "@/lib/api/client";
import { formatPaise } from "@/lib/format";
import { cn } from "@/lib/utils";

export type Choice = string | number;

export const MANUAL_STEPS = ["What to build", "A few questions", "Your cost"];
export const DOCUMENT_STEPS = ["Upload", "Check what we found", "Your cost"];

/**
 * Questions that only matter given other answers or the chosen features (from the options
 * API): e.g. helpdesk hours only with a helpdesk team, hosting and fees only with support
 * after launch, the chatbot question only when an AI feature is chosen.
 */
export function relevantQuestions<
  T extends {
    key: string;
    default: Choice;
    only_with_features?: string[];
    only_with_custom_types?: string[];
    hide_when?: Record<string, Choice[]>;
  },
>(
  questions: T[],
  choices: Record<string, Choice>,
  features: string[],
  customTypes: string[],
): T[] {
  const answer = (key: string) =>
    String(choices[key] ?? questions.find((q) => q.key === key)?.default);
  return questions.filter((q) => {
    const hidden = Object.entries(q.hide_when ?? {}).some(([key, values]) =>
      values.map(String).includes(answer(key)),
    );
    if (hidden) return false;
    const needFeatures = q.only_with_features ?? [];
    const needTypes = q.only_with_custom_types ?? [];
    if (needFeatures.length === 0 && needTypes.length === 0) return true;
    return (
      needFeatures.some((f) => features.includes(f)) ||
      needTypes.some((t) => customTypes.includes(t))
    );
  });
}

type DefaultBy = Record<string, Record<string, Choice>>;
type DependentQuestion = {
  key: string;
  default: Choice;
  default_by?: DefaultBy;
};

/** A question's default given the other answers (e.g. size "small" for a startup client). */
export function defaultFor(
  q: DependentQuestion,
  choices: Record<string, Choice>,
): Choice {
  for (const [other, byValue] of Object.entries(q.default_by ?? {})) {
    const value = byValue[String(choices[other])];
    if (value !== undefined) return value;
  }
  return q.default;
}

/**
 * Set one answer and refresh the defaults that follow it, except for questions the user (or
 * the document) has already answered (`fixed`).
 */
export function setChoice(
  questions: DependentQuestion[],
  choices: Record<string, Choice>,
  fixed: Set<string>,
  key: string,
  value: Choice,
): Record<string, Choice> {
  const next = { ...choices, [key]: value };
  for (const q of questions) {
    if (q.key !== key && !fixed.has(q.key) && q.default_by?.[key]) {
      next[q.key] = defaultFor(q, next);
    }
  }
  return next;
}

/** Starting answers: the given ones (fixed), then defaults that follow them. */
export function initialChoices(
  questions: DependentQuestion[],
  given: Record<string, Choice>,
): Record<string, Choice> {
  const base: Record<string, Choice> = Object.fromEntries(
    questions.map((q) => [q.key, given[q.key] ?? q.default]),
  );
  for (const q of questions) {
    if (given[q.key] === undefined) base[q.key] = defaultFor(q, base);
  }
  return base;
}

/** Currency of the country the options were loaded for ("INR" by default). */
export function optionsCurrency(options: {
  country: string;
  countries: { key: string; currency: string }[];
}): string {
  return (
    options.countries.find((c) => c.key === options.country)?.currency ?? "INR"
  );
}

export function StepIndicator({
  labels,
  current,
}: {
  labels: string[];
  current: number;
}) {
  return (
    <ol className="flex flex-wrap items-center gap-2 text-sm">
      {labels.map((label, i) => {
        const n = i + 1;
        const done = n < current;
        const active = n === current;
        return (
          <li key={label} className="flex items-center gap-2">
            <span
              className={cn(
                "flex size-7 items-center justify-center rounded-full border text-xs font-semibold",
                active && "border-primary bg-primary text-primary-foreground",
                done && "border-primary text-primary",
                !active && !done && "text-muted-foreground",
              )}
            >
              {done ? "✓" : n}
            </span>
            <span
              className={cn(
                active ? "font-medium" : "text-muted-foreground",
                "mr-2",
              )}
            >
              {label}
            </span>
            {n < labels.length ? (
              <span className="mr-2 hidden h-px w-8 bg-border sm:inline-block" />
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}

export function FeatureCard({
  label,
  hint,
  checked,
  onToggle,
  children,
}: {
  label: string;
  hint: string;
  checked: boolean;
  onToggle: () => void;
  /** Extra content under the card (e.g. where the document says so). */
  children?: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        "flex flex-col gap-2 rounded-xl border bg-card p-4 transition-colors",
        checked
          ? "border-primary bg-primary/5 ring-1 ring-primary"
          : "hover:border-primary/40 hover:bg-muted/40",
      )}
    >
      <label className="flex cursor-pointer items-start gap-3">
        <input
          type="checkbox"
          checked={checked}
          onChange={onToggle}
          className="mt-1 size-4 accent-primary"
        />
        <span className="flex flex-col gap-1">
          <span className="font-semibold">{label}</span>
          <span className="text-sm text-muted-foreground">{hint}</span>
        </span>
      </label>
      {children ? <div className="pl-7">{children}</div> : null}
    </div>
  );
}

const IMPACT_DEBOUNCE_MS = 600;

/**
 * Asks the engine which questions change the price most for the current form (nothing is
 * saved). Debounced; failures are ignored so the form keeps its default order.
 */
export function useQuestionImpact(
  body: QuickRequest | null,
): Map<string, QuestionImpact> {
  const [impacts, setImpacts] = React.useState<Map<string, QuestionImpact>>(
    () => new Map(),
  );
  const key = body ? JSON.stringify(body) : null;
  React.useEffect(() => {
    if (key === null) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      api
        .questionImpact(JSON.parse(key) as QuickRequest, controller.signal)
        .then((list) => setImpacts(new Map(list.map((q) => [q.key, q]))))
        .catch(() => {
          // Keep the previous (or default) order silently.
        });
    }, IMPACT_DEBOUNCE_MS);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [key]);
  return impacts;
}

/** A question as the heading of its own screen, with how much it can move the price. */
export function QuestionHeading({
  question,
  impact,
  currency = "INR",
}: {
  question: QuickQuestion;
  impact?: QuestionImpact;
  currency?: string;
}) {
  return (
    <div>
      <h1 className="text-2xl font-semibold tracking-tight text-balance sm:text-3xl">
        {question.label}
      </h1>
      <p className="mt-1 text-muted-foreground">
        {impact && impact.impact_paise > 0
          ? `This answer can change the price by about ${formatPaise(impact.impact_paise, currency)}.`
          : "We have picked the usual answer. Change it if it does not fit."}
      </p>
    </div>
  );
}

export function QuestionGroup({
  question,
  value,
  onChange,
  hideLegend = false,
  impact,
  currency = "INR",
}: {
  question: QuickQuestion;
  value: Choice;
  onChange: (value: Choice) => void;
  hideLegend?: boolean;
  /** Price per option from the engine, when known. */
  impact?: QuestionImpact;
  currency?: string;
}) {
  const prices = new Map(
    (impact?.options ?? []).map((o) => [String(o.value), o.likely_paise]),
  );
  return (
    <fieldset className="flex flex-col gap-3">
      <legend
        className={cn("mb-3 text-base font-semibold", hideLegend && "sr-only")}
      >
        {question.label}
        {impact && impact.impact_paise > 0 && !hideLegend ? (
          <span className="mt-0.5 block text-sm font-normal text-muted-foreground">
            Can change the price by about{" "}
            {formatPaise(impact.impact_paise, currency)}
          </span>
        ) : null}
      </legend>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {question.options.map((option) => {
          const selected = option.value === value;
          const price = prices.get(String(option.value));
          return (
            <label
              key={String(option.value)}
              className={cn(
                "flex cursor-pointer flex-col gap-1 rounded-xl border bg-card p-4 transition-colors",
                selected
                  ? "border-primary bg-primary/5 ring-1 ring-primary"
                  : "hover:border-primary/40 hover:bg-muted/40",
              )}
            >
              <span className="flex items-center gap-2">
                <input
                  type="radio"
                  name={question.key}
                  checked={selected}
                  onChange={() => onChange(option.value)}
                  className="size-4 accent-primary"
                />
                <span className="font-semibold">{option.label}</span>
              </span>
              {option.hint ? (
                <span className="pl-6 text-sm text-muted-foreground">
                  {option.hint}
                </span>
              ) : null}
              {prices.has(String(option.value)) ? (
                <span className="pl-6 text-xs text-muted-foreground tabular-nums">
                  {price === null || price === undefined
                    ? "not possible"
                    : `≈ ${formatPaise(price, currency)}`}
                </span>
              ) : null}
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

/** "Page 2 · Clause 4.3", with the exact sentence from the document on demand. */
export function Citation({
  evidence,
  approximatePages = false,
}: {
  evidence: Evidence[];
  approximatePages?: boolean;
}) {
  const first = evidence[0];
  if (!first) return null;
  const where = [
    `${approximatePages ? "≈ page" : "Page"} ${first.page}`,
    first.clause_ref ? `Clause ${first.clause_ref}` : null,
  ]
    .filter(Boolean)
    .join(" · ");
  return (
    <details className="group text-sm">
      <summary className="cursor-pointer list-none text-primary hover:underline">
        <span aria-hidden className="mr-1">
          📄
        </span>
        {first.checked === false
          ? `From a scanned page — please verify on ${where.charAt(0).toLowerCase()}${where.slice(1)}`
          : `Found in the document: ${where}`}
        <span className="ml-1 text-muted-foreground group-open:hidden">
          (show text)
        </span>
      </summary>
      <blockquote className="mt-2 border-l-2 border-primary/40 pl-3 text-muted-foreground italic">
        “{first.quote}”
      </blockquote>
    </details>
  );
}

export function Calculating({ labels }: { labels: string[] }) {
  return (
    <div className="flex flex-col items-center gap-4 py-24 text-center">
      <StepIndicator labels={labels} current={3} />
      <div className="mt-8 size-10 animate-spin rounded-full border-4 border-muted border-t-primary" />
      <p className="text-lg font-medium">Working out your cost…</p>
      <p className="text-sm text-muted-foreground">This takes a few seconds.</p>
    </div>
  );
}
