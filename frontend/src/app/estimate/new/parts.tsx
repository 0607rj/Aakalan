"use client";

import * as React from "react";

import {
  api,
  type Evidence,
  type QuestionImpact,
  type QuickQuestion,
  type QuickRequest,
  type StandardBlock,
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
  /** A decision asked on every estimate: nothing is pre-selected. */
  must_choose?: boolean;
};

/** The answer shown as chosen: the user's, else the default (none for a must-choose question). */
export function shownChoice(
  q: DependentQuestion,
  choices: Record<string, Choice>,
): Choice | undefined {
  return choices[q.key] ?? (q.must_choose ? undefined : q.default);
}

/** Must-choose questions among `questions` that have no answer yet. */
export function unchosen<T extends DependentQuestion>(
  questions: T[],
  choices: Record<string, Choice>,
): T[] {
  return questions.filter((q) => q.must_choose && choices[q.key] === undefined);
}

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

/**
 * Starting answers: the given ones (fixed), then defaults that follow them. Must-choose
 * questions start unanswered.
 */
export function initialChoices(
  questions: DependentQuestion[],
  given: Record<string, Choice>,
): Record<string, Choice> {
  const asked = questions.filter(
    (q) => !q.must_choose || given[q.key] !== undefined,
  );
  const base: Record<string, Choice> = Object.fromEntries(
    asked.map((q) => [q.key, given[q.key] ?? q.default]),
  );
  for (const q of asked) {
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
    <ol className="flex flex-wrap items-center gap-x-1 gap-y-2 text-sm">
      {labels.map((label, i) => {
        const n = i + 1;
        const done = n < current;
        const active = n === current;
        return (
          <li key={label} className="flex items-center gap-2">
            <span
              className={cn(
                "flex size-6 items-center justify-center rounded-full border text-xs font-semibold tabular-nums transition-colors duration-300",
                active && "border-primary bg-primary text-primary-foreground",
                done && "border-primary/40 bg-tape-soft text-primary",
                !active && !done && "text-muted-foreground",
              )}
            >
              {done ? (
                <svg
                  aria-label="done"
                  viewBox="0 0 16 16"
                  className="size-3"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.25"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M3.5 8.5 6.5 11.5 12.5 4.5" />
                </svg>
              ) : (
                n
              )}
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

/** Marks an unticked item "Not included": the quote then says it is not in the price. */
export function NotIncludedToggle({
  excluded,
  onClick,
}: {
  excluded: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={excluded}
      className={cn(
        "w-fit rounded px-1.5 py-0.5 text-xs font-medium",
        excluded
          ? "bg-muted text-foreground"
          : "text-muted-foreground hover:text-foreground hover:underline",
      )}
    >
      {excluded ? "Not included (undo)" : "Mark as not included"}
    </button>
  );
}

export function FeatureCard({
  label,
  hint,
  checked,
  onToggle,
  excluded = false,
  onNotIncluded,
  children,
}: {
  label: string;
  hint: string;
  checked: boolean;
  onToggle: () => void;
  /** Marked "Not included" (not ticked, and printed as not in the price). */
  excluded?: boolean;
  onNotIncluded?: () => void;
  /** Extra content under the card (e.g. where the document says so). */
  children?: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        "flex flex-col gap-2 rounded-lg border bg-card p-4 transition-[border-color,background-color,box-shadow] duration-200",
        checked
          ? "border-primary bg-tape-soft/50 shadow-[0_0_0_1px_var(--primary)]"
          : excluded
            ? "border-dashed bg-transparent opacity-60"
            : "hover:border-foreground/30",
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
      {onNotIncluded && !checked ? (
        <div className="pl-6">
          <NotIncludedToggle excluded={excluded} onClick={onNotIncluded} />
        </div>
      ) : null}
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

/**
 * The standard building blocks of this project's size, included by default. Unticking one
 * leaves it out of the price, and the quote says so. Asked from the API as the form changes
 * (debounced; nothing is saved or priced).
 */
export function StandardBlocks({
  body,
  removed,
  onToggle,
}: {
  body: QuickRequest | null;
  removed: string[];
  onToggle: (key: string) => void;
}) {
  const [blocks, setBlocks] = React.useState<StandardBlock[]>([]);
  const key = body ? JSON.stringify(body) : null;
  React.useEffect(() => {
    if (key === null) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      api
        .standardBlocks(JSON.parse(key) as QuickRequest, controller.signal)
        .then(setBlocks)
        .catch(() => {
          // Keep the previous list silently.
        });
    }, IMPACT_DEBOUNCE_MS);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [key]);
  if (blocks.length === 0) return null;
  const kept = blocks.filter((b) => !removed.includes(b.key)).length;
  return (
    <section className="flex flex-col gap-3">
      <SectionHeading
        title="Included by default"
        count={kept}
        aside="untick if not needed"
      />
      <p className="text-sm text-muted-foreground">
        A project of this size usually needs these. Untick any you do not need:
        it is left out of the price, and the quote says so.
      </p>
      <div className="grid gap-2 sm:grid-cols-2">
        {blocks.map((b) => (
          <label
            key={b.key}
            className="flex cursor-pointer items-start gap-2 rounded-lg p-2 hover:bg-muted/40"
          >
            <input
              type="checkbox"
              checked={!removed.includes(b.key)}
              onChange={() => onToggle(b.key)}
              className="mt-1 size-4 accent-primary"
            />
            <span className="flex flex-col gap-0.5">
              <span>{b.label}</span>
              {b.hint ? (
                <span className="text-sm text-muted-foreground">{b.hint}</span>
              ) : null}
            </span>
          </label>
        ))}
      </div>
    </section>
  );
}

/** A section heading of the features screen, with its count so the page reads at a glance. */
export function SectionHeading({
  title,
  count,
  aside,
}: {
  title: string;
  count?: number;
  aside?: string;
}) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-b pb-2">
      <h2 className="text-base font-semibold">
        {title}
        {count !== undefined ? (
          <span className="ml-2 text-muted-foreground tabular-nums">
            ({count})
          </span>
        ) : null}
      </h2>
      {aside ? (
        <span className="text-sm text-muted-foreground">{aside}</span>
      ) : null}
    </div>
  );
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
      <h1 className="text-3xl font-semibold tracking-tight text-balance">
        {question.label}
      </h1>
      <p className="mt-1 text-muted-foreground">
        {impact && impact.impact_paise > 0
          ? `This answer can change the price by about ${formatPaise(impact.impact_paise, currency)}.`
          : "The usual answer is picked. Change it if it does not fit."}
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
  /** undefined: nothing chosen yet (a must-choose question). */
  value: Choice | undefined;
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
                "flex cursor-pointer flex-col gap-1 rounded-lg border bg-card p-4 transition-[border-color,background-color,box-shadow] duration-200",
                selected
                  ? "border-primary bg-tape-soft/50 shadow-[0_0_0_1px_var(--primary)]"
                  : "hover:border-foreground/30",
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
      <summary className="w-fit cursor-pointer list-none text-muted-foreground transition-colors hover:text-foreground">
        {first.checked === false
          ? `From a scanned page — please verify on ${where.charAt(0).toLowerCase()}${where.slice(1)}`
          : where}
        <span className="ml-1 text-primary group-open:hidden">show text</span>
      </summary>
      <blockquote className="mt-2 rounded-md bg-panel-2 px-3 py-2 text-muted-foreground">
        “{first.quote}”
      </blockquote>
    </details>
  );
}

export function Calculating({ labels }: { labels: string[] }) {
  return (
    <div className="flex flex-col items-center gap-4 py-24 text-center">
      <StepIndicator labels={labels} current={3} />
      <div className="mt-10 h-1 w-48 overflow-hidden rounded-full bg-muted">
        <div className="h-full w-1/3 animate-[measure_1.4s_cubic-bezier(0.65,0,0.35,1)_infinite] rounded-full bg-primary" />
      </div>
      <p className="text-lg font-medium">Working out your cost…</p>
    </div>
  );
}
