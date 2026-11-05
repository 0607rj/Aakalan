"use client";

import { AppHero } from "@/components/app-hero";
import * as React from "react";
import { useRouter, useSearchParams } from "next/navigation";

import {
  ArrowRightIcon,
  CheckCircleIcon,
  FileArrowUpIcon,
  PencilSimpleLineIcon,
} from "@phosphor-icons/react/dist/ssr";

import { ErrorNotice, Loading } from "@/components/status";
import { Button } from "@/components/ui/button";
import {
  type Industry,
  type IndustrySuggestion,
  api,
  errorText,
  type NotIncluded,
  type QuickOptions,
  type QuickRequest,
  type Suggestion,
  type Template,
} from "@/lib/api/client";
import {
  currencySymbol,
  formatDate,
  monthsToWeeks,
  weeksToMonths,
} from "@/lib/format";
import { useLoad } from "@/lib/use-load";
import { cn } from "@/lib/utils";

import {
  NoReadyMadeNote,
  QuestionNotes,
  ReadyMadeNote,
  type Choice,
  FeatureCard,
  initialChoices,
  MANUAL_STEPS,
  TypeIcon,
  optionsCurrency,
  QuestionGroup,
  QuestionHeading,
  relevantQuestions,
  setChoice,
  shownChoice,
  StepIndicator,
  unchosen,
  useQuestionImpact,
  useSchedule,
  BuildTime,
  StepHeader,
  bandOf,
  readUsersNumber,
  SCALE,
  USERS_NUMBERS,
  type UsersNumber,
  UsersNumbers,
  usersNumbersValid,
  usersOverrides,
  missingPrerequisites,
  PrerequisiteWarnings,
} from "./parts";
import { Calculating } from "./calculating";
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
  AddOns,
  applicableScope,
  chosenScope,
  pickedLevels,
  presetFromFeatures,
  Progress,
  StepButtons,
  useSteps,
  VERSION,
  detailsTopics,
  topicSteps,
} from "./steps";
import {
  type CustomItem,
  itemsFromTemplate,
  toCustomFeatures,
} from "./custom-features";
import {
  FeatureChoice,
  FeatureSections,
  featureTicks,
  notIncludedText,
  sentNotIncluded,
} from "./feature-sections";
import { ReviewForm } from "./review";
import { UploadStep } from "./upload-step";

/** The longest deadline the form takes: five years (the engine's 60 months). */
const MAX_DEADLINE_WEEKS = 260;

