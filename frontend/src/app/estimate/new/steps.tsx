"use client";

import * as React from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import type { QuickOptions } from "@/lib/api/client";
import { cn } from "@/lib/utils";

import type { QuestionImpact } from "@/lib/api/client";

import {
  type Choice,
  NotIncludedToggle,
  Mark,
  QuestionGroup,
  StepHeader,
  shownChoice,
} from "./parts";

export type Level = "basic" | "standard" | "advanced";
export type Feature = QuickOptions["features"][number];
export type Question = QuickOptions["questions"][number];
export type Topic = QuickOptions["topics"][number];

/** The optional details screen of consecutive topics, e.g. "d:hosting+support". */
export function detailsStep(topics: string[]): string {
  return `d:${topics.join("+")}`;
}

export function detailsTopics(step: string): string[] {
  return step.startsWith("d:") ? step.slice(2).split("+") : [];
}

/**
 * The manual form's question screens, one topic at a time (OPEN_QUESTIONS 177): each main
 * question on its own screen (the levels right after the version, when wanted), a topic's
 * optional detail questions on one screen after its main ones (the details of topics next to
 * each other share a screen), and the deadline with the contract. A topic never comes back.
 */
export function topicSteps(
  topics: Topic[],
  main: Question[],
  details: Question[],
  levelsAfter: string | null,
): string[] {
  const out: string[] = [];
  let pending: string[] = [];
  const flush = () => {
    if (pending.length > 0) out.push(detailsStep(pending));
    pending = [];
  };
  for (const topic of topics) {
    const own = main.filter((q) => q.topic === topic.key);
    if (own.length > 0) flush();
    for (const q of own) {
      out.push(`q:${q.key}`);
      if (q.key === levelsAfter) out.push("levels");
    }
    if (details.some((q) => q.topic === topic.key)) pending.push(topic.key);
    if (topic.key === "contract") {
      flush();
      out.push("deadline");
    }
  }
  flush();
  return out;
}

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
    <div className="flex items-center gap-4">
      <div
        className="h-1.5 w-full overflow-hidden rounded-full bg-tape-soft"
        role="progressbar"
        aria-label="Progress"
        aria-valuemin={1}
        aria-valuemax={total}
        aria-valuenow={index + 1}
      >
        <div
          className="h-full rounded-full bg-primary/80 transition-[width] duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]"
          style={{ width: `${percent}%` }}
        />
      </div>
      <span className="shrink-0 text-sm text-muted-foreground tabular-nums">
        {index + 1} / {total}
      </span>
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
    <div className="sticky bottom-0 z-10 flex flex-wrap items-center gap-3 border-t bg-background py-4 shadow-[0_-8px_16px_-12px_rgb(0_0_0/0.15)]">
      <Button variant="ghost" size="lg" className="h-11" onClick={onBack}>
        ← Back
      </Button>
      <Button
        size="lg"
        className="h-11 px-6"
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
    <section className="flex flex-col gap-8">
      <StepHeader eyebrow="Optional" title="Change the level of any feature">
        Your answer on the last screen set every feature. Pick Basic for the
        simple version and Advanced for a large, detailed one.
      </StepHeader>
      <div className="flex flex-col divide-y overflow-hidden rounded-xl border bg-card">
        {features.map((feature) => {
          const value = levels[feature.key] ?? defaultLevel;
          const chosen = feature.levels.find((l) => l.key === value);
          return (
            <fieldset
              key={feature.key}
              className="flex flex-col gap-3 px-5 py-4 md:flex-row md:items-center md:justify-between md:gap-6"
            >
              <legend className="sr-only">{feature.label}</legend>
              <span className="flex min-w-0 flex-col gap-0.5">
                <span className="font-semibold">{feature.label}</span>
                {chosen ? (
                  <span className="text-sm text-muted-foreground">
                    {chosen.hint}
                  </span>
                ) : null}
              </span>
              <div
                role="radiogroup"
                aria-label={feature.label}
                className="inline-flex w-fit shrink-0 rounded-lg border bg-background p-0.5"
              >
                {feature.levels.map((level) => {
                  const selected = level.key === value;
                  return (
                    <label
                      key={level.key}
                      className={cn(
                        "cursor-pointer rounded-md px-3 py-1.5 text-sm font-medium transition-colors has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring",
                        selected
                          ? "bg-tape text-primary-foreground"
                          : "text-muted-foreground hover:text-foreground",
                      )}
                    >
                      <input
                        type="radio"
                        name={`level-${feature.key}`}
                        checked={selected}
                        onChange={() =>
                          onChange(feature.key, level.key as Level)
                        }
                        className="sr-only"
                      />
                      {level.label}
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
    <section className="flex flex-col gap-8">
      <StepHeader eyebrow="Last step" title="Check your answers">
        Change anything that is not right, then calculate.
      </StepHeader>
      <dl className="flex flex-col divide-y border-y">
        {rows.map((row) => (
          <div
            key={`${row.step}-${row.label}`}
            className="grid grid-cols-1 items-baseline gap-x-6 gap-y-1 py-4 sm:grid-cols-[12rem_1fr_auto]"
          >
            <dt className="text-sm text-muted-foreground">{row.label}</dt>
            <dd className="font-medium break-words">{row.value}</dd>
            <button
              type="button"
              onClick={() => onChange(row.step)}
              className="w-fit text-sm font-medium text-primary hover:underline focus-visible:underline focus-visible:outline-none"
            >
              Change
            </button>
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
  const v = value ?? (question.must_choose ? undefined : question.default);
  if (v === undefined) return "Not answered yet";
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
/** The optional detail questions of one topic, or of topics next to each other (each under
 * its own heading). */
export function DetailsStep({
  sections,
  choices,
  onChange,
  impacts,
  currency,
}: {
  sections: { topic: Topic; questions: Question[] }[];
  choices: Record<string, Choice>;
  onChange: (key: string, value: Choice) => void;
  impacts: Map<string, QuestionImpact>;
  currency: string;
}) {
  const many = sections.length > 1;
  return (
    <section className="flex flex-col gap-10">
      <StepHeader
        eyebrow={`Optional · ${sections.map((s) => s.topic.label).join(" · ")}`}
        title={many ? "A few more details" : sections[0]?.topic.label}
      >
        Answer what you know and skip the rest. We use the usual answer for
        anything you leave as it is.
      </StepHeader>
      {sections.map((section) => (
        <div key={section.topic.key} className="flex flex-col gap-8">
          {many ? (
            <h2 className="eyebrow border-b pb-2">{section.topic.label}</h2>
          ) : null}
          {section.questions.map((q) => (
            <QuestionGroup
              key={q.key}
              question={q}
              value={shownChoice(q, choices)}
              impact={impacts.get(q.key)}
              currency={currency}
              onChange={(value) => onChange(q.key, value)}
            />
          ))}
        </div>
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

type ScopeItem = ScopeGroup["items"][number];

/** What else the features need: each ticked item adds the work it takes; something already
 * in the project is not counted again. Suggestions (from a document or the user's own words)
 * are marked, never ticked for the user: nothing here is priced unless ticked. The items every
 * project may need show first ("Often needed"), then one list per ticked feature; the
 * `advanced` ones (security, compliance, office login) are folded away until wanted. */
export function ScopeStep({
  groups,
  chosen,
  suggested = [],
  notes = {},
  source = "your description",
  onToggle,
  onTickSuggested,
  notIncluded,
  onNotIncluded,
  offerNotIncluded = true,
}: {
  groups: ScopeGroup[];
  chosen: string[];
  suggested?: string[];
  notes?: Record<string, React.ReactNode>;
  source?: string;
  onToggle: (key: string) => void;
  onTickSuggested?: () => void;
  /** Items marked "Not included" (printed on the quote as not in the price). */
  notIncluded?: string[];
  onNotIncluded?: (key: string) => void;
  /** Offer "Mark as not included" on every item (a mark made before can still be undone). */
  offerNotIncluded?: boolean;
}) {
  const offered = new Set(groups.flatMap((g) => g.items.map((i) => i.key)));
  const waiting = suggested.filter(
    (k) => offered.has(k) && !chosen.includes(k),
  );
  const often = groups
    .filter((g) => g.feature === null)
    .flatMap((g) => g.items.filter((i) => !i.advanced));
  const perFeature = groups
    .filter((g) => g.feature !== null)
    .map((g) => ({ ...g, items: g.items.filter((i) => !i.advanced) }))
    .filter((g) => g.items.length > 0);
  const advanced = groups.flatMap((g) => g.items.filter((i) => i.advanced));
  const advancedInUse = advanced.filter(
    (i) =>
      chosen.includes(i.key) ||
      suggested.includes(i.key) ||
      (notIncluded?.includes(i.key) ?? false),
  ).length;

  const list = (items: ScopeItem[]) => (
    <div className="flex flex-col divide-y overflow-hidden rounded-xl border bg-card">
      {items.map((item) => (
        <ScopeRow
          key={item.key}
          item={item}
          checked={chosen.includes(item.key)}
          isSuggested={suggested.includes(item.key)}
          excluded={notIncluded?.includes(item.key) ?? false}
          note={notes[item.key]}
          onToggle={() => onToggle(item.key)}
          onNotIncluded={
            onNotIncluded &&
            (offerNotIncluded || (notIncluded?.includes(item.key) ?? false))
              ? () => onNotIncluded(item.key)
              : undefined
          }
        />
      ))}
    </div>
  );

  return (
    <section className="flex flex-col gap-8">
      <StepHeader eyebrow="Optional" title="Any extras?">
        Extras that add work beyond the features. Tick only what you need:
        nothing here is priced unless you tick it, and nothing is counted twice.
      </StepHeader>
      {waiting.length > 0 ? (
        <div className="flex flex-wrap items-center justify-between gap-3 border-y border-dashed border-tape/40 py-3 text-sm">
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
      {often.length > 0 ? (
        <fieldset className="flex flex-col gap-3">
          <legend className="sr-only">Often needed</legend>
          <span className="font-wide text-lg">Often needed</span>
          {list(often)}
        </fieldset>
      ) : null}
      {perFeature.map((group) => (
        <fieldset key={group.key} className="flex flex-col gap-3">
          <legend className="sr-only">{group.label}</legend>
          <span className="font-wide text-lg">
            {group.label}
            <span className="ml-2 font-sans text-sm font-normal text-muted-foreground">
              for this feature
            </span>
          </span>
          {list(group.items)}
        </fieldset>
      ))}
      {advanced.length > 0 ? (
        <details
          open={advancedInUse > 0 ? true : undefined}
          className="group/adv flex flex-col border-y"
        >
          <summary className="flex cursor-pointer list-none items-center gap-3 py-4 [&::-webkit-details-marker]:hidden">
            <span className="text-muted-foreground transition-transform group-open/adv:rotate-90">
              ›
            </span>
            <span className="flex flex-col gap-0.5">
              <span className="font-wide text-lg">
                For large or government projects
              </span>
              <span className="text-sm text-muted-foreground">
                Security checks, data protection rules, office login.{" "}
                {advanced.length} items
                {advancedInUse > 0 ? `, ${advancedInUse} in use` : ""}.
              </span>
            </span>
          </summary>
          <div className="pb-5">{list(advanced)}</div>
        </details>
      ) : null}
    </section>
  );
}

/** One extra: plain words, what it is, and a tick. */
function ScopeRow({
  item,
  checked,
  isSuggested,
  excluded,
  note,
  onToggle,
  onNotIncluded,
}: {
  item: ScopeItem;
  checked: boolean;
  isSuggested: boolean;
  excluded: boolean;
  note?: React.ReactNode;
  onToggle: () => void;
  onNotIncluded?: () => void;
}) {
  return (
    <div
      className={cn(
        "relative flex flex-col gap-1 transition-colors",
        checked && "bg-tape-soft/60",
        isSuggested && !checked && "bg-primary/5",
        excluded && "opacity-60",
      )}
    >
      {checked ? (
        <span aria-hidden className="absolute inset-y-0 left-0 w-1 bg-tape" />
      ) : null}
      <label className="flex cursor-pointer items-start gap-3 px-5 py-4 hover:bg-panel-2/60 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring has-[:focus-visible]:ring-inset">
        <input
          type="checkbox"
          checked={checked}
          onChange={onToggle}
          className="sr-only"
        />
        <Mark on={checked} />
        <span className="flex min-w-0 flex-col gap-0.5">
          <span className="font-medium">
            {item.ask || item.label}
            {isSuggested ? (
              <span className="ml-2 rounded bg-primary/10 px-1.5 py-0.5 text-xs font-medium text-primary">
                Suggested
              </span>
            ) : null}
          </span>
          {item.hint ? (
            <span className="text-sm text-muted-foreground">{item.hint}</span>
          ) : null}
          {note ?? null}
        </span>
      </label>
      {onNotIncluded && !checked ? (
        <div className="-mt-2 pb-3 pl-13">
          <NotIncludedToggle excluded={excluded} onClick={onNotIncluded} />
        </div>
      ) : null}
    </div>
  );
}
