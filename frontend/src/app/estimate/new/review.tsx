"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

import { ErrorNotice, WarningNotice } from "@/components/status";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { currencySymbol, monthsToWeeks } from "@/lib/format";
import {
  api,
  errorText,
  type FactValue,
  type FoundValue,
  type NotIncluded,
  type QuickOptions,
  type QuickRequest,
  type ReviewPrefill,
  type TenderDocument,
  type TenderExtraction,
} from "@/lib/api/client";

import {
  Calculating,
  type Choice,
  Citation,
  DOCUMENT_STEPS,
  optionsCurrency,
  QuestionGroup,
  relevantQuestions,
  setChoice,
  shownChoice,
  StepIndicator,
  unchosen,
  useQuestionImpact,
  useSchedule,
  BuildTime,
  StepHeader,
} from "./parts";
import {
  allFeatures,
  answerLabel,
  CheckStep,
  effectiveLevels,
  featureSummary,
  featuresWithLevels,
  type Level,
  LevelsStep,
  ScopeStep,
  applicableScope,
  chosenScope,
  pickedLevels,
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
import {
  Queries,
  sentStaff,
  StaffEditor,
  staffError,
  staffRows,
  type StaffRow,
} from "./key-answers";

/** A number the document may state (its limits are what the user may type). */
type Fact = FactValue;
type Question = QuickOptions["questions"][number];

const PAISE_PER_RUPEE = 100;
const PERCENT = 100;

function asChoice(found: FoundValue | undefined): Choice | undefined {
  const v = found?.value;
  return typeof v === "string" || typeof v === "number" ? v : undefined;
}

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
  if (value === null || value === undefined) return ""; // not stated
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
  if (fact.max != null && n > fact.max) return `Must be at most ${fact.max}.`;
  return null;
}

