"use client";

import * as React from "react";

import {
  BuildingOfficeIcon,
  BuildingsIcon,
  CalculatorIcon,
  CalendarCheckIcon,
  ChalkboardTeacherIcon,
  ChatCircleDotsIcon,
  ChatsIcon,
  CheckIcon,
  ClockIcon,
  CloudIcon,
  DatabaseIcon,
  DevicesIcon,
  GavelIcon,
  GlobeIcon,
  HandCoinsIcon,
  HandshakeIcon,
  HeadsetIcon,
  LifebuoyIcon,
  LockKeyIcon,
  PaintBrushIcon,
  PlugsConnectedIcon,
  PlusCircleIcon,
  PresentationChartIcon,
  PulseIcon,
  QuestionIcon,
  RobotIcon,
  RocketIcon,
  ShieldCheckIcon,
  StorefrontIcon,
  UsersThreeIcon,
  WrenchIcon,
} from "@phosphor-icons/react/dist/ssr";

import { IconTile, type IconType } from "@/components/site/illustrations";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  api,
  type Evidence,
  type QuestionImpact,
  type QuickQuestion,
  type QuickRequest,
  type QuickSchedule,
  type StandardBlock,
} from "@/lib/api/client";
import { formatPaise, monthsToWeeks, monthsToWeeksUp } from "@/lib/format";
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

const TYPE_ICONS: Record<string, IconType> = {
  portal: GlobeIcon,
  business: BuildingsIcon,
  store: StorefrontIcon,
  booking: CalendarCheckIcon,
  ai: RobotIcon,
  other: PlusCircleIcon,
};

/** The icon for a kind of software (its tile is drawn by the card, which shows the choice). */
export function TypeIcon({ kind }: { kind: string }) {
  const Icon = TYPE_ICONS[kind] ?? PlusCircleIcon;
  return <Icon size={20} weight="duotone" aria-hidden="true" />;
}

/** One icon per question, so each question screen is recognisable at a glance. */
const QUESTION_ICONS: Record<string, IconType> = {
  version: RocketIcon,
  platforms: DevicesIcon,
  scale: UsersThreeIcon,
  integrations: PlugsConnectedIcon,
  old_data: DatabaseIcon,
  build_type: WrenchIcon,
  hosting: CloudIcon,
  support_years: HandshakeIcon,
  helpdesk_scope: HeadsetIcon,
  support_hours: ClockIcon,
  availability: PulseIcon,
  disaster_site: LifebuoyIcon,
  penalties: GavelIcon,
  web_domain: GlobeIcon,
  ssl_certificate: LockKeyIcon,
  security_audit: ShieldCheckIcon,
  reporting: PresentationChartIcon,
  design: PaintBrushIcon,
  chatbot_task: ChatCircleDotsIcon,
  chatbot_volume: ChatsIcon,
  launch_help: ChalkboardTeacherIcon,
  onsite_period: BuildingOfficeIcon,
  ai_passthrough: HandCoinsIcon,
  ai_use: RobotIcon,
};

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
                <CheckIcon size={12} weight="bold" aria-label="done" />
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
              <span
                aria-hidden="true"
                className="mr-2 hidden w-10 border-t border-dashed border-primary/30 sm:inline-block"
              />
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