/** The tick-box path (no document, or the document could not be read): one screen at a time. */
function ManualForm({
  options,
  documentId = null,
  initialName = "",
  notice = null,
  template = null,
  onBack,
}: {
  options: QuickOptions;
  documentId?: string | null;
  initialName?: string;
  notice?: string | null;
  template?: Template | null;
  onBack: () => void;
}) {
  const router = useRouter();
  const saved = (template?.request ?? null) as QuickRequest | null;
  const [name, setName] = React.useState(saved?.name ?? initialName);
  // a mobile app, other software and old data are questions, not tick boxes
  const hiddenKeys = new Set(
    options.features.filter((f) => f.hidden).map((f) => f.key),
  );
  const [features, setFeatures] = React.useState<string[]>(() =>
    (saved?.features ?? []).filter((k) => !hiddenKeys.has(k)),
  );
  // "What is it for?" (OPEN_QUESTIONS 212), optional: its popular features are offered on the
  // next screen; a template finds it again by its label. Click the tile again to unselect it.
  const [industry, setIndustry] = React.useState<string | null>(() => {
    if (!saved) return null;
    const found = options.industries?.find(
      (i) => i.label === saved.project_domain,
    );
    return found?.key ?? (saved.project_type ? OTHER_TYPE : null);
  });
  const chosenIndustry = options.industries?.find((i) => i.key === industry);
  // the old "which kind is closest?", asked under "Something else" only
  const [kindPick, setKindPick] = React.useState<string | null>(() =>
    saved?.project_type && saved.project_type !== OTHER_TYPE
      ? saved.project_type
      : null,
  );
  // the kind of software (order of the features, never the price): the industry's, else the
  // kind picked under "Something else", else "other"
  const projectType =
    chosenIndustry?.project_type ??
    (industry === OTHER_TYPE ? kindPick : null) ??
    OTHER_TYPE;
  // asked for in the description, but nothing this estimate can price
  const [notPriced, setNotPriced] = React.useState<string[]>([]);
  // features suggested from the user's own description: key -> the words that asked for it
  const [reasons, setReasons] = React.useState<Record<string, string>>({});
  // the industry the AI read from the description: shown only, never priced
  const [projectDomain, setProjectDomain] = React.useState("");
  // "usually needed for this kind of software", from the same reading (OPEN_QUESTIONS 207)
  const [industrySuggestions, setIndustrySuggestions] = React.useState<
    IndustrySuggestion[]
  >([]);
  const [suggestionsAsked, setSuggestionsAsked] = React.useState(false);
  // ready products are common for this kind of software (OPEN_QUESTIONS 209)
  const [readyMade, setReadyMade] = React.useState("");
  // parts of the words nothing matched (OPEN_QUESTIONS 210)
  const [unmatched, setUnmatched] = React.useState<string[]>([]);
  const [levels, setLevels] = React.useState<Record<string, Level>>(
    () => (saved?.feature_levels ?? {}) as Record<string, Level>,
  );
  const [customizing, setCustomizing] = React.useState(
    () => Object.keys(saved?.feature_levels ?? {}).length > 0,
  );
  const [customItems, setCustomItems] = React.useState<CustomItem[]>(() =>
    itemsFromTemplate(saved?.custom_features ?? []),
  );
  const [scope, setScope] = React.useState<string[]>(() => saved?.scope ?? []);
  // scope items suggested from the user's own description: key -> the words that asked for it
  const [scopeReasons, setScopeReasons] = React.useState<
    Record<string, string>
  >({});
  const customFeatures = toCustomFeatures(customItems);
  const [choices, setChoices] = React.useState<Record<string, Choice>>(() =>
    initialChoices(options.questions, {
      ...presetFromFeatures(options, saved?.features ?? []),
      ...(saved?.choices ?? {}),
    }),
  );
  const answered = React.useRef(
    new Set<string>(Object.keys(saved?.choices ?? {})),
  );
  // the answers the user gave; the rest print on the quote as assumed ("change if wrong")
  const [touched, setTouched] = React.useState<string[]>(
    () => saved?.answered ?? Object.keys(saved?.choices ?? {}),
  );
  // features, scope items and standard blocks marked "Not included"
  const [notIncluded, setNotIncluded] = React.useState<NotIncluded[]>(
    () => saved?.not_included ?? [],
  );
  // the users, people online at once and chatbot questions a day typed under the users
  // question (empty: what the band means), as on the review form (OPEN_QUESTIONS 182)
  const [usersNumbers, setUsersNumbers] = React.useState<
    Partial<Record<UsersNumber, string>>
  >(() =>
    Object.fromEntries(
      USERS_NUMBERS.filter((k) => saved?.overrides?.[k] !== undefined).map(
        (k) => [k, String(saved?.overrides?.[k])],
      ),
    ),
  );
  const usersValid = usersNumbersValid(usersNumbers);
  const overrides = {
    ...Object.fromEntries(
      Object.entries(saved?.overrides ?? {}).filter(
        ([k]) => !(USERS_NUMBERS as readonly string[]).includes(k),
      ),
    ),
    ...usersOverrides(usersNumbers),
  };
  const [deadline, setDeadline] = React.useState(
    saved?.deadline_months ? String(monthsToWeeks(saved.deadline_months)) : "",
  );
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  // the user's description, saved with the estimate so user stories can be drafted from it
  // on the results page (OPEN_QUESTIONS 174)
  const [description, setDescription] = React.useState(
    saved?.description ?? "",
  );

  // asked in weeks, priced in months
  const deadlineWeeks = deadline.trim() === "" ? null : Number(deadline);
  const deadlineValid =
    deadlineWeeks === null ||
    (Number.isInteger(deadlineWeeks) &&
      deadlineWeeks >= 1 &&
      deadlineWeeks <= MAX_DEADLINE_WEEKS);
  const typeDone = name.trim().length > 0;
  const kind = options.project_types.find((t) => t.key === projectType);
  const everything = allFeatures(options, features, choices);
  // a mobile app, other software or old data count too (ticked through their question)
  const canContinue =
    typeDone && (everything.length > 0 || customFeatures.length > 0);
  const leveled = featuresWithLevels(options, everything);
  const scopeGroups = applicableScope(options, everything);
  const effective = effectiveLevels(options, everything, choices, levels);
  const relevant = relevantQuestions(
    options.questions,
    choices,
    everything,
    customFeatures.map((c) => c.category),
  );
  const questions = relevant.filter((q) => q.group === "main");
  const details = relevant.filter((q) => q.group === "detail");
  // Like public cost calculators: what it is, one feature tick list and its extras, then the
  // questions one topic at a time (OPEN_QUESTIONS 177), the deadline with the contract.
  const questionSteps = topicSteps(
    options.topics,
    questions,
    details,
    customizing && leveled.length > 0 ? VERSION : null,
  );
  const stepKeys = ["type", "features", ...questionSteps, "check"];
  const detailsStepOf = (topic: string) =>
    questionSteps.find((k) => detailsTopics(k).includes(topic)) ?? "check";
  const steps = useSteps(stepKeys);
  // A refresh in the middle loses the answers: start again from the first screen.
  const current = !typeDone
    ? "type"
    : !canContinue && steps.current !== "type"
      ? "features"
      : steps.current;
  // Only levels picked by hand are sent; the rest follow the answers.
  const featureLevels = pickedLevels(options, everything, levels);
  const pricedScope = chosenScope(scopeGroups, scope);
  const ticks = featureTicks({
    options,
    features,
    setFeatures,
    everything,
    notIncluded,
    setNotIncluded,
  });
  const { unmark, toggleOut } = ticks;
  // a template keeps its stories (edited on the results page), for features still chosen
  const storyKeys = new Set([
    ...everything,
    ...customFeatures.map((c) => c.name),
  ]);
  const featureStories = Object.fromEntries(
    Object.entries(saved?.feature_stories ?? {}).filter(([k]) =>
      storyKeys.has(k),
    ),
  );
  const request: QuickRequest = {
    name: name.trim(),
    project_type: projectType,
    country: options.country,
    features,
    feature_levels: featureLevels,
    // a template keeps its features' module counts (only for features still ticked)
    feature_units: Object.fromEntries(
      Object.entries(saved?.feature_units ?? {}).filter(([k]) =>
        everything.includes(k),
      ),
    ),
    custom_features: customFeatures,
    choices,
    scope: pricedScope,
    deadline_months:
      deadlineValid && deadlineWeeks !== null
        ? weeksToMonths(deadlineWeeks)
        : null,
    document_id: documentId,
    overrides,
    mode: "vendor",
    // an answer may have added a feature marked not included (e.g. an app): it is priced
    not_included: sentNotIncluded(notIncluded, everything, pricedScope),
    answered: touched,
    feature_stories: featureStories,
    // kept so user stories can be drafted from it on the results page (never priced)
    description,
    // shown on the results page only, never priced
    project_domain: projectDomain || chosenIndustry?.label || "",
  };
  // the build time beside the deadline; the deadline itself does not change it
  const schedule = useSchedule(
    current === "deadline" && canContinue
      ? { ...request, deadline_months: null }
      : null,
  );
  const impacts = useQuestionImpact(
    (current.startsWith("q:") || current.startsWith("d:")) && canContinue
      ? request
      : null,
  );

  function change(key: string, value: Choice) {
    if (key === SCALE) {
      // a band the typed users are not in replaces them
      const typed = readUsersNumber(usersNumbers.users_total ?? "");
      const question = options.questions.find((q) => q.key === SCALE);
      if (
        typeof typed === "number" &&
        question &&
        bandOf(question, typed) !== value
      )
        setUsersNumbers((now) => ({ ...now, users_total: "" }));
    }
    choose(key, value);
  }

  function choose(key: string, value: Choice) {
    answered.current.add(key);
    setTouched((now) => (now.includes(key) ? now : [...now, key]));
    if (key === VERSION) setLevels({}); // a new overall level resets hand-picked ones
    setChoices((now) =>
      setChoice(options.questions, now, answered.current, key, value),
    );
  }
  const currency = optionsCurrency(options);

  const removedBlocks = notIncluded.filter((n) => n.kind === "standard");

  // features found in the description, with the words (ruled-out ones too, with theirs)
  const ruledOut = notIncluded.filter(
    (n) => n.kind === "feature" && n.quote !== "",
  );
  const foundKeys = [
    ...new Set([...Object.keys(reasons), ...ruledOut.map((n) => n.key)]),
  ].filter((k) => options.features.some((f) => f.key === k));
  const described = customItems.filter((i) => i.fromDescription !== undefined);

  /** One feature with its three states and the words behind it. */
  function card(key: string) {
    const out = notIncluded.find((n) => n.kind === "feature" && n.key === key);
    return (
      <FeatureChoice
        key={key}
        options={options}
        featureKey={key}
        ticks={ticks}
        onTick={(k) => ticks.tick(k, change)}
        notIncluded={notIncluded}
      >
        <FromWords quote={reasons[key]} />
        <RuledOutBecause quote={out?.quote} />
      </FeatureChoice>
    );
  }

  /** Pick what it is for (OPEN_QUESTIONS 212): the industry's main features are ticked (the
   * user can untick them); a different industry unticks the previous one's. */
  function pickIndustry(picked: Industry) {
    // the same tile again: unselect it (and untick its main features)
    const next = picked.key === industry ? null : picked;
    setIndustry(next?.key ?? null);
    const mainOf = (ind: Industry | undefined) =>
      (ind?.suggestions ?? []).filter((s) => ind?.ticked.includes(s.label));
    const before = mainOf(chosenIndustry);
    const after = mainOf(next ?? undefined);
    const drop = new Set(before.map((s) => s.feature).filter(Boolean));
    setFeatures((now) => [
      ...new Set([
        ...now.filter((k) => !drop.has(k)),
        ...after.map((s) => s.feature).filter((k) => k && !hiddenKeys.has(k)),
      ]),
    ]);
    const isModule = (list: IndustrySuggestion[], item: CustomItem) =>
      item.suggested !== undefined &&
      list.some((s) => !s.feature && s.label === item.name);
    setCustomItems((now) => {
      const kept = now.filter((i) => !isModule(before, i));
      return [
        ...kept,
        ...after
          .filter((s) => !s.feature)
          .filter(
            (s) =>
              !kept.some(
                (i) => i.suggested !== undefined && i.name === s.label,
              ),
          )
          .map((s) => ({
            id: `suggested-custom:${s.label.toLowerCase()}`,
            name: s.label,
            category: s.category,
            size: (s.size || "M") as CustomItem["size"],
            foundIndex: null,
            description: s.why,
            evidence: [],
            included: true,
            suggested: s.why,
            catalogKey: s.catalog_key || null,
          })),
      ];
    });
  }

  async function submit() {
    setSubmitting(true);
    setError(null);
    try {
      const summary = await api.createQuickEstimate(request);
      router.push(`/estimate/${summary.estimate_id}`);
    } catch (e) {
      setError(errorText(e));
      setSubmitting(false);
    }
  }

  if (submitting)
    return <Calculating labels={MANUAL_STEPS} name={name.trim()} />;

  const questionNotes = readyMade
    ? { build_type: <ReadyMadeNote note={readyMade} /> }
    : suggestionsAsked
      ? { build_type: <NoReadyMadeNote /> }
      : {};

  const question = current.startsWith("q:")
    ? questions.find((q) => `q:${q.key}` === current)
    : undefined;
  const phase = ["type", "features", "levels"].includes(current) ? 1 : 2;

  return (
    <QuestionNotes.Provider value={questionNotes}>
      <div className="flex flex-col gap-8">
        <StepIndicator labels={MANUAL_STEPS} current={phase} />
        <Progress
          index={Math.max(0, stepKeys.indexOf(current))}
          total={steps.total}
        />
        <ErrorNotice message={notice} />

        <div key={current} className="step-in flex flex-col gap-8">
          {current === "type" ? (
            <section className="flex flex-col gap-8">
              <header className="app-head step-head settle flex flex-col gap-2">
                <div aria-hidden="true" className="app-head-grid" />
                <p className="eyebrow">New estimate</p>
                <h1 className="font-wide text-[2rem] leading-tight sm:text-[2.5rem]">
                  What do you want to build?
                </h1>
                <p className="max-w-2xl text-muted-foreground">
                  Name it and pick what it is for. Next, you see the features
                  that kind of software usually has.
                </p>
              </header>

              <label className="flex flex-col gap-2">
                <span className="eyebrow">Name</span>
                <input
                  id="project-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Booking app for a clinic"
                  autoComplete="off"
                  className="font-wide w-full border-b-2 border-foreground/15 bg-transparent pb-2 text-2xl transition-colors placeholder:text-muted-foreground/50 focus:border-tape focus:outline-none sm:text-3xl"
                />
                <span className="text-xs text-muted-foreground">
                  Only for you, to find it again in your list.
                </span>
              </label>

              <div className="flex flex-col gap-3">
                <span className="eyebrow">What is it for?</span>
                <div
                  role="radiogroup"
                  aria-label="What the software is for"
                  className="grid grid-cols-1 overflow-hidden rounded-3xl bg-card shadow-[0_1px_2px_rgb(0_0_0/0.05),0_18px_40px_-24px_rgb(0_0_0/0.28)] sm:grid-cols-2 lg:grid-cols-3"
                >
                  {[
                    ...(options.industries ?? []),
                    {
                      key: OTHER_TYPE,
                      label: "Something else",
                      tag: "",
                      hint: "Any other kind of software: every feature to choose from",
                      project_type: OTHER_TYPE,
                      suggestions: [],
                      ticked: [],
                    },
                  ].map((t, i) => {
                    const active = t.key === industry;
                    const count =
                      t.suggestions.length > 0
                        ? `${t.suggestions.length} popular features`
                        : "Every feature to choose from";
                    return (
                      <button
                        key={t.key}
                        type="button"
                        role="radio"
                        aria-checked={active}
                        onClick={() => pickIndustry(t)}
                        className={cn(
                          "group relative flex flex-col gap-2 border-foreground/10 p-5 text-left transition-colors focus-visible:bg-panel-2 focus-visible:outline-none sm:p-6",
                          // inner rules of the grid: a line above every row but the first
                          i > 0 && "border-t",
                          i === 1 && "sm:border-t-0",
                          i === 2 && "lg:border-t-0",
                          i % 2 === 1 && "sm:border-l lg:border-l-0",
                          i % 3 !== 0 && "lg:border-l",
                          active ? "bg-tape-soft/60" : "hover:bg-panel-2",
                        )}
                      >
                        {active ? (
                          <span
                            aria-hidden="true"
                            className="absolute inset-x-0 top-0 h-0.5 bg-tape"
                          />
                        ) : null}
                        <span className="flex items-start justify-between gap-3">
                          <span className="text-tape">
                            <TypeIcon kind={t.key} />
                          </span>
                          <CheckCircleIcon
                            size={20}
                            weight="fill"
                            aria-hidden="true"
                            className={cn(
                              "text-tape transition-opacity",
                              active ? "opacity-100" : "opacity-0",
                            )}
                          />
                        </span>
                        <span className="flex flex-wrap items-baseline gap-x-2">
                          <span className="font-semibold">{t.label}</span>
                          {t.tag ? (
                            <span className="font-mono text-xs text-muted-foreground">
                              {t.tag}
                            </span>
                          ) : null}
                        </span>
                        <span className="text-sm text-muted-foreground">
                          {t.hint}
                        </span>
                        <span className="mt-auto pt-2 font-mono text-xs text-muted-foreground">
                          {count}
                        </span>
                      </button>
                    );
                  })}
                </div>
                {chosenIndustry ? (
                  <p className="settle flex flex-wrap items-baseline gap-x-3 gap-y-1 border-t pt-4 text-sm text-muted-foreground">
                    <span className="eyebrow">Popular</span>
                    {chosenIndustry.suggestions.map((s) => s.label).join(" · ")}
                  </p>
                ) : industry === OTHER_TYPE ? (
                  <div className="settle flex flex-col gap-2 border-t pt-4">
                    <span className="eyebrow">
                      Which is closest? (optional)
                    </span>
                    <div className="flex flex-wrap gap-2">
                      {options.project_types
                        .filter((t) => t.key !== OTHER_TYPE)
                        .map((t) => (
                          <button
                            key={t.key}
                            type="button"
                            aria-pressed={kindPick === t.key}
                            title={t.hint}
                            onClick={() =>
                              setKindPick((now) =>
                                now === t.key ? null : t.key,
                              )
                            }
                            className={cn(
                              "rounded-full border px-3 py-1 text-sm transition-colors",
                              kindPick === t.key
                                ? "border-tape bg-tape-soft font-medium text-primary"
                                : "hover:bg-panel-2",
                            )}
                          >
                            {t.label}
                          </button>
                        ))}
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground">
                    Optional: click a tile again to unselect it. You can also
                    describe it on the next screen and the AI finds the
                    features.
                  </p>
                )}
              </div>
              <StepButtons
                onBack={onBack}
                onNext={steps.next}
                nextDisabled={!typeDone}
                hint={typeDone ? null : "Enter a name to continue."}
              />
            </section>
          ) : current === "features" ? (
            <section className="flex flex-col gap-8">
              <StepHeader eyebrow="Features" title="What should it do?">
                Describe it and we find the features, or tick them yourself.
                Each feature can be ticked, left out, or marked not included.
              </StepHeader>
              <DescribeBox
                onText={setDescription}
                onSuggested={(s) => {
                  const tickable = new Set(
                    options.features.filter((f) => !f.hidden).map((f) => f.key),
                  );
                  const keys = s.features.map((f) => f.key);
                  setReasons(
                    Object.fromEntries(s.features.map((f) => [f.key, f.quote])),
                  );
                  setNotPriced(s.not_priced ?? []);
                  setProjectDomain(s.project_domain ?? "");
                  setIndustrySuggestions(s.industry_suggestions ?? []);
                  setSuggestionsAsked(s.industry_suggestions_asked ?? false);
                  setReadyMade(s.ready_made?.note ?? "");
                  setUnmatched(s.unmatched ?? []);
                  // what the words rule out ("no mobile app"): marked not included
                  const out: NotIncluded[] = [
                    ...(s.excluded ?? []).map((f) => ({
                      kind: "feature" as const,
                      key: f.key,
                      quote: f.quote,
                    })),
                    ...(s.excluded_scope ?? []).map((i) => ({
                      kind: "scope" as const,
                      key: i.key,
                      quote: i.quote,
                    })),
                  ];
                  const outKeys = new Set(out.map((o) => o.key));
                  // a new reading replaces the previous one's ticks (the user's own stay)
                  const before = new Set(Object.keys(reasons));
                  setFeatures((now) => [
                    ...new Set([
                      ...now.filter(
                        (k) =>
                          !outKeys.has(k) &&
                          !(before.has(k) && !keys.includes(k)),
                      ),
                      ...keys.filter((k) => tickable.has(k)),
                    ]),
                  ]);
                  // a mobile app, other software or old data: answer those questions
                  const implied: Record<string, Choice> = {
                    ...presetFromFeatures(
                      options,
                      keys.filter((k) => !tickable.has(k)),
                    ),
                    ...s.choices,
                  };
                  // one ruled out that an answer adds (an app): the answer without it
                  for (const o of out) {
                    if (o.kind !== "feature" || tickable.has(o.key)) continue;
                    const q = options.questions.find((x) =>
                      x.options.some(
                        (opt) => o.key in (opt.add_features ?? {}),
                      ),
                    );
                    const keep = q?.options.find(
                      (opt) =>
                        !(o.key in (opt.add_features ?? {})) && !opt.unsure,
                    );
                    if (q && keep) implied[q.key] = keep.value;
                  }
                  for (const key of Object.keys(implied))
                    answered.current.add(key);
                  setTouched((now) => [
                    ...new Set([...now, ...Object.keys(implied)]),
                  ]);
                  setChoices((now) => ({ ...now, ...implied }));
                  setScope((now) => now.filter((k) => !outKeys.has(k)));
                  setNotIncluded((now) => [
                    ...now.filter((n) => !outKeys.has(n.key)),
                    ...out,
                  ]);
                  const items = s.scope ?? [];
                  setScopeReasons(
                    Object.fromEntries(
                      items.map((i) => [
                        i.key,
                        i.status === "explicit"
                          ? i.quote
                          : `${i.quote} (may be needed: please check)`,
                      ]),
                    ),
                  );
                  // not in our list: priced as the user's own features, shown under "Found"
                  setCustomItems((now) => [
                    ...now.filter((i) => i.fromDescription === undefined),
                    ...s.other_features.map((o, i) => ({
                      id: `described-${Date.now()}-${i}`,
                      name: o.name,
                      category: o.category,
                      size: o.size as "S" | "M" | "L",
                      foundIndex: null,
                      description: o.description,
                      evidence: [],
                      included: true,
                      fromDescription: o.evidence[0]?.quote ?? o.name,
                    })),
                  ]);
                }}
              />

              <FeatureSections
                options={options}
                foundTitle="Found in your description"
                foundKeys={foundKeys}
                foundCount={foundKeys.length + described.length}
                found={
                  <>
                    {foundKeys.map((key) => card(key))}
                    {described.map((item) => (
                      <FeatureCard
                        key={item.id}
                        label={item.name}
                        hint="Custom: priced from a general size estimate, less certain"
                        checked={item.included}
                        onToggle={() =>
                          setCustomItems((now) =>
                            now.map((i) =>
                              i.id === item.id
                                ? { ...i, included: !i.included }
                                : i,
                            ),
                          )
                        }
                      >
                        <FromWords quote={item.fromDescription} />
                      </FeatureCard>
                    ))}
                  </>
                }
                foundNote={
                  <>
                    <Unmatched
                      parts={unmatched}
                      onAdd={(part) => {
                        setUnmatched((now) => now.filter((p) => p !== part));
                        setCustomItems((now) => [
                          ...now,
                          {
                            id: `unmatched-${Date.now()}`,
                            name: part.charAt(0).toUpperCase() + part.slice(1),
                            category:
                              options.custom_feature_types[0]?.key ?? "",
                            size: "M",
                            foundIndex: null,
                            description: part,
                            evidence: [],
                            included: true,
                            fromDescription: part,
                          },
                        ]);
                      }}
                    />
                    {notPriced.length > 0 ? (
                      <div className="rounded-xl border border-dashed px-4 py-3 text-sm">
                        <span className="font-medium">
                          Asked for, but not priced by this estimate:
                        </span>{" "}
                        {notPriced.join(", ")}. Price these separately if they
                        are needed.
                      </div>
                    ) : null}
                    <PrerequisiteWarnings
                      items={missingPrerequisites(
                        options,
                        everything,
                        Object.keys(scopeReasons),
                        Object.fromEntries(
                          touched.flatMap((k) =>
                            k in choices ? [[k, choices[k]]] : [],
                          ),
                        ),
                      )}
                    />
                  </>
                }
                emptyHint="Describe your project to find features, or browse all below."
                card={card}
                isTicked={ticks.isTicked}
                kindFeatures={kind?.features ?? []}
                blocksBody={
                  typeDone
                    ? { ...request, not_included: [], answered: null }
                    : null
                }
                removedBlocks={removedBlocks.map((n) => n.key)}
                onToggleBlock={(key) => toggleOut("standard", key)}
                customItems={customItems}
                onCustomItems={setCustomItems}
                // the industry's list, then what the AI adds from a description (no repeats)
                suggestions={withAiSuggestions(
                  chosenIndustry?.suggestions ?? [],
                  industrySuggestions,
                )}
                domain={chosenIndustry?.label || projectDomain || ""}
                fromIndustry={chosenIndustry !== undefined}
                levels={effective}
                onLevel={(key, level) =>
                  setLevels((now) => ({ ...now, [key]: level }))
                }
                suggestionsAsked={suggestionsAsked}
                onTick={(k) => ticks.tick(k, change)}
              />

              <AddOns
                groups={scopeGroups}
                chosen={scope}
                suggested={Object.keys(scopeReasons)}
                notIncluded={notIncluded
                  .filter((n) => n.kind === "scope")
                  .map((n) => n.key)}
                onToggle={(key) => {
                  setScope((now) =>
                    now.includes(key)
                      ? now.filter((k) => k !== key)
                      : [...now, key],
                  );
                  unmark("scope", key);
                }}
              />

              <StepButtons
                onBack={steps.prev}
                onNext={steps.next}
                nextDisabled={!canContinue}
                hint={
                  canContinue
                    ? `${everything.length + customFeatures.length} selected`
                    : "Tick or add at least one feature to continue."
                }
              />
            </section>
          ) : current === "levels" ? (
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
            <section className="flex flex-col gap-6">
              <QuestionHeading
                question={question}
                impact={impacts.get(question.key)}
                currency={currency}
              />
              <QuestionGroup
                question={question}
                value={shownChoice(question, choices)}
                impact={impacts.get(question.key)}
                currency={currency}
                hideLegend
                compact={question.key === SCALE}
                onChange={(value) => change(question.key, value)}
              />
              {question.key === SCALE ? (
                <UsersNumbers
                  question={question}
                  band={choices[question.key] ?? question.default}
                  values={usersNumbers}
                  chatbot={everything.includes("ai_chatbot")}
                  onChange={(key, text) => {
                    setUsersNumbers((now) => ({ ...now, [key]: text }));
                    const n = readUsersNumber(text);
                    const band =
                      typeof n === "number" ? bandOf(question, n) : undefined;
                    if (key === "users_total" && band !== undefined)
                      choose(SCALE, band); // the band the typed users fall in
                  }}
                />
              ) : null}
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
                nextDisabled={
                  unchosen([question], choices).length > 0 ||
                  (question.key === SCALE && !usersValid)
                }
                hint={
                  unchosen([question], choices).length > 0
                    ? "Pick an answer to continue."
                    : null
                }
              />
            </section>
          ) : current.startsWith("d:") ? (
            <>
              <DetailsStep
                sections={options.topics
                  .filter((t) => detailsTopics(current).includes(t.key))
                  .map((topic) => ({
                    topic,
                    questions: details.filter((q) => q.topic === topic.key),
                  }))}
                choices={choices}
                onChange={change}
                impacts={impacts}
                currency={currency}
              />
              <StepButtons onBack={steps.prev} onNext={steps.next} />
            </>
          ) : current === "deadline" ? (
            <section className="flex flex-col gap-8">
              <StepHeader eyebrow="Optional" title="Is there a deadline?">
                A tight deadline needs a bigger team, which costs more. Leave it
                empty if there is no fixed date.
              </StepHeader>
              <div className="flex flex-col gap-2">
                <label htmlFor="deadline" className="eyebrow">
                  Weeks from start to launch
                </label>
                <div className="flex items-baseline gap-3">
                  <input
                    id="deadline"
                    type="number"
                    inputMode="numeric"
                    min={1}
                    max={MAX_DEADLINE_WEEKS}
                    value={deadline}
                    onChange={(e) => setDeadline(e.target.value)}
                    placeholder="None"
                    className="font-wide w-32 border-b-2 border-foreground/15 bg-transparent pb-1 text-3xl tabular-nums transition-colors placeholder:text-muted-foreground/50 focus:border-tape focus:outline-none"
                  />
                  <span className="text-muted-foreground">weeks</span>
                </div>
                {!deadlineValid ? (
                  <span className="text-sm text-destructive">
                    Enter a whole number of weeks between 1 and{" "}
                    {MAX_DEADLINE_WEEKS}.
                  </span>
                ) : null}
              </div>
              <BuildTime
                plan={schedule}
                weeks={deadlineValid ? deadlineWeeks : null}
                keepTeam="this estimate does not include them: upload the requirement document so its staff lines are priced."
              />
              <StepButtons
                onBack={steps.prev}
                onNext={steps.next}
                nextDisabled={!deadlineValid}
              />
            </section>
          ) : (
            <>
              <CheckStep
                rows={[
                  { step: "type", label: "Project name", value: name.trim() },
                  {
                    step: "type",
                    label: "Kind of software",
                    value: kind?.label ?? "—",
                  },
                  {
                    step: "features",
                    label: "Features",
                    value: featureSummary(
                      options,
                      everything,
                      effective,
                      customFeatures.map((c) => c.name),
                    ),
                  },
                  {
                    step: "features",
                    label: "Not included",
                    value: notIncludedText(options, notIncluded),
                  },
                  // the answers in the order asked: one topic at a time
                  ...options.topics.flatMap((topic) => [
                    ...questions
                      .filter((q) => q.topic === topic.key)
                      .flatMap((q) => [
                        {
                          step: `q:${q.key}`,
                          label: q.label,
                          value: answerLabel(q, choices[q.key]),
                        },
                        ...(q.key === SCALE
                          ? Object.entries(usersOverrides(usersNumbers)).map(
                              ([k, n]) => ({
                                step: `q:${SCALE}`,
                                label: USERS_LABELS[k as UsersNumber],
                                value: n.toLocaleString("en-IN"),
                              }),
                            )
                          : []),
                      ]),
                    ...details
                      .filter((q) => q.topic === topic.key)
                      .map((q) => ({
                        step: detailsStepOf(topic.key),
                        label: q.label,
                        value: answerLabel(q, choices[q.key]),
                      })),
                    ...(topic.key === "contract"
                      ? [
                          {
                            step: "deadline",
                            label: "Deadline",
                            value: deadlineWeeks
                              ? `${deadlineWeeks} weeks`
                              : "None",
                          },
                        ]
                      : []),
                  ]),
                ]}
                onChange={steps.goTo}
              />
              <ErrorNotice message={error} />
              <StepButtons
                onBack={steps.prev}
                onNext={submit}
                nextLabel="Calculate my cost"
                nextDisabled={
                  !deadlineValid || unchosen(questions, choices).length > 0
                }
                hint={
                  unchosen(questions, choices).length > 0
                    ? `Answer: ${unchosen(questions, choices)[0].label}`
                    : null
                }
              />
            </>
          )}
        </div>
      </div>
    </QuestionNotes.Provider>
  );
}

