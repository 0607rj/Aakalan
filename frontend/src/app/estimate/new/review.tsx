"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

import { ErrorNotice, WarningNotice } from "@/components/status";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { currencySymbol } from "@/lib/format";
import {
  api,
  errorText,
  type FoundValue,
  type NotIncluded,
  type QuickOptions,
  type QuickRequest,
  type TenderDocument,
  type TenderExtraction,
} from "@/lib/api/client";

import {
  Calculating,
  type Choice,
  Citation,
  DOCUMENT_STEPS,
  initialChoices,
  optionsCurrency,
  QuestionGroup,
  QuestionHeading,
  relevantQuestions,
  setChoice,
  shownChoice,
  StepIndicator,
  unchosen,
  useQuestionImpact,
} from "./parts";
import {
  allFeatures,
  answerLabel,
  CheckStep,
  DetailsStep,
  effectiveLevels,
  featureSummary,
  featuresWithLevels,
  type Level,
  LevelsStep,
  ScopeStep,
  applicableScope,
  chosenScope,
  pickedLevels,
  presetFromFeatures,
  Progress,
  StepButtons,
  useSteps,
  VERSION,
} from "./steps";
import {
  type CustomItem,
  FoundOtherFeatures,
  itemsFromDocument,
  toCustomFeatures,
} from "./custom-features";
import {
  FeatureChoice,
  FeatureSections,
  featureTicks,
  notIncludedText,
  sentNotIncluded,
} from "./feature-sections";
import { PrebidQueries } from "./prebid";

/** Unit conversions between what the user types and what the API stores. */
type Unit = "count" | "rupees" | "percent";

interface Fact {
  key: string;
  label: string;
  unit: Unit;
  min: number;
  max?: number;
  integer: boolean;
  /** Only show when this feature is ticked. */
  needsFeature?: string;
  /** Only show when the document mentioned it. */
  onlyIfFound?: boolean;
  /** Indian bid terms (EMD, bank guarantee): elsewhere only shown if the document states them. */
  indiaTerm?: boolean;
}

const PAISE_PER_RUPEE = 100;
const PERCENT = 100;

// prettier-ignore
const FACTS: Fact[] = [
  { key: "users_total", label: "Registered users", unit: "count", min: 0, integer: true },
  { key: "peak_concurrent_users", label: "Users online at the same time", unit: "count", min: 0, integer: true },
  { key: "om_years", label: "Years of support after launch", unit: "count", min: 0, max: 10, integer: true },
  { key: "deadline_months", label: "Deadline (months)", unit: "count", min: 1, max: 60, integer: true },
  { key: "languages", label: "Languages", unit: "count", min: 1, max: 30, integer: true },
  { key: "chatbot_queries_per_day", label: "Chatbot questions per day", unit: "count", min: 0, integer: true, needsFeature: "ai_chatbot" },
  { key: "documents_per_month", label: "Documents uploaded per month", unit: "count", min: 0, integer: true, onlyIfFound: true },
  { key: "onsite_staff", label: "Staff at your office during support", unit: "count", min: 0, max: 50, integer: true, onlyIfFound: true },
  { key: "onsite_days", label: "Days they are needed in all (empty = every support year)", unit: "count", min: 1, max: 2000, integer: true, onlyIfFound: true },
  { key: "emd_paise", label: "EMD amount", unit: "rupees", min: 0, integer: false, indiaTerm: true },
  { key: "pbg_percent", label: "Performance guarantee (%)", unit: "percent", min: 0, max: 100, integer: false, indiaTerm: true },
];

const LEVEL_LABEL: Record<Level, string> = {
  basic: "Basic",
  standard: "Standard",
  advanced: "Advanced",
};

/** The user stories the document asks for under a feature, and the level their count gives. */
function Stories({
  stories,
  level,
}: {
  stories: string[];
  level: Level | null;
}) {
  if (stories.length === 0) return null;
  return (
    <details className="text-sm">
      <summary className="cursor-pointer text-muted-foreground">
        {stories.length} user {stories.length === 1 ? "story" : "stories"}
        {level ? ` · sized ${LEVEL_LABEL[level]}` : ""}
      </summary>
      <ul className="mt-2 list-disc space-y-1 pl-5">
        {stories.map((s) => (
          <li key={s}>{s}</li>
        ))}
      </ul>
    </details>
  );
}

