"use client";

import * as React from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import type { QuickOptions } from "@/lib/api/client";
import { cn } from "@/lib/utils";

import type { QuestionImpact } from "@/lib/api/client";

import { type Choice, QuestionGroup } from "./parts";

export type Level = "basic" | "standard" | "advanced";
export type Feature = QuickOptions["features"][number];
export type Question = QuickOptions["questions"][number];

/** The first-version / full-product question: its answer sets every feature's level. */
export const VERSION = "version";

function chosen(q: Question, choices: Record<string, Choice>) {
  const value = choices[q.key] ?? q.default;
  return q.options.find((o) => o.value === value);
}

/** Features the chosen answers add (a mobile app, other software, old data) with their level. */
export function addedFeatures(
  options: QuickOptions,
  choices: Record<string, Choice>,
): Record<string, string | null> {
  const out: Record<string, string | null> = {};
  for (const q of options.questions) {
    Object.assign(out, chosen(q, choices)?.add_features ?? {});
  }
  return out;
}

/** Ticked features plus those the answers add. */
export function allFeatures(
  options: QuickOptions,
  ticked: string[],
  choices: Record<string, Choice>,
): string[] {
  return [
    ...new Set([...ticked, ...Object.keys(addedFeatures(options, choices))]),
  ];
}

/**
 * The level each feature is priced at: the one picked for it, else the level its answer
 * sets, else the first-version / full-product default.
 */
export function effectiveLevels(
  options: QuickOptions,
  features: string[],
  choices: Record<string, Choice>,
  picked: Record<string, Level>,
): Record<string, Level> {
  const added = addedFeatures(options, choices);
  const versionLevel = options.questions
    .map((q) => chosen(q, choices)?.feature_level)
    .find((l) => l != null);
  const base = (versionLevel ?? options.default_level) as Level;
  return Object.fromEntries(
    features.map((k) => [k, picked[k] ?? (added[k] as Level | null) ?? base]),
  );
}

/** Only the levels picked by hand, for features still in the project. */
export function pickedLevels(
  options: QuickOptions,
  features: string[],
  picked: Record<string, Level>,
): Record<string, Level> {
  const leveled = new Set(
    options.features.filter((f) => f.levels.length > 0).map((f) => f.key),
  );
  return Object.fromEntries(
    Object.entries(picked).filter(
      ([k]) => features.includes(k) && leveled.has(k),
    ),
  );
}

/** Answers implied by features found in a document or saved in a template (e.g. a mobile
 * app found -> "website and a mobile app"). */
export function presetFromFeatures(
  options: QuickOptions,
  keys: string[],
): Record<string, Choice> {
  const out: Record<string, Choice> = {};
  for (const q of options.questions) {
    const match = q.options.find(
      (o) =>
        !o.unsure &&
        Object.keys(o.add_features ?? {}).some((k) => keys.includes(k)),
    );
    if (match) out[q.key] = match.value;
  }
  return out;
}

/**
 * One screen at a time. The current screen lives in the web address (?step=<key>) so the
 * browser Back button goes one screen back and a refresh keeps the place. When the list of
 * screens changes (an answer hides a later question), an unknown step falls back to the first.
 */
export function useSteps(keys: string[]) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const requested = searchParams.get("step");
  const index = Math.max(0, requested ? keys.indexOf(requested) : 0);
  const current = keys[index] ?? keys[0];

  function goTo(key: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (key === keys[0]) params.delete("step");
    else params.set("step", key);
    router.push(`/estimate/new?${params.toString()}`, { scroll: true });
  }
  return {
    current,
    index,
    total: keys.length,
    goTo,
    next: () => goTo(keys[Math.min(index + 1, keys.length - 1)]),
    prev: () => goTo(keys[Math.max(index - 1, 0)]),
  };
}