/** A few lines about the software -> features ticked for the user to check. */
function DescribeBox({
  onSuggested,
  onText,
}: {
  onSuggested: (s: Suggestion) => void;
  onText: (text: string) => void;
}) {
  const [text, setText] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const ready = text.trim().length >= MIN_DESCRIPTION;

  async function suggest() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const s = await api.suggestFeatures(text.trim());
      onSuggested(s);
      const found = s.features.length + s.other_features.length;
      setMessage(
        (found === 0
          ? "We could not match any feature to this. Please tick them below."
          : `We found ${found} feature${found === 1 ? "" : "s"} in your description. Check them below and add anything missing.`) +
          (s.note ? ` ${s.note}` : ""),
      );
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <label htmlFor="describe" className="eyebrow">
        Describe it in your own words
      </label>
      <div className="overflow-hidden rounded-xl border bg-card transition-colors focus-within:border-tape">
        <textarea
          id="describe"
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            onText(e.target.value);
          }}
          rows={3}
          maxLength={4000}
          placeholder="e.g. An app for my clinic where patients book an appointment with a doctor, pay the fee online and get an SMS reminder."
          className="block w-full resize-y bg-transparent px-5 py-4 text-base focus:outline-none"
        />
        <div className="flex flex-wrap items-center gap-3 border-t bg-panel-2/60 px-5 py-3">
          <Button onClick={suggest} disabled={!ready || busy}>
            {busy ? "Reading…" : "Find features"}
          </Button>
          <span className="text-sm text-muted-foreground">
            We only tick features; you can untick them or add others yourself.
          </span>
        </div>
      </div>
      {message ? <p className="text-sm">{message}</p> : null}
      <ErrorNotice message={error} />
    </div>
  );
}