/** Check what was found in the document, one screen at a time, then calculate. */
export function ReviewForm({
  options,
  doc,
  extraction,
  prefill,
  onBack,
}: {
  options: QuickOptions;
  doc: TenderDocument;
  extraction: TenderExtraction;
  /** The form's starting state, from the backend (services/quick/prefill). */
  prefill: ReviewPrefill;
  onBack: () => void;
}) {
  const router = useRouter();
  const approx = doc.approximate_pages;
  const foundFeatures = React.useMemo(
    () => new Map(extraction.features.map((f) => [f.key, f])),
    [extraction.features],
  );

  const [name, setName] = React.useState(prefill.name);
  // what the document asks for is ticked; a mobile app, other software and old data are
  // questions, not tick boxes (a found one answers its question)
  const [features, setFeatures] = React.useState<string[]>(prefill.features);
  const initialFacts = React.useMemo(
    () =>
      Object.fromEntries(
        prefill.facts.map((f) => [f.key, toDisplay(f, f.value)]),
      ),
    [prefill.facts],
  );
  const [facts, setFacts] =
    React.useState<Record<string, string>>(initialFacts);
  const [choices, setChoices] = React.useState<Record<string, Choice>>(
    prefill.choices,
  );
  // answers from the document or the user are not overwritten by following defaults
  const answered = React.useRef(new Set<string>(prefill.answered));
  // answers from the document or the user; the rest print on the quote as assumed
  const [touched, setTouched] = React.useState<string[]>(prefill.answered);
  const [customItems, setCustomItems] = React.useState<CustomItem[]>(() =>
    itemsFromDocument(prefill.custom_features, extraction.other_features ?? []),
  );
  const customFeatures = toCustomFeatures(customItems);
  // features, scope items and standard blocks marked "Not included"
  const [notIncluded, setNotIncluded] = React.useState<NotIncluded[]>([]);
  // each found feature starts at the level its user stories give; the user can still change it
  const [levels, setLevels] = React.useState<Record<string, Level>>(
    prefill.levels,
  );
  // scope items the document mentions come with their quotes; only what is ticked is priced
  const foundScope = React.useMemo(
    () => new Map((extraction.scope ?? []).map((s) => [s.key, s])),
    [extraction.scope],
  );
  // what the document asks for is ticked; what it only implies waits for the user
  const [scope, setScope] = React.useState<string[]>(prefill.scope);
  const terms = extraction.payment_terms ?? null;
  const [useTerms, setUseTerms] = React.useState(
    prefill.payment_schedule !== null,
  );
  const [customizing, setCustomizing] = React.useState(false);
  // staff during support, priced from the document's staff lines (null: the reading has none,
  // so the staff numbers on the facts screen are used)
  const [staff, setStaff] = React.useState<StaffRow[] | null>(() =>
    prefill.staff ? staffRows(prefill.staff) : null,
  );
  const staffHasErrors = (staff ?? []).some((r) => staffError(r) !== null);
  // the answers that move the price most (the API orders them by price effect) come first in
  // their topic, each with its clause and any pre-bid query
  const keyAnswers = prefill.key_answers ?? [];
  const keyRank = new Map(keyAnswers.map((k, i) => [k.key as string, i]));
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
  const visibleFacts = prefill.facts.filter(
    (f) =>
      (!f.needs_feature || features.includes(f.needs_feature)) &&
      (!f.only_if_found || extraction.numbers[f.key] !== undefined) &&
      (!f.india_term ||
        options.country === "india" ||
        extraction.numbers[f.key] !== undefined),
  );
  const errors = Object.fromEntries(
    visibleFacts.map((f) => [f.key, factError(f, facts[f.key] ?? "")]),
  );
  const hasErrors = Object.values(errors).some(Boolean) || staffHasErrors;
  // the numbers shown on the topic screens (the EMD is read and used, never shown)
  const factsShown = visibleFacts.filter((f) => !f.hidden);
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
  const isOpen = (q: Question) => extraction.choices[q.key] === undefined;
  const relevant = relevantQuestions(
    options.questions,
    choices,
    everything,
    customFeatures.map((c) => c.category),
  );
  // Every question of a topic is shown (OPEN_QUESTIONS 177): the document's answer with its
  // page, else the usual answer to confirm; not when a stated number answers it, nor what the
  // document decides when it says nothing (e.g. first version or the full product).
  const questions = relevant.filter(
    (q) =>
      !(q.key === "support_years" && omYearsGiven) &&
      byNumber[q.key] === undefined &&
      !(q.on_upload === "document" && isOpen(q)),
  );
  const rank = (key: string) => keyRank.get(key) ?? keyAnswers.length;
  const topicQuestions = (topic: string) =>
    questions
      .filter((q) => q.topic === topic)
      .sort((a, b) => rank(a.key) - rank(b.key));
  const topicFacts = (topic: string) =>
    factsShown.filter((f) => f.topic === topic);
  const hasTopic = (topic: string) =>
    topicQuestions(topic).length > 0 ||
    topicFacts(topic).length > 0 ||
    (topic === "support" && staff !== null) ||
    (topic === "contract" && terms !== null);
  // what the document does not state and is priced at the usual answer (a weak document
  // leaves many of these; each is worth confirming with the department before bidding)
  const assumed = relevant.filter(
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
    payment_schedule: useTerms ? prefill.payment_schedule : null,
    staff: staff === null ? null : sentStaff(staff),
    feature_stories: {}, // the document's own stories are used
    description: "", // nothing typed: the document says what it is
  };
  // what is built, then one screen per topic in the form's order (OPEN_QUESTIONS 177)
  const steps = useSteps([
    "found",
    ...(scopeGroups.length > 0 ? ["scope"] : []),
    ...options.topics.flatMap((t) =>
      hasTopic(t.key)
        ? [
            `t:${t.key}`,
            ...(t.key === "build" && customizing && leveled.length > 0
              ? ["levels"]
              : []),
          ]
        : [],
    ),
    "check",
  ]);
  const impacts = useQuestionImpact(
    anyFeature && !hasErrors && steps.current.startsWith("t:") ? request : null,
  );
  // the build time beside the deadline (contract); the deadline itself does not change it
  const { deadline_months: deadlineMonths, ...otherNumbers } = overrides;
  const schedule = useSchedule(
    anyFeature && !hasErrors && steps.current === "t:contract"
      ? { ...request, overrides: otherNumbers }
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

  const topic = options.topics.find((t) => `t:${t.key}` === steps.current);

  /** A number the document may state: as found (with its page), or typed. */
  function factBox(fact: Fact) {
    const found = extraction.numbers[fact.key];
    const value = facts[fact.key] ?? "";
    const unchanged = found !== undefined && value === initialFacts[fact.key];
    return (
      <div key={fact.key} className="flex flex-col gap-2">
        <Label htmlFor={`fact-${fact.key}`} className="eyebrow">
          {fact.label}
          {fact.unit === "rupees" ? ` (${currencySymbol(currency)})` : ""}
        </Label>
        {fact.hint ? (
          <span className="-mt-1 text-sm text-muted-foreground">
            {fact.hint}
          </span>
        ) : null}
        <Input
          id={`fact-${fact.key}`}
          type="number"
          inputMode="decimal"
          min={fact.min}
          max={fact.max ?? undefined}
          value={value}
          placeholder="Not stated"
          onChange={(e) =>
            setFacts((now) => ({ ...now, [fact.key]: e.target.value }))
          }
          className="h-10 max-w-48"
        />
        {errors[fact.key] ? (
          <span className="text-sm text-destructive">{errors[fact.key]}</span>
        ) : null}
        {found && unchanged ? (
          <Citation evidence={found.evidence} approximatePages={approx} />
        ) : found ? (
          <span className="text-sm text-muted-foreground">
            Changed by you (document says {initialFacts[fact.key]})
          </span>
        ) : (
          <span className="text-sm text-muted-foreground">
            Not in the document: we use a typical value.
          </span>
        )}
      </div>
    );
  }

  /** One question: the document's answer with its page (change it if wrong), else the usual
   * answer to confirm; with any pre-bid query about it. */
  function questionBlock(q: Question) {
    const found = extraction.choices[q.key];
    const queries = keyAnswers.find((k) => k.key === q.key)?.queries ?? [];
    if (found) {
      const selected = q.options.find((o) => o.value === choices[q.key]);
      const open = changing[q.key] ?? false;
      return (
        <div
          key={q.key}
          className="flex flex-col gap-3 rounded-xl border bg-card p-4"
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="flex flex-col gap-1">
              <span className="text-sm text-muted-foreground">{q.label}</span>
              <span className="font-semibold">
                {selected?.label ?? found.label}
                {selected?.hint ? (
                  <span className="font-normal text-muted-foreground">
                    {" "}
                    ({selected.hint})
                  </span>
                ) : null}
              </span>
              {choices[q.key] === asChoice(found) ? (
                <Citation evidence={found.evidence} approximatePages={approx} />
              ) : (
                <span className="text-sm text-muted-foreground">
                  Changed by you
                </span>
              )}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setChanging((now) => ({ ...now, [q.key]: !open }))}
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
          <Queries queries={queries} approximatePages={approx} />
        </div>
      );
    }
    return (
      <div key={q.key} className="flex flex-col gap-3">
        <div className="flex flex-col gap-1">
          <span className="font-wide text-lg">{q.label}</span>
          <span className="text-sm text-muted-foreground">
            {q.must_choose
              ? "Your decision: pick one."
              : prefill.answered.includes(q.key)
                ? "The document mentions this, so we picked the matching answer."
                : "Not in the document: we picked the usual answer. Change it if you know."}
          </span>
        </div>
        <QuestionGroup
          question={q}
          value={shownChoice(q, choices)}
          impact={impacts.get(q.key)}
          currency={currency}
          hideLegend
          onChange={(value) => changeChoice(q.key, value)}
        />
        <Queries queries={queries} approximatePages={approx} />
      </div>
    );
  }

  /** A topic's screen: the answers that move the price most first, then the numbers, the
   * other questions and (contract) the payment terms. */
  function topicScreen(key: string) {
    const shown = topicQuestions(key);
    const first = shown.filter((q) => keyRank.has(q.key));
    const others = shown.filter((q) => !keyRank.has(q.key));
    const numbers = topicFacts(key);
    const staffKey = keyAnswers.find((k) => k.key === "staff");
    // pre-bid queries of a key answer a stated number replaced (e.g. the support years)
    const orphanQueries = keyAnswers
      .filter(
        (k) =>
          k.key !== "staff" &&
          !shown.some((q) => q.key === k.key) &&
          options.questions.find((q) => q.key === k.key)?.topic === key,
      )
      .flatMap((k) => k.queries);
    return (
      <>
        {key === "support" && staff !== null ? (
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1">
              <span className="font-wide text-lg">Staff during support</span>
              <span className="text-sm text-muted-foreground">
                Read from the document. Check the people and the months.
              </span>
            </div>
            <StaffEditor
              rows={staff}
              onChange={setStaff}
              approximatePages={approx}
            />
            <Queries
              queries={staffKey?.queries ?? []}
              approximatePages={approx}
            />
          </div>
        ) : null}
        {first.map(questionBlock)}
        {numbers.length > 0 ? (
          <div className="grid gap-x-6 gap-y-5 border-y py-6 sm:grid-cols-2 lg:grid-cols-3">
            {numbers.map(factBox)}
          </div>
        ) : null}
        <Queries queries={orphanQueries} approximatePages={approx} />
        {others.map(questionBlock)}
        {key === "build" && leveled.length > 0 ? (
          <button
            type="button"
            className="w-fit text-sm font-medium text-primary hover:underline"
            onClick={() => {
              setCustomizing(true);
              steps.goTo("levels");
            }}
          >
            Want to set each feature&apos;s level yourself? Change levels →
          </button>
        ) : null}
        {key === "contract" ? (
          <BuildTime
            plan={schedule}
            weeks={
              deadlineMonths === undefined
                ? null
                : monthsToWeeks(Number(deadlineMonths))
            }
          />
        ) : null}
        {key === "contract" && terms ? (
          <div className="flex flex-col gap-2 rounded-xl border bg-card p-4">
            <span className="font-semibold">
              When you get paid, as the document says
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
              Use these payment terms in the price (late payments mean more cost
              of waiting for money)
            </label>
          </div>
        ) : null}
      </>
    );
  }

  return (
    <div className="flex flex-col gap-8">
      <StepIndicator labels={DOCUMENT_STEPS} current={2} />
      <Progress index={steps.index} total={steps.total} />

      <div key={steps.current} className="step-in flex flex-col gap-8">
        {steps.current === "found" ? (
          <>
            <section className="flex flex-col gap-4">
              <StepHeader
                eyebrow={`${doc.pages} ${approx ? "approximate " : ""}page${doc.pages === 1 ? "" : "s"} · ${extraction.reader === "ai" ? "read by AI" : "basic reading"}`}
                title={<>Here&apos;s what we found in {doc.filename}</>}
              >
                Check the features, then continue.
              </StepHeader>
              {extraction.reader !== "ai" ? (
                <WarningNotice>
                  Read with basic keyword matching (no AI key set) — please
                  check carefully, some items may be missed.
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
                    {(extraction.not_priced ?? [])
                      .map((n) => n.label)
                      .join(", ")}
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
                      <Citation
                        evidence={s.evidence}
                        approximatePages={approx}
                      />
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
        ) : topic ? (
          <section className="flex flex-col gap-8">
            <StepHeader eyebrow="From the document" title={topic.label}>
              {topic.hint}. What the document says shows its page; what it does
              not say is the usual answer: change it if you know better.
            </StepHeader>
            {topicScreen(topic.key)}
            <StepButtons
              onBack={steps.prev}
              onNext={steps.next}
              nextDisabled={
                topicFacts(topic.key).some((f) => errors[f.key]) ||
                (topic.key === "support" && staffHasErrors) ||
                unchosen(topicQuestions(topic.key), choices).length > 0
              }
              hint={
                topicFacts(topic.key).some((f) => errors[f.key]) ||
                (topic.key === "support" && staffHasErrors)
                  ? "Fix the highlighted numbers."
                  : unchosen(topicQuestions(topic.key), choices).length > 0
                    ? "Pick an answer for each question."
                    : null
              }
            />
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
                // the answers in the order asked: one topic at a time
                ...options.topics.flatMap((t) => [
                  ...(t.key === "support" && staff !== null
                    ? [
                        {
                          step: "t:support",
                          label: "Staff during support",
                          value: staffSummary(staff),
                        },
                      ]
                    : []),
                  ...topicQuestions(t.key).map((q) => ({
                    step: `t:${t.key}`,
                    label: q.label,
                    value: answerLabel(q, choices[q.key]),
                  })),
                  ...topicFacts(t.key)
                    .filter((f) => (facts[f.key] ?? "").trim() !== "")
                    .map((f) => ({
                      step: `t:${t.key}`,
                      label: f.label,
                      value: facts[f.key] ?? "",
                    })),
                ]),
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
    </div>
  );
}

/** The staff list in one line, for the check screen. */
function staffSummary(rows: StaffRow[]): string {
  const kept = rows.filter((r) => !r.leftOut);
  if (kept.length === 0) return "None";
  return kept
    .map(
      (r) =>
        `${r.countText} ${r.role} (${r.kind === "onsite" ? "onsite" : "offsite"}${
          r.monthsText.trim() ? `, ${r.monthsText} months` : ""
        })`,
    )
    .join("; ");
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
