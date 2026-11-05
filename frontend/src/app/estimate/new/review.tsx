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
  NoReadyMadeNote,
  QuestionNotes,
  ReadyMadeNote,
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
  answersFromNumbers,
  bandOf,
  readUsersNumber,
  SCALE,
  USERS_NUMBERS,
  type UsersNumber,
  UsersNumbers,
  usersNumbersValid,
  CoverageTag,
  missingPrerequisites,
  PrerequisiteWarnings,
  ProjectContextLine,
  QuestionHeading,
} from "./parts";
import { Calculating } from "./calculating";
import {
  allFeatures,
  answerLabel,
  CheckStep,
  effectiveLevels,
  featureSummary,
  featuresWithLevels,
  type Level,
  LevelsStep,
  AddOns,
  DetailRow,
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
  OutsideScopeNote,
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

/** A folded list of answers on a topic screen (nothing shown when it is empty). */
function Folded({
  title,
  hint,
  children,
}: {
  title: string;
  hint: string;
  children: React.ReactNode[];
}) {
  if (children.length === 0) return null;
  return (
    <details className="group rounded-xl border bg-card">
      <summary className="flex cursor-pointer list-none flex-col gap-1 px-4 py-3">
        <span className="font-semibold">
          {title}
          <span className="ml-2 text-sm font-normal text-primary group-open:hidden">
            Show
          </span>
          <span className="ml-2 hidden text-sm font-normal text-primary group-open:inline">
            Hide
          </span>
        </span>
        <span className="text-sm text-muted-foreground">{hint}</span>
      </summary>
      <div className="flex flex-col gap-6 border-t px-4 py-4">{children}</div>
    </details>
  );
}

/** Requirement sentences no finding quotes (OPEN_QUESTIONS 204): shown so none is lost. */
function Uncovered({
  sentences,
  more,
}: {
  sentences: TenderExtraction["uncovered"];
  more: number;
}) {
  if (sentences.length === 0) return null;
  return (
    <Folded
      title={`Not priced yet: ${sentences.length + more} requirement sentence${sentences.length + more === 1 ? "" : "s"} nothing above covers`}
      hint="Each asks for something, and no feature or answer above quotes it. Most are covered by the standard blocks; if one is real extra work, add it as your own feature below."
    >
      {sentences.map((s, i) => (
        <p key={i} className="text-sm">
          <span className="font-mono text-xs text-muted-foreground">
            {s.document ? `${s.document}, ` : ""}page {s.page}
          </span>{" "}
          {s.text}
        </p>
      ))}
      {more > 0 ? (
        <p className="text-sm text-muted-foreground">
          … and {more} more in the document.
        </p>
      ) : null}
    </Folded>
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
  const hasErrors =
    Object.values(errors).some(Boolean) ||
    staffHasErrors ||
    !usersNumbersValid(facts);
  // the numbers shown on the topic screens (the EMD is read and used, never shown)
  const factsShown = visibleFacts.filter(
    (f) => !f.hidden && !isUsersNumber(f.key),
  );
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
    overrides,
  );
  // Every question of a topic is shown (OPEN_QUESTIONS 177): the document's answer with its
  // page, else the usual answer to confirm; not when a stated number answers it, nor what the
  // document decides when it says nothing (e.g. first version or the full product).
  const questions = relevant.filter(
    (q) =>
      !(q.key === "support_years" && omYearsGiven) &&
      (byNumber[q.key] === undefined || q.key === SCALE) &&
      !(q.on_upload === "document" && isOpen(q)),
  );
  const rank = (key: string) => keyRank.get(key) ?? keyAnswers.length;
  // The same questions as the manual form (OPEN_QUESTIONS 215): each main question on a screen
  // of its own, in the topics' order; the rest on one optional screen. A tender-only question
  // the document does not mention is not asked: its usual answer is priced and listed under
  // "Not in the document: we assumed" on the check screen.
  const foundInDocument = (q: Question) =>
    extraction.choices[q.key] !== undefined ||
    byNumber[q.key] !== undefined ||
    prefill.answered.includes(q.key);
  const hasQueries = (q: Question) =>
    (keyAnswers.find((k) => k.key === q.key)?.queries ?? []).length > 0;
  const mainQuestions = options.topics.flatMap((t) =>
    questions.filter((q) => q.group === "main" && q.topic === t.key),
  );
  const moreQuestions = options.topics.flatMap((t) =>
    questions
      .filter(
        (q) =>
          q.topic === t.key &&
          q.group !== "main" &&
          !(
            q.group === "document" &&
            !foundInDocument(q) &&
            !q.must_choose &&
            !hasQueries(q) &&
            unchosen([q], choices).length === 0
          ),
      )
      .sort((a, b) => rank(a.key) - rank(b.key)),
  );
  const lastBuildQuestion = mainQuestions
    .filter((q) => q.topic === "build")
    .at(-1)?.key;
  const stepOf = (q: Question) =>
    mainQuestions.includes(q) ? `q:${q.key}` : "more";
  const topicQuestions = (topic: string) =>
    questions
      .filter((q) => q.topic === topic)
      .sort((a, b) => rank(a.key) - rank(b.key));
  const topicFacts = (topic: string) =>
    factsShown.filter((f) => f.topic === topic);
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
    project_domain: extraction.project_domain ?? "", // shown only, never priced
  };
  // what is built, then the main questions one at a time, then the optional screen
  const steps = useSteps([
    "found",
    ...mainQuestions.flatMap((q) => [
      `q:${q.key}`,
      ...(q.key === lastBuildQuestion && customizing && leveled.length > 0
        ? ["levels"]
        : []),
    ]),
    "more",
    "check",
  ]);
  // ready products are common for this kind of software (OPEN_QUESTIONS 209)
  const questionNotes = extraction.ready_made
    ? { build_type: <ReadyMadeNote note={extraction.ready_made.note} /> }
    : extraction.industry_suggestions_asked
      ? { build_type: <NoReadyMadeNote /> }
      : {};
  const impacts = useQuestionImpact(
    anyFeature &&
      !hasErrors &&
      (steps.current.startsWith("q:") || steps.current === "more")
      ? request
      : null,
  );
  // the build time beside the deadline (contract); the deadline itself does not change it
  const { deadline_months: deadlineMonths, ...otherNumbers } = overrides;
  const schedule = useSchedule(
    anyFeature && !hasErrors && steps.current === "more"
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
        {found ? (
          <CoverageTag kind={found.suggested ? "catalog" : "optional"} />
        ) : null}
        {found?.outside_scope ? <OutsideScopeNote /> : null}
        {found && !found.suggested && !found.outside_scope ? (
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
    const scale = options.questions.find((q) => q.key === SCALE);
    const typed = readUsersNumber(facts.users_total ?? "");
    if (
      key === SCALE &&
      scale &&
      typeof typed === "number" &&
      bandOf(scale, typed) !== value
    )
      setFacts((now) => ({ ...now, users_total: "" })); // a band the users are not in
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

  if (submitting)
    return <Calculating labels={DOCUMENT_STEPS} name={name.trim()} />;

  const question = mainQuestions.find((q) => `q:${q.key}` === steps.current);

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
  function questionBlock(q: Question, ownScreen = false) {
    const found = extraction.choices[q.key];
    const value = byNumber[q.key] ?? shownChoice(q, choices);
    const queries = keyAnswers.find((k) => k.key === q.key)?.queries ?? [];
    if (found) {
      const selected = q.options.find((o) => o.value === value);
      const open = changing[q.key] ?? false;
      return (
        <div
          key={q.key}
          className="flex flex-col gap-3 rounded-xl border bg-card p-4"
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="flex flex-col gap-1">
              {ownScreen ? (
                <span className="eyebrow">The document says</span>
              ) : (
                <span className="text-sm text-muted-foreground">{q.label}</span>
              )}
              <span className="font-semibold">
                {selected?.label ?? found.label}
                {selected?.hint ? (
                  <span className="font-normal text-muted-foreground">
                    {" "}
                    ({selected.hint})
                  </span>
                ) : null}
              </span>
              {value === asChoice(found) ? (
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
              value={value}
              onChange={(v) => changeChoice(q.key, v)}
              hideLegend
              compact={q.key === SCALE}
              impact={impacts.get(q.key)}
              currency={currency}
            />
          ) : null}
          <Queries queries={queries} approximatePages={approx} />
          {q.key === SCALE ? usersNumbers(q, value) : null}
        </div>
      );
    }
    return (
      <div key={q.key} className="flex flex-col gap-3">
        <div className="flex flex-col gap-1">
          {ownScreen ? null : (
            <span className="font-wide text-lg">{q.label}</span>
          )}
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
          value={value}
          impact={impacts.get(q.key)}
          currency={currency}
          hideLegend
          compact={q.key === SCALE}
          onChange={(v) => changeChoice(q.key, v)}
        />
        <Queries queries={queries} approximatePages={approx} />
        {q.key === SCALE ? usersNumbers(q, value) : null}
      </div>
    );
  }

  /** Under the users question: the users, people online at once and chatbot questions a day
   * the document states (with the page), as on the manual form (OPEN_QUESTIONS 182). */
  function usersNumbers(q: Question, band: Choice | undefined) {
    const note = (key: UsersNumber) => {
      const found = extraction.numbers[key];
      if (!found) return null;
      return (facts[key] ?? "") === initialFacts[key] ? (
        <Citation evidence={found.evidence} approximatePages={approx} />
      ) : (
        <span className="text-sm text-muted-foreground">
          Changed by you (document says {initialFacts[key] || "nothing"})
        </span>
      );
    };
    return (
      <UsersNumbers
        question={q}
        band={band}
        values={facts}
        chatbot={visibleFacts.some((f) => f.key === "chatbot_queries_per_day")}
        onChange={(key, text) => setFacts((now) => ({ ...now, [key]: text }))}
        notes={Object.fromEntries(USERS_NUMBERS.map((k) => [k, note(k)]))}
      />
    );
  }

  /** The optional screen (OPEN_QUESTIONS 199, 215): the staff the document lists, then "Please
   * answer" (what the document does not say and moves the price a lot, a decision, or an
   * answer with a pre-bid query), the numbers, and two folded lists: what the document says
   * (with its page) and the usual answers it leaves (priced as they are). */
  function moreScreen() {
    const shown = moreQuestions;
    // asked open: a decision, an answer with a pre-bid query, or one with no answer yet;
    // the rest the document leaves are closed rows with the usual answer, as on the manual form
    const ask = shown.filter(
      (q) =>
        q.must_choose || hasQueries(q) || unchosen([q], choices).length > 0,
    );
    // what the document changes from the usual answer stays in view (it changes the price, so
    // the user should see it); answers the same as usual are folded (OPEN_QUESTIONS 218). Split
    // by the pre-filled answer, so a row never moves while the user changes it.
    const fromDocument = shown.filter(
      (q) => !ask.includes(q) && foundInDocument(q),
    );
    const changedByDocument = fromDocument.filter(
      (q) => q.key in prefill.choices && prefill.choices[q.key] !== q.default,
    );
    const sameAsUsual = fromDocument.filter(
      (q) => !changedByDocument.includes(q),
    );
    const assumedHere = shown.filter(
      (q) => !ask.includes(q) && !foundInDocument(q),
    );
    const staffKey = keyAnswers.find((k) => k.key === "staff");
    // a number the document states stays in view (by what it stated, so a box never moves
    // while the user types in it)
    const numbersStated = factsShown.filter(
      (f) =>
        extraction.numbers[f.key] !== undefined ||
        (initialFacts[f.key] ?? "").trim() !== "",
    );
    const numbersOpen = factsShown.filter((f) => !numbersStated.includes(f));
    // pre-bid queries of a key answer that is asked nowhere (e.g. a stated number replaced it)
    const asked = new Set([...mainQuestions, ...shown].map((q) => q.key));
    const orphanQueries = keyAnswers
      .filter((k) => k.key !== "staff" && !asked.has(k.key))
      .flatMap((k) => k.queries);
    return (
      <>
        {staff !== null ? (
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
        {ask.length > 0 ? (
          <div className="flex flex-col gap-1">
            <span className="eyebrow">Please answer</span>
            <span className="text-sm text-muted-foreground">
              The document does not say, and the answer changes the price.
            </span>
          </div>
        ) : null}
        {ask.map((q) => questionBlock(q))}
        {assumedHere.length > 0 ? (
          <div className="flex flex-col gap-2">
            <span className="text-sm text-muted-foreground">
              Not in the document, so we used the usual answer:
            </span>
            <div className="flex flex-col divide-y overflow-hidden rounded-2xl border bg-card">
              {assumedHere.map((q) => (
                <DetailRow
                  key={q.key}
                  question={q}
                  value={shownChoice(q, choices)}
                  changed={q.key in choices && choices[q.key] !== q.default}
                  impact={impacts.get(q.key)}
                  currency={currency}
                  onChange={(v) => changeChoice(q.key, v)}
                />
              ))}
            </div>
          </div>
        ) : null}
        {numbersStated.length > 0 ? (
          <div className="grid gap-x-6 gap-y-5 border-y py-6 sm:grid-cols-2 lg:grid-cols-3">
            {numbersStated.map(factBox)}
          </div>
        ) : null}
        {numbersOpen.length > 0 ? (
          <Folded
            title={`Numbers the document does not state (${numbersOpen.length})`}
            hint="A typical value is used for each. Open to type one if you know it."
          >
            {[
              <div
                key="numbers"
                className="grid gap-x-6 gap-y-5 sm:grid-cols-2 lg:grid-cols-3"
              >
                {numbersOpen.map(factBox)}
              </div>,
            ]}
          </Folded>
        ) : null}
        <Queries queries={orphanQueries} approximatePages={approx} />
        {changedByDocument.length > 0 ? (
          <div className="flex flex-col gap-1">
            <span className="eyebrow">Check these</span>
            <span className="text-sm text-muted-foreground">
              The document changes these from the usual answer, and that changes
              the price. Each shows its page.
            </span>
          </div>
        ) : null}
        {changedByDocument.map((q) => questionBlock(q))}
        {sameAsUsual.length > 0 ? (
          <Folded
            title={`Found in your document (${sameAsUsual.length})`}
            hint="The same as the usual answer. Each shows its page."
          >
            {sameAsUsual.map((q) => questionBlock(q))}
          </Folded>
        ) : null}
        <BuildTime
          plan={schedule}
          weeks={
            deadlineMonths === undefined
              ? null
              : monthsToWeeks(Number(deadlineMonths))
          }
          keepTeam={
            staff !== null
              ? "add them under Staff during support at the top of this screen, or the price leaves them out."
              : "the price leaves them out: this reading has no staff list (read the document again)."
          }
        />
        {terms ? (
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
    <QuestionNotes.Provider value={questionNotes}>
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
                {extraction.own_report ? (
                  <WarningNotice>
                    This file is an estimate report made by Aakalan, not a
                    requirement document. Its features and answers come from
                    that earlier estimate, so the price may not match your
                    project. For a fresh reading, upload the RFP, SRS or scope
                    document instead.
                  </WarningNotice>
                ) : null}
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
                <ProjectContextLine
                  domain={extraction.project_domain}
                  roles={extraction.user_roles}
                />
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
                  <>
                    {(extraction.not_priced ?? []).length > 0 ? (
                      <div className="rounded-xl border border-dashed px-4 py-3 text-sm">
                        <span className="font-medium">
                          Asked for, but not priced by this estimate:
                        </span>{" "}
                        {(extraction.not_priced ?? [])
                          .map((n) => n.label)
                          .join(", ")}
                        . Details on the last screen; price these separately.
                      </div>
                    ) : null}
                    <PrerequisiteWarnings
                      items={missingPrerequisites(
                        options,
                        everything,
                        [...foundScope.keys()],
                        Object.fromEntries(
                          touched.flatMap((k) =>
                            k in choices ? [[k, choices[k]]] : [],
                          ),
                        ),
                      )}
                    />
                    <Uncovered
                      sentences={extraction.uncovered ?? []}
                      more={extraction.uncovered_more ?? 0}
                    />
                  </>
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
                suggestions={extraction.industry_suggestions ?? []}
                domain={extraction.project_domain ?? ""}
                forDocument
                suggestionsAsked={
                  extraction.industry_suggestions_asked ?? false
                }
                onTick={(k) => ticks.tick(k, changeChoice)}
              />
              <AddOns
                groups={scopeGroups}
                chosen={scope}
                suggested={[...foundScope.keys()]}
                source="the document"
                notes={Object.fromEntries(
                  [...foundScope.values()].map((s) => [
                    s.key,
                    <span key={s.key} className="flex flex-col gap-1">
                      <span className="text-muted-foreground">
                        {s.status === "explicit"
                          ? "The document asks for this."
                          : `The document suggests it may be needed${s.note ? `: ${s.note}` : ""}. Please check.`}
                      </span>
                      <Citation
                        evidence={s.evidence}
                        approximatePages={approx}
                      />
                    </span>,
                  ]),
                )}
                notIncluded={notIncluded
                  .filter((n) => n.kind === "scope")
                  .map((n) => n.key)}
                onToggle={(key) => {
                  setScope((now) =>
                    now.includes(key)
                      ? now.filter((k) => k !== key)
                      : [...now, key],
                  );
                  ticks.unmark("scope", key);
                }}
              />
              {(extraction.scope_set_aside ?? []).length > 0 ? (
                <div className="flex flex-col gap-2 rounded-xl bg-muted/60 px-4 py-3 text-sm">
                  <span className="font-medium">
                    Mentioned in the document, but not asked for now (not
                    priced)
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
                    Add it under More options above if it should be built now.
                  </span>
                </div>
              ) : null}
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
          ) : question ? (
            <section className="flex flex-col gap-8">
              <QuestionHeading
                question={question}
                impact={impacts.get(question.key)}
                currency={currency}
              />
              {questionBlock(question, true)}
              {question.key === lastBuildQuestion && leveled.length > 0 ? (
                <button
                  type="button"
                  className="w-fit text-sm font-medium text-primary hover:underline"
                  onClick={() => {
                    setCustomizing(true);
                    steps.goTo("levels");
                  }}
                >
                  Want to set each feature&apos;s level yourself? Change levels
                  →
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
          ) : steps.current === "more" ? (
            <section className="flex flex-col gap-8">
              <StepHeader
                eyebrow="Optional"
                title="Anything different from the usual?"
              >
                What the document says shows its page; what it does not say is
                the usual answer. Change only what you know is different, or
                just continue.
              </StepHeader>
              {moreScreen()}
              <StepButtons
                onBack={steps.prev}
                onNext={steps.next}
                nextDisabled={
                  factsShown.some((f) => errors[f.key]) ||
                  staffHasErrors ||
                  unchosen(moreQuestions, choices).length > 0
                }
                hint={
                  factsShown.some((f) => errors[f.key]) || staffHasErrors
                    ? "Fix the highlighted numbers."
                    : unchosen(moreQuestions, choices).length > 0
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
                            step: "more",
                            label: "Staff during support",
                            value: staffSummary(staff),
                          },
                        ]
                      : []),
                    ...topicQuestions(t.key)
                      .filter(
                        (q) =>
                          mainQuestions.includes(q) ||
                          moreQuestions.includes(q),
                      )
                      .map((q) => ({
                        step: stepOf(q),
                        label: q.label,
                        value: answerLabel(q, choices[q.key]),
                      })),
                    ...topicFacts(t.key)
                      .filter((f) => (facts[f.key] ?? "").trim() !== "")
                      .map((f) => ({
                        step: "more",
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
                          <span className="text-muted-foreground">
                            {q.label}
                          </span>
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
                        The document asks for these. This estimate does not
                        price them, so check them yourself before you quote.
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
    </QuestionNotes.Provider>
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

function isUsersNumber(key: string): boolean {
  return (USERS_NUMBERS as readonly string[]).includes(key);
}