/** Under a feature found in the description: the user's words it came from. */
/** Parts of the description nothing matched (OPEN_QUESTIONS 210): one click adds each as the
 * user's own feature, so nothing they asked for is lost silently. */
function Unmatched({
  parts,
  onAdd,
}: {
  parts: string[];
  onAdd: (part: string) => void;
}) {
  if (parts.length === 0) return null;
  return (
    <div className="flex flex-col gap-2 rounded-xl border border-warning/40 bg-warning-muted px-4 py-3 text-sm">
      <span className="font-medium text-warning">
        Not matched to a feature yet, so not in the price:
      </span>
      <ul className="flex flex-col gap-2">
        {parts.map((part) => (
          <li
            key={part}
            className="flex flex-wrap items-center gap-x-3 gap-y-1"
          >
            <span>&ldquo;{part}&rdquo;</span>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-7"
              onClick={() => onAdd(part)}
            >
              Add as my own feature
            </Button>
          </li>
        ))}
      </ul>
    </div>
  );
}

function FromWords({ quote }: { quote?: string }) {
  if (!quote) return null;
  return <span className="text-sm text-primary">from: “{quote}”</span>;
}

/** Under a feature marked not included from the description: the words that ruled it out. */
function RuledOutBecause({ quote }: { quote?: string }) {
  if (!quote) return null;
  return (
    <span className="text-sm text-muted-foreground">
      Marked not included because you wrote: “{quote}”
    </span>
  );
}