export function Progress({ index, total }: { index: number; total: number }) {
  const percent = Math.round(((index + 1) / total) * 100);
  return (
    <div className="flex flex-col gap-2">
      <span className="text-sm text-muted-foreground">
        Step {index + 1} of {total}
      </span>
      <div
        className="h-2 w-full max-w-xl overflow-hidden rounded-full bg-muted"
        role="progressbar"
        aria-valuemin={1}
        aria-valuemax={total}
        aria-valuenow={index + 1}
      >
        <div
          className="h-full rounded-full bg-primary transition-all"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}

/** Back / Continue under every screen. */
export function StepButtons({
  onBack,
  onNext,
  nextLabel = "Continue",
  nextDisabled = false,
  hint,
}: {
  onBack: () => void;
  onNext: () => void;
  nextLabel?: string;
  nextDisabled?: boolean;
  hint?: string | null;
}) {
  return (
    <div className="flex flex-wrap items-center gap-4">
      <Button variant="outline" size="lg" className="h-11" onClick={onBack}>
        Back
      </Button>
      <Button
        size="lg"
        className="h-11"
        disabled={nextDisabled}
        onClick={onNext}
      >
        {nextLabel}
      </Button>
      {hint ? (
        <span className="text-sm text-muted-foreground">{hint}</span>
      ) : null}
    </div>
  );
}

/** Ticked features that come in Basic / Standard / Advanced. */
export function featuresWithLevels(
  options: QuickOptions,
  ticked: string[],
): Feature[] {
  return options.features.filter(
    (f) => ticked.includes(f.key) && f.levels.length > 0,
  );
}

/** How much of each ticked feature is built: the price follows this, not who orders it. */
export function LevelsStep({
  features,
  levels,
  defaultLevel,
  onChange,
}: {
  features: Feature[];
  levels: Record<string, Level>;
  defaultLevel: string;
  onChange: (key: string, level: Level) => void;
}) {
  return (
    <section className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
          Change the level of any feature (optional)
        </h1>
        <p className="mt-1 max-w-3xl text-muted-foreground">
          Your answer on the last screen set every feature. Pick Basic for the
          simple version and Advanced for a large, detailed one.
        </p>
      </div>
      <div className="flex flex-col gap-4">
        {features.map((feature) => {
          const value = levels[feature.key] ?? defaultLevel;
          return (
            <fieldset
              key={feature.key}
              className="flex flex-col gap-3 rounded-xl border bg-card p-4"
            >
              <legend className="sr-only">{feature.label}</legend>
              <span className="font-semibold">{feature.label}</span>
              <div
                role="radiogroup"
                aria-label={feature.label}
                className="grid gap-3 sm:grid-cols-3"
              >
                {feature.levels.map((level) => {
                  const selected = level.key === value;
                  return (
                    <label
                      key={level.key}
                      className={cn(
                        "flex cursor-pointer flex-col gap-1 rounded-xl border p-3 transition-colors",
                        selected
                          ? "border-primary bg-primary/5 ring-1 ring-primary"
                          : "hover:border-primary/40 hover:bg-muted/40",
                      )}
                    >
                      <span className="flex items-center gap-2">
                        <input
                          type="radio"
                          name={`level-${feature.key}`}
                          checked={selected}
                          onChange={() =>
                            onChange(feature.key, level.key as Level)
                          }
                          className="size-4 accent-primary"
                        />
                        <span className="font-medium">{level.label}</span>
                      </span>
                      <span className="pl-6 text-sm text-muted-foreground">
                        {level.hint}
                      </span>
                    </label>
                  );
                })}
              </div>
            </fieldset>
          );
        })}
      </div>
    </section>
  );
}

export interface CheckRow {
  step: string;
  label: string;
  value: string;
}

/** Everything chosen, with a way back to each screen, before calculating. */
export function CheckStep({
  rows,
  onChange,
  children,
}: {
  rows: CheckRow[];
  onChange: (step: string) => void;
  children?: React.ReactNode;
}) {
  return (
    <section className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
          Check your answers
        </h1>
        <p className="mt-1 text-muted-foreground">
          Change anything that is not right, then calculate.
        </p>
      </div>
      <dl className="flex flex-col divide-y rounded-2xl border bg-card">
        {rows.map((row) => (
          <div
            key={`${row.step}-${row.label}`}
            className="flex flex-wrap items-start justify-between gap-3 px-5 py-3"
          >
            <div className="flex min-w-0 flex-col gap-0.5">
              <dt className="text-sm text-muted-foreground">{row.label}</dt>
              <dd className="font-medium break-words">{row.value}</dd>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onChange(row.step)}
            >
              Change
            </Button>
          </div>
        ))}
      </dl>
      {children}
    </section>
  );
}

/** The chosen option's label for a question (for the check screen). */
export function answerLabel(
  question: QuickOptions["questions"][number],
  value: Choice | undefined,
): string {
  const v = value ?? question.default;
  return question.options.find((o) => o.value === v)?.label ?? String(v);
}

/** "Online forms (Advanced), Search, ..." for the check screen. */
export function featureSummary(
  options: QuickOptions,
  ticked: string[],
  levels: Record<string, Level>,
  customNames: string[],
): string {
  const named = options.features
    .filter((f) => ticked.includes(f.key))
    .map((f) => {
      if (f.levels.length === 0) return f.label;
      const key = levels[f.key] ?? options.default_level;
      const label = f.levels.find((l) => l.key === key)?.label ?? key;
      return `${f.label} (${label})`;
    });
  return [...named, ...customNames].join(", ") || "None";
}