/** The visible box (tick) or dot (radio) of a choice; the real input beside it stays for the keyboard. */
export function Mark({ on, round = false }: { on: boolean; round?: boolean }) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "mt-0.5 flex size-5 shrink-0 items-center justify-center border transition-colors duration-200",
        round ? "rounded-full" : "rounded-md",
        on
          ? "border-primary bg-primary text-primary-foreground"
          : "border-input bg-card",
      )}
    >
      {on ? (
        round ? (
          <span className="size-2 rounded-full bg-primary-foreground" />
        ) : (
          <CheckIcon size={14} weight="bold" />
        )
      ) : null}
    </span>
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
        "relative flex flex-col gap-2 overflow-hidden rounded-xl border bg-card p-4 transition-[border-color,background-color] duration-200 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring",
        checked
          ? "border-tape/40 bg-tape-soft/60"
          : excluded
            ? "border-dashed bg-transparent opacity-60"
            : "hover:border-primary/40 hover:bg-panel-2",
      )}
    >
      {checked ? (
        <span
          aria-hidden="true"
          className="absolute inset-x-0 top-0 h-0.5 bg-tape"
        />
      ) : null}
      <label className="flex cursor-pointer items-start gap-3">
        <input
          type="checkbox"
          checked={checked}
          onChange={onToggle}
          className="sr-only"
        />
        <Mark on={checked} />
        <span className="flex flex-col gap-1">
          <span className="font-semibold">{label}</span>
          <span className="text-sm text-muted-foreground">{hint}</span>
        </span>
      </label>
      {children ? <div className="pl-8">{children}</div> : null}
      {onNotIncluded && !checked ? (
        <div className="pl-7">
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
 * How long the form's project takes to build: with the usual team, and with the biggest team
 * that still helps (OPEN_QUESTIONS 179). Asked from the API as the form changes (debounced;
 * nothing is saved or priced); null until known or when it fails.
 */
export function useSchedule(body: QuickRequest | null): QuickSchedule | null {
  const [plan, setPlan] = React.useState<QuickSchedule | null>(null);
  const key = body ? JSON.stringify(body) : null;
  React.useEffect(() => {
    if (key === null) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      api
        .quickSchedule(JSON.parse(key) as QuickRequest, controller.signal)
        .then(setPlan)
        .catch(() => setPlan(null));
    }, IMPACT_DEBOUNCE_MS);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [key]);
  return plan;
}

/** The usual and fastest time to build beside the deadline, and what a typed deadline does. */
export function BuildTime({
  plan,
  weeks,
  keepTeam,
}: {
  plan: QuickSchedule | null;
  weeks: number | null;
  /** What to do when the client wants people for the whole (longer) period. */
  keepTeam: string;
}) {
  if (!plan) return null;
  const usual = monthsToWeeks(Number(plan.usual_months));
  const fastest = Math.max(1, monthsToWeeksUp(Number(plan.fastest_months)));
  const note =
    weeks === null
      ? null
      : weeks < fastest
        ? `Shorter than the fastest possible. More people would not finish sooner, so we price it for ${fastest} weeks and say so. To keep your date, launch the most important features first and the rest later.`
        : weeks < usual
          ? "Shorter than usual: a bigger team works in parallel, which costs more."
          : weeks > usual
            ? `Longer than the build needs: the team builds in about ${usual} weeks and hands over early, so the extra time adds no cost. If the client wants people kept for the whole ${weeks} weeks (a project manager, developers or support staff), ${keepTeam}`
            : null;
  return (
    <div className="flex flex-col gap-3">
      <dl className="grid max-w-md grid-cols-2 divide-x rounded-xl border bg-card">
        <div className="flex flex-col gap-1 px-4 py-3">
          <dt className="text-sm text-muted-foreground">Usual time</dt>
          <dd className="font-wide text-xl tabular-nums">
            about {usual} weeks
          </dd>
        </div>
        <div className="flex flex-col gap-1 px-4 py-3">
          <dt className="text-sm text-muted-foreground">Fastest possible</dt>
          <dd className="font-wide text-xl tabular-nums">
            about {fastest} weeks
          </dd>
        </div>
      </dl>
      {note ? (
        <p
          className={cn(
            "max-w-xl text-sm",
            weeks !== null && weeks < fastest
              ? "text-warning"
              : "text-muted-foreground",
          )}
        >
          {note}
        </p>
      ) : null}
    </div>
  );
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
            className="flex cursor-pointer items-start gap-3 rounded-lg p-2 hover:bg-panel-2 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring"
          >
            <input
              type="checkbox"
              checked={!removed.includes(b.key)}
              onChange={() => onToggle(b.key)}
              className="sr-only"
            />
            <Mark on={!removed.includes(b.key)} />
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

/** The header of every screen of the form: a small label, the title, one line under it (the
 * same as the "Your estimates" and start pages). */
export function StepHeader({
  eyebrow,
  title,
  children,
}: {
  eyebrow: string;
  title: React.ReactNode;
  children?: React.ReactNode;
}) {
  return (
    <header className="settle flex flex-col gap-2">
      <p className="eyebrow">{eyebrow}</p>
      <h1 className="font-wide text-[2rem] leading-tight text-balance sm:text-[2.5rem]">
        {title}
      </h1>
      {children ? (
        <p className="max-w-2xl text-muted-foreground">{children}</p>
      ) : null}
    </header>
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
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h2 className="font-wide text-lg">
          {title}
          {count !== undefined ? (
            <span className="ml-2 font-mono text-sm font-normal text-muted-foreground tabular-nums">
              {count}
            </span>
          ) : null}
        </h2>
        {aside ? (
          <span className="text-sm text-muted-foreground">{aside}</span>
        ) : null}
      </div>
      <div aria-hidden="true" className="h-px bg-border" />
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
  const Icon = QUESTION_ICONS[question.key] ?? QuestionIcon;
  return (
    <div className="settle flex flex-col gap-2">
      <span className="flex items-center gap-2 text-tape">
        <Icon
          size={18}
          weight="duotone"
          aria-hidden="true"
          className={question.key.startsWith("ai") ? "text-ai" : undefined}
        />
        <span className="eyebrow">A question</span>
      </span>
      <h1 className="font-wide text-[2rem] leading-tight text-balance sm:text-[2.5rem]">
        {question.label}
      </h1>
      <p className="max-w-2xl text-muted-foreground">
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
  compact = false,
}: {
  question: QuickQuestion;
  /** Two columns on wider screens (a long list, e.g. the user bands). */
  compact?: boolean;
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
      <legend className={cn("font-wide mb-3 text-lg", hideLegend && "sr-only")}>
        {question.label}
        {impact && impact.impact_paise > 0 && !hideLegend ? (
          <span className="mt-0.5 block text-sm font-normal text-muted-foreground">
            Can change the price by about{" "}
            {formatPaise(impact.impact_paise, currency)}
          </span>
        ) : null}
      </legend>
      <div
        className={cn(
          "overflow-hidden rounded-xl border bg-card",
          compact
            ? "grid divide-y sm:grid-cols-2 sm:divide-y-0 sm:[&>label]:border-b sm:[&>label:nth-child(odd)]:border-r"
            : "flex flex-col divide-y",
        )}
      >
        {question.options.map((option) => {
          const selected = option.value === value;
          const price = prices.get(String(option.value));
          return (
            <label
              key={String(option.value)}
              className={cn(
                "relative flex cursor-pointer items-start gap-4 px-5 py-4 transition-colors has-[:focus-visible]:bg-panel-2",
                selected ? "bg-tape-soft/60" : "hover:bg-panel-2",
              )}
            >
              {selected ? (
                <span
                  aria-hidden="true"
                  className="absolute inset-y-0 left-0 w-0.5 bg-tape"
                />
              ) : null}
              <input
                type="radio"
                name={question.key}
                checked={selected}
                onChange={() => onChange(option.value)}
                className="sr-only"
              />
              <span className="mt-0.5">
                <Mark on={selected} round />
              </span>
              <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                <span className="font-semibold">{option.label}</span>
                {option.hint ? (
                  <span className="text-sm text-muted-foreground">
                    {option.hint}
                  </span>
                ) : null}
              </span>
              {prices.has(String(option.value)) ? (
                <span
                  className={cn(
                    "shrink-0 pt-0.5 text-right font-mono text-sm tabular-nums",
                    selected
                      ? "font-medium text-foreground"
                      : "text-muted-foreground",
                  )}
                >
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

/** The users question: the numbers typed under it on both flows (OPEN_QUESTIONS 182). */
export const SCALE = "scale";
export const USERS_NUMBERS = [
  "users_total",
  "peak_concurrent_users",
  "chatbot_queries_per_day",
] as const;
export type UsersNumber = (typeof USERS_NUMBERS)[number];
const MAX_USERS_NUMBER = 1_000_000_000; // a typing guard only: the engine prices any number

/** A typed users number: empty = not typed (null), else a whole number, or "invalid". */
export function readUsersNumber(text: string): number | null | "invalid" {
  if (text.trim() === "") return null;
  const n = Number(text);
  return Number.isInteger(n) && n >= 1 && n <= MAX_USERS_NUMBER ? n : "invalid";
}

/** The numbers that follow `n` users on the question's curve (as the API prices them): a
 * straight line between its points, flat outside them, rounded half up. */
export function followingNumbers(
  question: Pick<QuickQuestion, "curve" | "answered_by_number">,
  n: number,
): Record<string, number> {
  const by = question.answered_by_number;
  if (!by || !question.curve || question.curve.length < 2) return {};
  const points = [...question.curve].sort((a, b) => a[by] - b[by]);
  const last = points.length - 1;
  const i =
    n >= points[last][by]
      ? last - 1
      : points.findIndex((_, j) => n < points[j + 1][by]);
  const lo = points[i];
  const hi = points[i + 1];
  const share = Math.min(Math.max((n - lo[by]) / (hi[by] - lo[by]), 0), 1);
  return Object.fromEntries(
    Object.keys(lo)
      .filter((k) => k !== by)
      .map((k) => [k, Math.round(lo[k] + (hi[k] - lo[k]) * share)]),
  );
}

/** Answers that follow a stated number: e.g. 50,000 registered users pick the smallest
 * scale option whose max_users covers them (an option with no limit covers everything). */
export function answersFromNumbers(
  questions: {
    key: string;
    answered_by_number?: string | null;
    options: { value: Choice; unsure?: boolean; max_users?: number | null }[];
  }[],
  numbers: Record<string, number>,
): Record<string, Choice> {
  const answers: Record<string, Choice> = {};
  for (const q of questions) {
    const n = q.answered_by_number ? numbers[q.answered_by_number] : undefined;
    if (n === undefined) continue;
    const fits = q.options
      .filter((o) => !o.unsure && (o.max_users == null || o.max_users >= n))
      .sort(
        (a, b) =>
          (a.max_users ?? Number.POSITIVE_INFINITY) -
          (b.max_users ?? Number.POSITIVE_INFINITY),
      );
    if (fits[0]) answers[q.key] = fits[0].value;
  }
  return answers;
}

/** The band a typed user count falls in (undefined: no count). */
export function bandOf(
  question: QuickQuestion,
  n: number | null,
): Choice | undefined {
  if (n === null || !question.answered_by_number) return undefined;
  return answersFromNumbers([question], { [question.answered_by_number]: n })[
    question.key
  ];
}

/**
 * Under the users question, the same on both flows: the exact number of users, the people
 * online at once and (with a chatbot) its questions a day, all optional. Empty = what the
 * band, or the typed users, mean on the question's curve; a typed number is priced as typed.
 */
export function UsersNumbers({
  question,
  band,
  values,
  onChange,
  chatbot,
  notes = {},
}: {
  question: QuickQuestion;
  band: Choice | undefined;
  values: Partial<Record<UsersNumber, string>>;
  onChange: (key: UsersNumber, text: string) => void;
  chatbot: boolean;
  /** Under a box, e.g. where the document states it. */
  notes?: Partial<Record<UsersNumber, React.ReactNode>>;
}) {
  const typed = readUsersNumber(values.users_total ?? "");
  const option = question.options.find((o) => String(o.value) === String(band));
  const users = typeof typed === "number" ? typed : (option?.max_users ?? null);
  const follow = users !== null ? followingNumbers(question, users) : {};
  const assumed = (key: UsersNumber) =>
    key === "users_total" ? option?.max_users : follow[key];
  const boxes: { key: UsersNumber; label: string; hint: string }[] = [
    {
      key: "users_total",
      label: "Exact number of users",
      hint: "If you know it: the price follows this number, not the top of the range.",
    },
    {
      key: "peak_concurrent_users",
      label: "People online at the same time",
      hint: "It decides the servers and hosting, not the building cost.",
    },
    ...(chatbot
      ? [
          {
            key: "chatbot_queries_per_day" as const,
            label: "Chatbot questions a day",
            hint: "It decides the cost of AI usage.",
          },
        ]
      : []),
  ];
  return (
    <div className="grid gap-x-6 gap-y-5 border-t pt-6 sm:grid-cols-2 lg:grid-cols-3">
      {boxes.map(({ key, label, hint }) => {
        const n = assumed(key);
        return (
          <div key={key} className="flex flex-col gap-2">
            <Label htmlFor={`users-${key}`} className="eyebrow">
              {label}{" "}
              <span className="font-normal text-muted-foreground normal-case">
                (optional)
              </span>
            </Label>
            <Input
              id={`users-${key}`}
              type="number"
              inputMode="numeric"
              min={1}
              value={values[key] ?? ""}
              onChange={(e) => onChange(key, e.target.value)}
              placeholder={n ? `We assume ${n.toLocaleString("en-IN")}` : ""}
              className="h-10 max-w-56"
            />
            <span className="text-sm text-muted-foreground">{hint}</span>
            {readUsersNumber(values[key] ?? "") === "invalid" ? (
              <span className="text-sm text-destructive">
                Enter a whole number, 1 or more.
              </span>
            ) : null}
            {notes[key] ?? null}
          </div>
        );
      })}
    </div>
  );
}

/** Whether every typed users number is empty or a whole number (the form can continue). */
export function usersNumbersValid(
  values: Partial<Record<UsersNumber, string>>,
): boolean {
  return USERS_NUMBERS.every(
    (k) => readUsersNumber(values[k] ?? "") !== "invalid",
  );
}

/** The typed users numbers the API prices (empty and invalid ones left out). */
export function usersOverrides(
  values: Partial<Record<UsersNumber, string>>,
): Record<string, number> {
  const out: Record<string, number> = {};
  for (const k of USERS_NUMBERS) {
    const n = readUsersNumber(values[k] ?? "");
    if (typeof n === "number") out[k] = n;
  }
  return out;
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
      <IconTile icon={CalculatorIcon} size="lg" className="mt-10" />
      <div className="h-1.5 w-64 overflow-hidden rounded-full bg-tape-soft">
        <div className="h-full w-1/3 animate-[measure_1.4s_cubic-bezier(0.65,0,0.35,1)_infinite] rounded-full bg-primary/80" />
      </div>
      <p className="text-lg font-medium">Working out your cost…</p>
    </div>
  );
}