const MIN_DESCRIPTION = 10; // characters, as the API requires

/** The numbers typed under the users question, as listed on the check step. */
const USERS_LABELS: Record<UsersNumber, string> = {
  users_total: "Exact number of users",
  peak_concurrent_users: "People online at the same time",
  chatbot_queries_per_day: "Chatbot questions a day",
};

/** The "Something else" kind: every feature, nothing ticked to start with. */
const OTHER_TYPE = "other";

/** The industry's list first, then the AI's suggestions it does not have (the same feature, or
 * a module of the same name, once), OPEN_QUESTIONS 212. */
function withAiSuggestions(
  fromIndustry: IndustrySuggestion[],
  fromAi: IndustrySuggestion[],
): IndustrySuggestion[] {
  const id = (s: IndustrySuggestion) => s.feature || s.label.toLowerCase();
  const seen = new Set(fromIndustry.map(id));
  return [...fromIndustry, ...fromAi.filter((s) => !seen.has(id(s)))];
}

function CountryChoice({
  options,
  onChange,
}: {
  options: QuickOptions;
  onChange: (country: string) => void;
}) {
  if (options.countries.length < 2) return null; // only one country switched on
  return (
    <div className="flex flex-col gap-2">
      <span className="text-sm font-medium">Where is the client?</span>
      <div
        role="radiogroup"
        aria-label="Country"
        className="inline-flex w-fit rounded-xl border bg-card p-1"
      >
        {options.countries.map((c) => {
          const active = c.key === options.country;
          return (
            <button
              key={c.key}
              type="button"
              role="radio"
              aria-checked={active}
              onClick={() => onChange(c.key)}
              className={cn(
                "rounded-lg px-4 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted",
              )}
            >
              {c.label}{" "}
              <span className="opacity-70">({currencySymbol(c.currency)})</span>
            </button>
          );
        })}
      </div>
      <span className="text-sm text-muted-foreground">
        Prices, taxes and hosting options follow the country.
      </span>
    </div>
  );
}