/** The optional details on one screen: skipped questions keep the usual answer. */
export function DetailsStep({
  questions,
  choices,
  onChange,
  impacts,
  currency,
}: {
  questions: Question[];
  choices: Record<string, Choice>;
  onChange: (key: string, value: Choice) => void;
  impacts: Map<string, QuestionImpact>;
  currency: string;
}) {
  return (
    <section className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
          A few more details (optional)
        </h1>
        <p className="mt-1 max-w-3xl text-muted-foreground">
          Answer what you know and skip the rest — we use the usual answer for
          anything you leave as it is.
        </p>
      </div>
      {questions.map((q) => (
        <QuestionGroup
          key={q.key}
          question={q}
          value={choices[q.key] ?? q.default}
          impact={impacts.get(q.key)}
          currency={currency}
          onChange={(value) => onChange(q.key, value)}
        />
      ))}
    </section>
  );
}

export type ScopeGroup = QuickOptions["scope"][number];

/** Scope groups that apply: those every project has and those of the ticked features. */
export function applicableScope(
  options: QuickOptions,
  features: string[],
): ScopeGroup[] {
  return options.scope.filter(
    (g) => g.feature === null || features.includes(g.feature),
  );
}

/** Only items of groups that still apply are sent (a feature may have been unticked). */
export function chosenScope(groups: ScopeGroup[], chosen: string[]): string[] {
  const keys = new Set(groups.flatMap((g) => g.items.map((i) => i.key)));
  return chosen.filter((k) => keys.has(k));
}

/** What else the features need: each ticked item adds the work it takes; something already
 * in the project is not counted again. Suggestions (from a document or the user's own words)
 * are marked, never ticked for the user: nothing here is priced unless ticked. */
export function ScopeStep({
  groups,
  chosen,
  suggested = [],
  notes = {},
  source = "your description",
  onToggle,
  onTickSuggested,
}: {
  groups: ScopeGroup[];
  chosen: string[];
  suggested?: string[];
  notes?: Record<string, React.ReactNode>;
  source?: string;
  onToggle: (key: string) => void;
  onTickSuggested?: () => void;
}) {
  const offered = new Set(groups.flatMap((g) => g.items.map((i) => i.key)));
  const waiting = suggested.filter(
    (k) => offered.has(k) && !chosen.includes(k),
  );
  return (
    <section className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
          What else does it need? (optional)
        </h1>
        <p className="mt-1 max-w-3xl text-muted-foreground">
          Tick only what the software really needs. Each item adds the work it
          takes; anything already included is not counted twice. Nothing here is
          priced unless you tick it.
        </p>
      </div>
      {waiting.length > 0 ? (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-dashed px-4 py-3 text-sm">
          <span>
            {waiting.length} suggested from {source}, marked{" "}
            <strong>Suggested</strong>. They are not included until you tick
            them.
          </span>
          {onTickSuggested ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onTickSuggested}
            >
              Tick the suggested ones
            </Button>
          ) : null}
        </div>
      ) : null}
      <div className="flex flex-col gap-4">
        {groups.map((group) => (
          <fieldset
            key={group.key}
            className="flex flex-col gap-3 rounded-xl border bg-card p-4"
          >
            <legend className="sr-only">{group.label}</legend>
            <span className="font-semibold">{group.label}</span>
            <div className="grid gap-2 sm:grid-cols-2">
              {group.items.map((item) => {
                const isSuggested = suggested.includes(item.key);
                const checked = chosen.includes(item.key);
                return (
                  <label
                    key={item.key}
                    className={cn(
                      "flex cursor-pointer items-start gap-2 rounded-lg p-2 hover:bg-muted/40",
                      isSuggested &&
                        !checked &&
                        "border border-dashed border-primary/40",
                    )}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => onToggle(item.key)}
                      className="mt-1 size-4 accent-primary"
                    />
                    <span className="flex flex-col gap-1">
                      <span>
                        {item.label}
                        {isSuggested ? " " : null}
                        {isSuggested ? (
                          <span className="ml-1 rounded bg-primary/10 px-1.5 py-0.5 text-xs font-medium text-primary">
                            Suggested
                          </span>
                        ) : null}
                      </span>
                      {item.note ? (
                        <span className="text-sm text-muted-foreground">
                          {item.partly_priced ? "Partly priced. " : ""}
                          {item.note}
                        </span>
                      ) : null}
                      {notes[item.key] ?? null}
                    </span>
                  </label>
                );
              })}
            </div>
          </fieldset>
        ))}
      </div>
    </section>
  );
}