function toDisplay(fact: Fact, value: unknown): string {
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return "";
  if (fact.unit === "rupees") return String(n / PAISE_PER_RUPEE);
  if (fact.unit === "percent") return String(Number((n * PERCENT).toFixed(4)));
  return String(n);
}

function toApi(fact: Fact, input: number): number {
  if (fact.unit === "rupees") return Math.round(input * PAISE_PER_RUPEE);
  if (fact.unit === "percent") return input / PERCENT;
  return input;
}

function factError(fact: Fact, text: string): string | null {
  if (text.trim() === "") return null;
  const n = Number(text);
  if (!Number.isFinite(n)) return "Enter a number.";
  if (fact.integer && !Number.isInteger(n)) return "Enter a whole number.";
  if (n < fact.min) return `Must be at least ${fact.min}.`;
  if (fact.max !== undefined && n > fact.max)
    return `Must be at most ${fact.max}.`;
  return null;
}

function asChoice(found: FoundValue | undefined): Choice | undefined {
  const v = found?.value;
  return typeof v === "string" || typeof v === "number" ? v : undefined;
}

/** Check what was found in the document, one screen at a time, then calculate. */
export function ReviewForm({
  options,
  doc,
  extraction,
  onBack,
}: {
  options: QuickOptions;
  doc: TenderDocument;
  extraction: TenderExtraction;
  onBack: () => void;
}) {
  const router = useRouter();
  const approx = doc.approximate_pages;
  const foundFeatures = React.useMemo(
    () => new Map(extraction.features.map((f) => [f.key, f])),
    [extraction.features],
  );

  const [name, setName] = React.useState(extraction.project_name);
  const suggested = options.features.filter(
    (f) => foundFeatures.get(f.key)?.suggested ?? false,
  );
  // a mobile app, other software and old data are questions, not tick boxes
  const [features, setFeatures] = React.useState<string[]>(() =>
    suggested.filter((f) => !f.hidden).map((f) => f.key),
  );
  const initialFacts = React.useMemo(
    () =>
      Object.fromEntries(
        FACTS.map((f) => [
          f.key,
          toDisplay(f, extraction.numbers[f.key]?.value),
        ]),
      ),
    [extraction.numbers],
  );
  const [facts, setFacts] =
    React.useState<Record<string, string>>(initialFacts);
  const found: Record<string, Choice> = Object.fromEntries(
    options.questions.flatMap((q) => {
      const value = asChoice(extraction.choices[q.key]);
      return value === undefined ? [] : [[q.key, value]];
    }),
  );
  // features the document mentions that are asked as questions (e.g. a mobile app)
  const preset = presetFromFeatures(
    options,
    suggested.filter((f) => f.hidden).map((f) => f.key),
  );
  const [choices, setChoices] = React.useState<Record<string, Choice>>(() =>
    initialChoices(options.questions, { ...preset, ...found }),
  );
  // answers from the document or the user are not overwritten by following defaults
  const answered = React.useRef(
    new Set<string>([...Object.keys(found), ...Object.keys(preset)]),
  );
  // answers from the document or the user; the rest print on the quote as assumed
  const [touched, setTouched] = React.useState<string[]>(() => [
    ...new Set([...Object.keys(found), ...Object.keys(preset)]),
  ]);
  const [customItems, setCustomItems] = React.useState<CustomItem[]>(() =>
    itemsFromDocument(extraction.other_features ?? []),
  );
  const customFeatures = toCustomFeatures(customItems);
  // features, scope items and standard blocks marked "Not included"
  const [notIncluded, setNotIncluded] = React.useState<NotIncluded[]>([]);
  // each found feature starts at the level its user stories give; the user can still change it
  const [levels, setLevels] = React.useState<Record<string, Level>>(() =>
    Object.fromEntries(
      extraction.features.flatMap((f) =>
        f.story_level ? [[f.key, f.story_level]] : [],
      ),
    ),
  );
  // scope items the document mentions come with their quotes; only what is ticked is priced
  const foundScope = React.useMemo(
    () => new Map((extraction.scope ?? []).map((s) => [s.key, s])),
    [extraction.scope],
  );
  const [scope, setScope] = React.useState<string[]>(() =>
    // what the document asks for is ticked; what it only implies waits for the user
    (extraction.scope ?? [])
      .filter((s) => s.status === "explicit")
      .map((s) => s.key),
  );
  const terms = extraction.payment_terms ?? null;
  const [useTerms, setUseTerms] = React.useState(terms !== null);
  const [customizing, setCustomizing] = React.useState(false);
  const everything = allFeatures(options, features, choices);
  // a mobile app, other software or old data count too (ticked through their question)
  const anyFeature = everything.length > 0 || customFeatures.length > 0;
  const ticks = featureTicks({
    options,
    features,
    setFeatures,
    everything,
    notIncluded,
    setNotIncluded,
  });
  const leveled = featuresWithLevels(options, everything);
  const effective = effectiveLevels(options, everything, choices, levels);
  const scopeGroups = applicableScope(options, everything);
  const [changing, setChanging] = React.useState<Record<string, boolean>>({});
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const currency = optionsCurrency(options);
  const visibleFacts = FACTS.filter(
    (f) =>
      (!f.needsFeature || features.includes(f.needsFeature)) &&
      (!f.onlyIfFound || extraction.numbers[f.key] !== undefined) &&
      (!f.indiaTerm ||
        options.country === "india" ||
        extraction.numbers[f.key] !== undefined),
  );
  const errors = Object.fromEntries(
    visibleFacts.map((f) => [f.key, factError(f, facts[f.key] ?? "")]),
  );
  const hasErrors = Object.values(errors).some(Boolean);
  const overrides: Record<string, number> = {};
  for (const fact of visibleFacts) {
    const text = (facts[fact.key] ?? "").trim();
    if (text !== "" && !errors[fact.key]) {
      overrides[fact.key] = toApi(fact, Number(text));
    }
  }
  // a stated number answers its question (e.g. the registered users pick the scale)
  const byNumber = answersFromNumbers(options.questions, overrides);
  const omYearsGiven = (facts.om_years ?? "").trim() !== "";
  const questions = relevantQuestions(
    options.questions,
    choices,
    everything,
    customFeatures.map((c) => c.category),
  ).filter(
    (q) =>
      !(q.key === "support_years" && omYearsGiven) &&
      // the document decides these (what is built), and a stated number answers its question
      q.on_upload !== "document" &&
      byNumber[q.key] === undefined,
  );
  const isOpen = (q: (typeof questions)[number]) =>
    extraction.choices[q.key] === undefined;
  const openQuestions = questions.filter(
    (q) => q.group === "main" && isOpen(q),
  );
  const details = questions.filter((q) => q.group === "detail" && isOpen(q));
  const foundQuestions = questions.filter((q) => !isOpen(q));
  // what the document does not state and is priced at the usual answer (a weak document
  // leaves many of these; each is worth confirming with the department before bidding)
  const assumed = relevantQuestions(
    options.questions,
    choices,
    everything,
    customFeatures.map((c) => c.category),
  ).filter(
    (q) =>
      isOpen(q) &&
      byNumber[q.key] === undefined &&
      !(q.key === "support_years" && omYearsGiven) &&
      !q.must_choose &&
      String(choices[q.key] ?? q.default) === String(q.default),
  );
  const toChoose = unchosen(questions, choices);
  const canSubmit =
    name.trim().length > 0 && anyFeature && !hasErrors && toChoose.length === 0;

  // Only levels picked by hand are sent; the rest follow the answers.
  const featureLevels = pickedLevels(options, everything, levels);
  const pricedScope = chosenScope(scopeGroups, scope);
  const request: QuickRequest = {
    mode: "vendor",
    name: name.trim() || "Estimate",
    country: options.country,
    document_id: doc.id,
    features,
    feature_levels: featureLevels,
    // a feature with more user stories than one large block covers is several modules
    feature_units: Object.fromEntries(
      extraction.features.flatMap((f) =>
        (f.story_units ?? 1) > 1 && everything.includes(f.key)
          ? [[f.key, f.story_units]]
          : [],
      ),
    ),
    custom_features: customFeatures,
    choices: { ...choices, ...byNumber },
    scope: pricedScope,
    overrides,
    not_included: sentNotIncluded(notIncluded, everything, pricedScope),
    answered: [...new Set([...touched, ...Object.keys(byNumber)])],
    payment_schedule:
      terms && useTerms
        ? terms.payments.map((p) => ({
            at_build_fraction: p.at_build_fraction,
            offset_months: p.offset_months,
            percent: p.percent,
          }))
        : null,
  };
  const [first, ...rest] = openQuestions.map((q) => `q:${q.key}`);
  const steps = useSteps([
    "found",
    ...(scopeGroups.length > 0 ? ["scope"] : []),
    ...(first ? [first] : []),
    ...(customizing && leveled.length > 0 ? ["levels"] : []),
    ...(visibleFacts.length > 0 || terms ? ["facts"] : []),
    ...rest,
    ...(foundQuestions.length > 0 ? ["found_answers"] : []),
    ...(details.length > 0 ? ["details"] : []),
    "check",
  ]);
  const impacts = useQuestionImpact(
    anyFeature &&
      !hasErrors &&
      (steps.current.startsWith("q:") || steps.current === "details")
      ? request
      : null,
  );

  // features from the list the document mentions (ticked if it asks for them), with the pages
  const foundKeys = options.features
    .filter((f) => foundFeatures.has(f.key))
    .map((f) => f.key);
  const foundOther = customItems.filter((i) => i.foundIndex !== null);

  /** One feature with its three states and where the document mentions it. */
  function card(key: string) {
    const found = foundFeatures.get(key);
    return (
      <FeatureChoice
        key={key}
        options={options}
        featureKey={key}
        ticks={ticks}
        onTick={(k) => ticks.tick(k, changeChoice)}
        notIncluded={notIncluded}
      >
        {found && !found.suggested ? (
          <span className="text-sm text-warning">
            Mentioned only{" "}
            {found.mentions === 1 ? "once" : `${found.mentions} times`} in a
            long document, so not ticked. Tick it if it is part of the work.
          </span>
        ) : null}
        {found ? (
          <Citation evidence={found.evidence} approximatePages={approx} />
        ) : null}
        {found ? (
          <Stories stories={found.stories} level={found.story_level ?? null} />
        ) : null}
      </FeatureChoice>
    );
  }

  function changeChoice(key: string, value: Choice) {
    answered.current.add(key);
    setTouched((now) => (now.includes(key) ? now : [...now, key]));
    if (key === VERSION) setLevels({}); // a new overall level resets hand-picked ones
    setChoices((now) =>
      setChoice(options.questions, now, answered.current, key, value),
    );
  }

  async function submit() {
    setSubmitting(true);
    setError(null);
    try {
      const summary = await api.createQuickEstimate({
        ...request,
        name: name.trim(),
      });
      router.push(`/estimate/${summary.estimate_id}`);
    } catch (e) {
      setError(errorText(e));
      setSubmitting(false);
    }
  }

  if (submitting) return <Calculating labels={DOCUMENT_STEPS} />;

  const question = steps.current.startsWith("q:")
    ? openQuestions.find((q) => `q:${q.key}` === steps.current)
    : undefined;

  return (
    <div className="flex flex-col gap-8">
      <StepIndicator labels={DOCUMENT_STEPS} current={2} />
      <Progress index={steps.index} total={steps.total} />

      {steps.current === "found" ? (
        <>
          <section className="flex flex-col gap-4">
            <div>
              <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
                Here&apos;s what we found in {doc.filename}
              </h1>
              <p className="mt-1 text-sm text-muted-foreground">
                {doc.pages} {approx ? "approximate " : ""}page
                {doc.pages === 1 ? "" : "s"} ·{" "}
                {extraction.reader === "ai" ? "Read by AI" : "Basic reading"} ·
                Check the features, then continue.
              </p>
            </div>
            {extraction.reader !== "ai" ? (
              <WarningNotice>
                Read with basic keyword matching (no AI key set) — please check
                carefully, some items may be missed.
              </WarningNotice>
            ) : null}
            {extraction.summary ? (
              <p className="max-w-3xl rounded-xl border bg-card px-4 py-3 text-muted-foreground">
                {extraction.summary}
              </p>
            ) : null}
            <div className="flex max-w-xl flex-col gap-2">
              <Label htmlFor="project-name" className="text-base">
                Project name
              </Label>
              <Input
                id="project-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="h-11 text-base"
              />
            </div>
          </section>

          <FeatureSections
            options={options}
            foundTitle="Found in your document"
            foundKeys={foundKeys}
            foundCount={foundKeys.length + foundOther.length}
            found={
              <>
                {foundKeys.map((key) => card(key))}
                <FoundOtherFeatures
                  items={customItems}
                  onChange={setCustomItems}
                  types={options.custom_feature_types}
                  approximatePages={approx}
                />
              </>
            }
            foundNote={
              (extraction.not_priced ?? []).length > 0 ? (
                <div className="rounded-xl border border-dashed px-4 py-3 text-sm">
                  <span className="font-medium">
                    Asked for, but not priced by this estimate:
                  </span>{" "}
                  {(extraction.not_priced ?? []).map((n) => n.label).join(", ")}
                  . Details on the last screen; price these separately.
                </div>
              ) : null
            }
            emptyHint={
              extraction.reader === "ai"
                ? "Nothing from our list was found in the document. Tick features below, or add your own."
                : "Nothing from our list was found (basic reading, no AI key). Tick features below, or add your own."
            }
            card={card}
            isTicked={ticks.isTicked}
            blocksBody={
              name.trim() !== ""
                ? { ...request, not_included: [], answered: null }
                : null
            }
            removedBlocks={notIncluded
              .filter((n) => n.kind === "standard")
              .map((n) => n.key)}
            onToggleBlock={(key) => ticks.toggleOut("standard", key)}
            customItems={customItems}
            onCustomItems={setCustomItems}
            approximatePages={approx}
          />
          <StepButtons
            onBack={onBack}
            onNext={steps.next}
            nextDisabled={name.trim() === "" || !anyFeature}
            hint={
              name.trim() === ""
                ? "Enter a project name."
                : !anyFeature
                  ? "Tick or add at least one thing the software should do."
                  : `${everything.length + customFeatures.length} selected`
            }
          />
        </>
      ) : steps.current === "scope" ? (
        <>
          <ScopeStep
            groups={scopeGroups}
            chosen={scope}
            suggested={[...foundScope.keys()]}
            source="the document"
            onTickSuggested={() =>
              setScope((now) => [...new Set([...now, ...foundScope.keys()])])
            }
            notes={Object.fromEntries(
              [...foundScope.values()].map((s) => [
                s.key,
                <span key={s.key} className="flex flex-col gap-1">
                  <span className="text-sm text-muted-foreground">
                    {s.status === "explicit"
                      ? "The document asks for this."
                      : `The document suggests it may be needed${s.note ? `: ${s.note}` : ""}. Please check.`}
                  </span>
                  <Citation evidence={s.evidence} approximatePages={approx} />
                </span>,
              ]),
            )}
            onToggle={(key) => {
              setScope((now) =>
                now.includes(key)
                  ? now.filter((k) => k !== key)
                  : [...now, key],
              );
              ticks.unmark("scope", key);
            }}
            notIncluded={notIncluded
              .filter((n) => n.kind === "scope")
              .map((n) => n.key)}
            onNotIncluded={(key) => ticks.toggleOut("scope", key)}
          />
          {(extraction.scope_set_aside ?? []).length > 0 ? (
            <div className="flex flex-col gap-2 rounded-xl bg-muted/60 px-4 py-3 text-sm">
              <span className="font-medium">
                Mentioned in the document, but not asked for now (not priced)
              </span>
              <ul className="flex flex-col gap-1">
                {(extraction.scope_set_aside ?? []).map((s) => (
                  <li key={s.key}>
                    {s.label}:{" "}
                    {s.status === "excluded"
                      ? "ruled out"
                      : s.status === "future"
                        ? "for a later phase or optional"
                        : "only mentioned"}
                    {" — "}
                    <Citation evidence={s.evidence} approximatePages={approx} />
                  </li>
                ))}
              </ul>
              <span className="text-muted-foreground">
                Tick it above if it should be built now.
              </span>
            </div>
          ) : null}
          <StepButtons onBack={steps.prev} onNext={steps.next} />
        </>
      ) : steps.current === "levels" ? (
        <>
          <LevelsStep
            features={leveled}
            levels={effective}
            defaultLevel={options.default_level}
            onChange={(key, level) =>
              setLevels((now) => ({ ...now, [key]: level }))
            }
          />
          <StepButtons onBack={steps.prev} onNext={steps.next} />
        </>
      ) : steps.current === "facts" ? (
        <section className="flex flex-col gap-6">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
              Key numbers
            </h1>
            <p className="mt-1 text-muted-foreground">
              Numbers from the document. Leave a box empty if it is not stated —
              we will use a typical value.
            </p>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {visibleFacts.map((fact) => {
              const found = extraction.numbers[fact.key];
              const value = facts[fact.key] ?? "";
              const unchanged =
                found !== undefined && value === initialFacts[fact.key];
              return (
                <div
                  key={fact.key}
                  className="flex flex-col gap-2 rounded-xl border bg-card p-4"
                >
                  <Label htmlFor={`fact-${fact.key}`} className="font-semibold">
                    {fact.label}
                    {fact.unit === "rupees"
                      ? ` (${currencySymbol(currency)})`
                      : ""}
                  </Label>
                  <Input
                    id={`fact-${fact.key}`}
                    type="number"
                    inputMode="decimal"
                    min={fact.min}
                    max={fact.max}
                    value={value}
                    placeholder="Not stated in the document"
                    onChange={(e) =>
                      setFacts((now) => ({
                        ...now,
                        [fact.key]: e.target.value,
                      }))
                    }
                    className="h-10"
                  />
                  {errors[fact.key] ? (
                    <span className="text-sm text-destructive">
                      {errors[fact.key]}
                    </span>
                  ) : null}
                  {found && unchanged ? (
                    <Citation
                      evidence={found.evidence}
                      approximatePages={approx}
                    />
                  ) : found ? (
                    <span className="text-sm text-muted-foreground">
                      Changed by you (document says {initialFacts[fact.key]})
                    </span>
                  ) : null}
                </div>
              );
            })}
          </div>
          {terms ? (
            <div className="flex flex-col gap-2 rounded-xl border bg-card p-4">
              <span className="font-semibold">
                When you pay, as the document says
              </span>
              <span>{terms.payments.map((p) => p.label).join(", ")}</span>
              <Citation evidence={terms.evidence} approximatePages={approx} />
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={useTerms}
                  onChange={(e) => setUseTerms(e.target.checked)}
                  className="size-4 accent-primary"
                />
                Use these payment terms in the price (late payments mean more
                cost of waiting for money)
              </label>
            </div>
          ) : null}
          <StepButtons
            onBack={steps.prev}
            onNext={steps.next}
            nextDisabled={hasErrors}
            hint={hasErrors ? "Fix the highlighted numbers." : null}
          />
        </section>
      ) : question ? (
        <section className="flex flex-col gap-6">
          <QuestionHeading
            question={question}
            impact={impacts.get(question.key)}
            currency={currency}
          />
          <p className="-mt-4 text-sm text-muted-foreground">
            {question.must_choose
              ? "Your decision: pick one."
              : preset[question.key] !== undefined
                ? "The document mentions this, so we picked the matching answer."
                : "The document doesn't say, so we picked the usual answer."}
          </p>
          <QuestionGroup
            question={question}
            value={shownChoice(question, choices)}
            impact={impacts.get(question.key)}
            currency={currency}
            hideLegend
            onChange={(value) => changeChoice(question.key, value)}
          />
          {question.key === VERSION && leveled.length > 0 ? (
            <button
              type="button"
              className="w-fit text-sm font-medium text-primary hover:underline"
              onClick={() => {
                setCustomizing(true);
                steps.goTo("levels");
              }}
            >
              Want to set each feature yourself? Change levels →
            </button>
          ) : null}
          <StepButtons
            onBack={steps.prev}
            onNext={steps.next}
            nextDisabled={unchosen([question], choices).length > 0}
            hint={
              unchosen([question], choices).length > 0
                ? "Pick an answer to continue."
                : null
            }
          />
        </section>
      ) : steps.current === "details" ? (
        <>
          <DetailsStep
            questions={details}
            choices={choices}
            onChange={changeChoice}
            impacts={impacts}
            currency={currency}
          />
          <StepButtons onBack={steps.prev} onNext={steps.next} />
        </>
      ) : steps.current === "found_answers" ? (
        <section className="flex flex-col gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
              Also found in the document
            </h1>
            <p className="mt-1 text-muted-foreground">
              These answers come from the document. Change any that are wrong.
            </p>
          </div>
          {foundQuestions.map((q) => {
            const found = extraction.choices[q.key];
            const selected = q.options.find((o) => o.value === choices[q.key]);
            const open = changing[q.key] ?? false;
            return (
              <div
                key={q.key}
                className="flex flex-col gap-3 rounded-xl border bg-card p-4"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="flex flex-col gap-1">
                    <span className="text-sm text-muted-foreground">
                      {q.label}
                    </span>
                    <span className="font-semibold">
                      {selected?.label ?? found?.label}
                      {selected?.hint ? (
                        <span className="font-normal text-muted-foreground">
                          {" "}
                          ({selected.hint})
                        </span>
                      ) : null}
                    </span>
                    {found && choices[q.key] === asChoice(found) ? (
                      <Citation
                        evidence={found.evidence}
                        approximatePages={approx}
                      />
                    ) : (
                      <span className="text-sm text-muted-foreground">
                        Changed by you
                      </span>
                    )}
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      setChanging((now) => ({ ...now, [q.key]: !open }))
                    }
                  >
                    {open ? "Done" : "Change"}
                  </Button>
                </div>
                {open ? (
                  <QuestionGroup
                    question={q}
                    value={shownChoice(q, choices)}
                    onChange={(value) => changeChoice(q.key, value)}
                    hideLegend
                    impact={impacts.get(q.key)}
                    currency={currency}
                  />
                ) : null}
              </div>
            );
          })}
          <StepButtons onBack={steps.prev} onNext={steps.next} />
        </section>
      ) : (
        <>
          <CheckStep
            rows={[
              { step: "found", label: "Project name", value: name.trim() },
              {
                step: "found",
                label: "Features",
                value: featureSummary(
                  options,
                  everything,
                  effective,
                  customFeatures.map((c) => c.name),
                ),
              },
              ...questions.map((q) => ({
                step: openQuestions.includes(q)
                  ? `q:${q.key}`
                  : details.includes(q)
                    ? "details"
                    : "found_answers",
                label: q.label,
                value: answerLabel(q, choices[q.key]),
              })),
              ...visibleFacts
                .filter((f) => (facts[f.key] ?? "").trim() !== "")
                .map((f) => ({
                  step: "facts",
                  label: f.label,
                  value: facts[f.key] ?? "",
                })),
              {
                step: "found",
                label: "Not included",
                value: notIncludedText(options, notIncluded),
              },
            ]}
            onChange={steps.goTo}
          >
            {assumed.length > 0 ? (
              <section className="flex flex-col gap-3 rounded-2xl border px-6 py-5">
                <div>
                  <h2 className="text-lg font-semibold">
                    Not in the document: we assumed
                  </h2>
                  <p className="text-sm text-muted-foreground">
                    The document does not say these, so the usual answer is
                    priced. Confirm them with the department before you bid.
                  </p>
                </div>
                <ul className="flex flex-col gap-2 text-sm">
                  {assumed.map((q) => (
                    <li
                      key={q.key}
                      className="flex flex-wrap justify-between gap-x-4"
                    >
                      <span className="text-muted-foreground">{q.label}</span>
                      <span className="font-medium">
                        {answerLabel(q, choices[q.key] ?? q.default)}
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}
            {(extraction.not_priced ?? []).length > 0 ? (
              <section className="flex flex-col gap-3 rounded-2xl border border-warning/30 bg-warning-muted px-6 py-5">
                <div>
                  <h2 className="text-lg font-semibold">
                    In the document, but not in this price
                  </h2>
                  <p className="text-sm text-muted-foreground">
                    The document asks for these. This estimate does not price
                    them, so check them yourself before you quote.
                  </p>
                </div>
                <ul className="flex flex-col gap-3">
                  {(extraction.not_priced ?? []).map((n) => (
                    <li key={n.topic} className="flex flex-col gap-1">
                      <span className="font-medium">{n.label}</span>
                      {n.note ? (
                        <span className="text-sm text-muted-foreground">
                          {n.note}
                        </span>
                      ) : null}
                      <Citation
                        evidence={n.evidence}
                        approximatePages={approx}
                      />
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}
            <PrebidQueries
              documentId={doc.id}
              approximatePages={approx}
              fallback={extraction.unclear_points}
            />
          </CheckStep>
          <ErrorNotice message={error} />
          <StepButtons
            onBack={steps.prev}
            onNext={submit}
            nextLabel="Calculate my cost"
            nextDisabled={!canSubmit}
            hint={
              canSubmit
                ? null
                : name.trim() === ""
                  ? "Enter a project name."
                  : !anyFeature
                    ? "Tick or add at least one thing the software should do."
                    : toChoose.length > 0
                      ? `Answer: ${toChoose[0].label}`
                      : "Fix the highlighted numbers."
            }
          />
        </>
      )}
    </div>
  );
}

/** Answers that follow from a stated number: e.g. 50,000 registered users pick the smallest
 * scale option whose max_users covers them (an option with no limit covers everything). */
function answersFromNumbers(
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