/** What happens after choosing, as ruled columns (as on "Your estimates"). */
const START_STEPS = [
  {
    title: "Upload or describe",
    text: "A PDF or Word requirement document, or a few lines about what the software should do.",
  },
  {
    title: "Check and answer",
    text: "Untick anything wrong, add anything missing, and answer a few short questions.",
  },
  {
    title: "See your cost",
    text: "Low, likely and high, feature by feature, with the team it needs.",
  },
];

function StartChoice({
  options,
  onCountry,
  onUpload,
  onManual,
  onTemplate,
}: {
  options: QuickOptions;
  onCountry: (country: string) => void;
  onUpload: () => void;
  onManual: () => void;
  onTemplate: (id: string) => void;
}) {
  const ways = [
    {
      key: "upload",
      onClick: onUpload,
      icon: FileArrowUpIcon,
      title: "Upload the requirement document",
      text: "PDF or Word. We read it and fill in the details for you to check.",
      points: [
        "Every feature found keeps the page and sentence it came from",
        "A corrigendum overrides the original",
        "You check what was found before any price is worked out",
      ],
      recommended: true,
    },
    {
      key: "manual",
      onClick: onManual,
      icon: PencilSimpleLineIcon,
      title: "No document? Describe it yourself",
      text: "A few lines about the software, or tick what it should do.",
      points: [
        "Write a few lines and the features you mean are ticked",
        "Or pick what it is for and tick from its usual features",
        "Choose basic, standard or advanced for each one",
      ],
      recommended: false,
    },
  ];
  return (
    <section className="flex flex-col gap-8">
      <AppHero>
        <header className="settle flex flex-col gap-3">
          <p className="eyebrow">New estimate</p>
          <h1 className="font-display text-[clamp(2.4rem,5.5vw,3.75rem)] leading-[1]">
            How would you like to start?
          </h1>
          <p className="max-w-xl text-muted-foreground">
            The quickest way is to upload the requirement document.
          </p>
        </header>
      </AppHero>

      <CountryChoice options={options} onChange={onCountry} />

      <div className="settle grid grid-cols-1 overflow-hidden rounded-3xl bg-card shadow-[0_1px_2px_rgb(0_0_0/0.05),0_18px_40px_-24px_rgb(0_0_0/0.28)] sm:grid-cols-2">
        {ways.map((way, i) => (
          <button
            key={way.key}
            type="button"
            onClick={way.onClick}
            className={cn(
              "group flex items-start gap-4 p-5 text-left transition-colors hover:bg-panel-2 focus-visible:bg-panel-2 focus-visible:outline-none sm:p-6",
              i > 0 && "border-t sm:border-t-0 sm:border-l",
            )}
          >
            <way.icon
              size={22}
              weight="duotone"
              aria-hidden="true"
              className="mt-0.5 shrink-0 text-tape"
            />
            <span className="flex min-w-0 flex-1 flex-col gap-1">
              <span className="flex flex-wrap items-center gap-2 font-semibold">
                {way.title}
                {way.recommended ? (
                  <span className="rounded-full bg-tape-soft px-2 py-0.5 text-xs font-semibold text-primary">
                    Recommended
                  </span>
                ) : null}
              </span>
              <span className="text-sm text-muted-foreground">{way.text}</span>
              <ul className="mt-2 flex flex-col gap-1.5">
                {way.points.map((point) => (
                  <li
                    key={point}
                    className="flex items-start gap-2 text-sm text-foreground/80"
                  >
                    <CheckCircleIcon
                      size={16}
                      weight="fill"
                      aria-hidden="true"
                      className="mt-0.5 shrink-0 text-tape"
                    />
                    {point}
                  </li>
                ))}
              </ul>
            </span>
            <ArrowRightIcon
              size={18}
              weight="bold"
              aria-hidden="true"
              className="mt-0.5 shrink-0 text-muted-foreground transition-[transform,color] group-hover:translate-x-1 group-hover:text-tape"
            />
          </button>
        ))}
      </div>

      <SavedTemplates onUse={onTemplate} />

      <section className="flex flex-col gap-6 pt-2">
        <p className="eyebrow">What happens next</p>
        <ol className="grid grid-cols-1 gap-8 sm:grid-cols-3">
          {START_STEPS.map((step, i) => (
            <li
              key={step.title}
              className="flex flex-col gap-2 border-t-2 border-foreground/10 pt-5 first:border-tape"
            >
              <span className="font-mono text-sm text-muted-foreground">
                0{i + 1}
              </span>
              <span className="font-wide text-lg">{step.title}</span>
              <span className="text-sm text-muted-foreground">{step.text}</span>
            </li>
          ))}
        </ol>
      </section>
    </section>
  );
}

/**
 * Where the wizard is lives in the web address, not in memory:
 *   /estimate/new              -> choose upload or manual
 *   /estimate/new?via=upload   -> upload the requirement document
 *   /estimate/new?via=manual   -> tick-box form, one screen per step (&step=<key>)
 *   /estimate/new?doc=<id>     -> review what was found in an uploaded document
 * So the browser Back button moves one step back, a refresh keeps the place, and
 * "Start a new estimate" (/estimate/new) always begins fresh.
 */
function Flow({ options }: { options: QuickOptions }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const via = searchParams.get("via");
  const docId = searchParams.get("doc");
  const country = options.country;

  /** Every step keeps the chosen country in the web address. */
  function go(params: Record<string, string>) {
    const query = new URLSearchParams(params);
    if (country !== "india") query.set("country", country);
    const qs = query.toString();
    router.push(qs ? `/estimate/new?${qs}` : "/estimate/new", { scroll: true });
  }
  /** One step back: to wherever the person came from (the home cards skip the start choice). */
  const toStart = () => {
    if (window.history.length > 1) router.back();
    else go({});
  };

  if (docId)
    return (
      <ReviewStep
        key={docId}
        options={options}
        docId={docId}
        onBack={toStart}
      />
    );
  if (via === "upload")
    return (
      <UploadStep onUploaded={(doc) => go({ doc: doc.id })} onBack={toStart} />
    );
  const templateId = searchParams.get("template");
  if (via === "manual" && templateId)
    return (
      <TemplateStep
        key={templateId}
        options={options}
        templateId={templateId}
        onBack={toStart}
      />
    );
  if (via === "manual")
    return <ManualForm key="manual" options={options} onBack={toStart} />;
  return (
    <StartChoice
      options={options}
      onCountry={(next) => {
        const query = next === "india" ? "" : `?country=${next}`;
        router.replace(`/estimate/new${query}`, { scroll: false });
      }}
      onUpload={() => go({ via: "upload" })}
      onManual={() => go({ via: "manual" })}
      onTemplate={(id) => go({ via: "manual", template: id })}
    />
  );
}

/** Start a new estimate from a saved template (loaded by id, so a refresh keeps it). */
function TemplateStep({
  options,
  templateId,
  onBack,
}: {
  options: QuickOptions;
  templateId: string;
  onBack: () => void;
}) {
  const loader = React.useCallback(
    () => api.getTemplate(templateId),
    [templateId],
  );
  const { state } = useLoad(loader);
  if (state.kind === "loading")
    return <Loading fullPage>Opening your template…</Loading>;
  if (state.kind === "error") return <ErrorNotice message={state.message} />;
  return (
    <ManualForm
      options={options}
      template={state.data}
      notice={`Started from the template "${state.data.name}". Change anything you need, then calculate.`}
      onBack={onBack}
    />
  );
}

/** Saved templates on the start page: use one, or delete it. */
function SavedTemplates({ onUse }: { onUse: (id: string) => void }) {
  const loader = React.useCallback(() => api.listTemplates(), []);
  const { state, reload } = useLoad(loader);
  if (state.kind !== "ready" || state.data.length === 0) return null;
  async function remove(id: string, name: string) {
    const question = `Delete the template "${name}"? Estimates made from it are kept.`;
    if (!window.confirm(question)) return;
    try {
      await api.deleteTemplate(id);
      reload();
    } catch (e) {
      window.alert(errorText(e));
    }
  }
  return (
    <section className="flex flex-col gap-3">
      <p className="eyebrow">Or start from a saved template</p>
      <ul className="flex flex-col divide-y border-y">
        {state.data.map((t) => (
          <li
            key={t.id}
            className="flex flex-wrap items-center justify-between gap-3 py-3"
          >
            <span className="flex flex-col">
              <span className="font-medium">{t.name}</span>
              <span className="text-sm text-muted-foreground">
                {t.features.length + t.extra_features} features · saved{" "}
                {formatDate(t.created_at)}
              </span>
            </span>
            <span className="flex gap-2">
              <Button size="sm" onClick={() => onUse(t.id)}>
                Use
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => remove(t.id, t.name)}
              >
                Delete
              </Button>
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** Review an uploaded document (loaded by id, so a page refresh keeps it). */
function ReviewStep({
  options,
  docId,
  onBack,
}: {
  options: QuickOptions;
  docId: string;
  onBack: () => void;
}) {
  // the document, and the form pre-filled from its reading (the backend's, so the
  // back-test prices what this form sends)
  const loader = React.useCallback(async () => {
    const doc = await api.getDocument(docId);
    const read = doc.status === "extracted" && doc.extraction !== null;
    const form = read ? await api.reviewForm(docId, options.country) : null;
    return { doc, form };
  }, [docId, options.country]);
  const { state } = useLoad(loader);
  if (state.kind === "loading")
    return <Loading fullPage>Opening your document…</Loading>;
  if (state.kind === "error") return <ErrorNotice message={state.message} />;
  const { doc, form } = state.data;
  if (doc.status !== "extracted" || !doc.extraction || !form) {
    return (
      <ManualForm
        options={options}
        documentId={doc.id}
        initialName={doc.project_name}
        onBack={onBack}
        notice={
          doc.error
            ? `We saved your document but could not read it: ${doc.error} Please tick what the software should do instead.`
            : "We saved your document but could not read it. Please tick what the software should do instead."
        }
      />
    );
  }
  return (
    <ReviewForm
      options={options}
      doc={doc}
      extraction={doc.extraction}
      prefill={form}
      onBack={onBack}
    />
  );
}

export function NewEstimateWizard() {
  const searchParams = useSearchParams();
  const country = searchParams.get("country") === "us" ? "us" : "india";
  const loader = React.useCallback(() => api.quickOptions(country), [country]);
  const { state } = useLoad(loader);
  if (state.kind === "loading") return <Loading fullPage />;
  if (state.kind === "error") return <ErrorNotice message={state.message} />;
  return <Flow key={state.data.country} options={state.data} />;
}
