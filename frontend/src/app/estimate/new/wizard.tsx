"use client";

import * as React from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { ErrorNotice, Loading } from "@/components/status";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  api,
  errorText,
  type NotIncluded,
  type QuickOptions,
  type QuickRequest,
  type Suggestion,
  type Template,
} from "@/lib/api/client";
import { currencySymbol, formatDate } from "@/lib/format";
import { useLoad } from "@/lib/use-load";
import { cn } from "@/lib/utils";

import {
  Calculating,
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
import { sentStories, StoriesStep, type StoryText } from "./stories-step";
import { UploadStep } from "./upload-step";

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
  const [projectType, setProjectType] = React.useState<string | null>(
    () => saved?.project_type ?? (saved ? OTHER_TYPE : null),
  );
  // asked for in the description, but nothing this estimate can price
  const [notPriced, setNotPriced] = React.useState<string[]>([]);
  // features suggested from the user's own description: key -> the words that asked for it
  const [reasons, setReasons] = React.useState<Record<string, string>>({});
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
  const overrides = saved?.overrides ?? {};
  const [deadline, setDeadline] = React.useState(
    saved?.deadline_months ? String(saved.deadline_months) : "",
  );
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  // the user's description (for drafting stories) and the stories per feature, as typed
  const [description, setDescription] = React.useState("");
  const [storyText, setStoryText] = React.useState<StoryText>(() =>
    Object.fromEntries(
      Object.entries(saved?.feature_stories ?? {}).map(([k, v]) => [
        k,
        v.join("\n"),
      ]),
    ),
  );

  const deadlineMonths = deadline.trim() === "" ? null : Number(deadline);
  const deadlineValid =
    deadlineMonths === null ||
    (Number.isInteger(deadlineMonths) &&
      deadlineMonths >= 1 &&
      deadlineMonths <= 60);
  const typeDone = name.trim().length > 0 && projectType !== null;
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
  const [first, ...rest] = questions.map((q) => `q:${q.key}`);
  // Like public cost calculators: what it is, one feature tick list, a few questions and the
  // deadline; the extras ("What else does it need?") and details come last and are optional.
  const stepKeys = [
    "type",
    "features",
    ...(first ? [first] : []),
    ...(customizing && leveled.length > 0 ? ["levels"] : []),
    ...rest,
    "deadline",
    ...(scopeGroups.length > 0 ? ["scope"] : []),
    ...(details.length > 0 ? ["details"] : []),
    // optional: what people can do (double-checks the build size; a document has its own)
    ...(documentId ? [] : ["stories"]),
    "check",
  ];
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
  const storyFeatures = [
    ...everything.map((k) => ({
      key: k,
      label: options.features.find((f) => f.key === k)?.label ?? k,
    })),
    ...customFeatures.map((c) => ({ key: c.name, label: c.name })),
  ];
  const featureStories = sentStories(storyText, storyFeatures);
  const storyCount = Object.values(featureStories).reduce(
    (n, s) => n + s.length,
    0,
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
    deadline_months: deadlineValid ? deadlineMonths : null,
    document_id: documentId,
    overrides,
    mode: "vendor",
    // an answer may have added a feature marked not included (e.g. an app): it is priced
    not_included: sentNotIncluded(notIncluded, everything, pricedScope),
    answered: touched,
    feature_stories: featureStories,
  };
  const impacts = useQuestionImpact(
    (current.startsWith("q:") || current === "details") && canContinue
      ? request
      : null,
  );

  function change(key: string, value: Choice) {
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

  if (submitting) return <Calculating labels={MANUAL_STEPS} />;

  const question = current.startsWith("q:")
    ? questions.find((q) => `q:${q.key}` === current)
    : undefined;
  const phase = ["type", "features", "scope", "levels"].includes(current)
    ? 1
    : 2;

  return (
    <div className="flex flex-col gap-8">
      <StepIndicator labels={MANUAL_STEPS} current={phase} />
      <Progress
        index={Math.max(0, stepKeys.indexOf(current))}
        total={steps.total}
      />
      <ErrorNotice message={notice} />

      <div key={current} className="step-in flex flex-col gap-8">
        {current === "type" ? (
          <section className="flex flex-col gap-6">
            <div className="settle flex flex-col gap-2">
              <p className="eyebrow">Step 1 of 3</p>
              <h1 className="font-display text-3xl sm:text-4xl">
                What do you want to build?
              </h1>
              <p className="max-w-2xl text-muted-foreground">
                Give it a name and pick the closest kind. Next, you choose what
                it should do.
              </p>
            </div>
            <div className="slab flex flex-col gap-2 p-5 sm:p-6">
              <Label htmlFor="project-name" className="text-base">
                Project name
              </Label>
              <Input
                id="project-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Booking app for a clinic"
                className="h-12 max-w-xl rounded-lg px-4 text-base"
              />
              <span className="text-xs text-muted-foreground">
                Only for you, to find it again in your list.
              </span>
            </div>
            <div className="flex flex-col gap-1">
              <h2 className="text-lg font-semibold">Which one is closest?</h2>
              <p className="text-sm text-muted-foreground">
                It only decides which features we show first. You can still tick
                anything.
              </p>
            </div>
            <div
              role="radiogroup"
              aria-label="Kind of software"
              className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3"
            >
              {options.project_types.map((t) => {
                const active = t.key === projectType;
                return (
                  <button
                    key={t.key}
                    type="button"
                    role="radio"
                    aria-checked={active}
                    onClick={() => setProjectType(t.key)}
                    className={cn(
                      "flex flex-col gap-2 rounded-xl border bg-card p-4 text-left transition-colors focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
                      active
                        ? "border-primary bg-tape-soft/50 ring-1 ring-primary"
                        : "hover:border-primary/40 hover:bg-panel-2",
                    )}
                  >
                    <span className="flex items-center justify-between">
                      <span
                        className={cn(
                          "flex size-9 items-center justify-center rounded-lg transition-colors",
                          active
                            ? "bg-primary text-primary-foreground"
                            : "bg-tape-soft text-primary",
                        )}
                      >
                        <TypeIcon kind={t.key} />
                      </span>
                      {active ? (
                        <span className="text-xs font-semibold text-primary">
                          Selected
                        </span>
                      ) : null}
                    </span>
                    <span className="font-semibold">{t.label}</span>
                    <span className="text-sm text-muted-foreground">
                      {t.hint}
                    </span>
                  </button>
                );
              })}
            </div>
            <StepButtons
              onBack={onBack}
              onNext={steps.next}
              nextDisabled={!typeDone}
              hint={
                typeDone ? null : "Enter a name and pick a kind to continue."
              }
            />
          </section>
        ) : current === "features" ? (
          <section className="flex flex-col gap-8">
            <div>
              <h1 className="font-display text-3xl sm:text-4xl">
                What should it do?
              </h1>
              <p className="mt-1 text-muted-foreground">
                Describe it and we find the features, or tick them yourself.
                Each feature can be ticked, left out, or marked not included.
              </p>
            </div>
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
                setFeatures((now) => [
                  ...new Set([
                    ...now.filter((k) => !outKeys.has(k)),
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
                    x.options.some((opt) => o.key in (opt.add_features ?? {})),
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
                      hint="Not in our list: priced as your own feature"
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
                notPriced.length > 0 ? (
                  <div className="rounded-xl border border-dashed px-4 py-3 text-sm">
                    <span className="font-medium">
                      Asked for, but not priced by this estimate:
                    </span>{" "}
                    {notPriced.join(", ")}. Price these separately if they are
                    needed.
                  </div>
                ) : null
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
        ) : current === "scope" ? (
          <>
            <ScopeStep
              groups={scopeGroups}
              chosen={scope}
              suggested={Object.keys(scopeReasons)}
              onTickSuggested={() =>
                setScope((now) => [
                  ...new Set([...now, ...Object.keys(scopeReasons)]),
                ])
              }
              notes={Object.fromEntries(
                Object.entries(scopeReasons).map(([k, quote]) => [
                  k,
                  <FromWords key={k} quote={quote} />,
                ]),
              )}
              onToggle={(key) => {
                setScope((now) =>
                  now.includes(key)
                    ? now.filter((k) => k !== key)
                    : [...now, key],
                );
                unmark("scope", key);
              }}
              notIncluded={notIncluded
                .filter((n) => n.kind === "scope")
                .map((n) => n.key)}
              onNotIncluded={(key) => toggleOut("scope", key)}
            />
            <StepButtons onBack={steps.prev} onNext={steps.next} />
          </>
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
              onChange={(value) => change(question.key, value)}
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
        ) : current === "details" ? (
          <>
            <DetailsStep
              questions={details}
              choices={choices}
              onChange={change}
              impacts={impacts}
              currency={currency}
            />
            <StepButtons onBack={steps.prev} onNext={steps.next} />
          </>
        ) : current === "stories" ? (
          <>
            <StoriesStep
              features={storyFeatures}
              description={description}
              text={storyText}
              onChange={setStoryText}
            />
            <StepButtons
              onBack={steps.prev}
              onNext={steps.next}
              nextLabel={storyCount > 0 ? "Continue" : "Skip"}
            />
          </>
        ) : current === "deadline" ? (
          <section className="flex flex-col gap-6">
            <div>
              <h1 className="font-display text-3xl sm:text-4xl">
                Is there a deadline?
              </h1>
              <p className="mt-1 text-muted-foreground">
                A tight deadline needs a bigger team, which costs more. Leave it
                empty if there is no fixed date.
              </p>
            </div>
            <div className="slab flex max-w-sm flex-col gap-2 p-5 sm:p-6">
              <Label htmlFor="deadline" className="text-base">
                Months from start to launch
              </Label>
              <div className="flex items-center gap-2">
                <Input
                  id="deadline"
                  type="number"
                  inputMode="numeric"
                  min={1}
                  max={60}
                  value={deadline}
                  onChange={(e) => setDeadline(e.target.value)}
                  className="h-11 w-28 text-base"
                />
                <span className="text-muted-foreground">months</span>
              </div>
              {!deadlineValid ? (
                <span className="text-sm text-destructive">
                  Enter a whole number of months between 1 and 60.
                </span>
              ) : null}
            </div>
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
                ...questions.map((q) => ({
                  step: `q:${q.key}`,
                  label: q.label,
                  value: answerLabel(q, choices[q.key]),
                })),
                ...details.map((q) => ({
                  step: "details",
                  label: q.label,
                  value: answerLabel(q, choices[q.key]),
                })),
                {
                  step: "features",
                  label: "Not included",
                  value: notIncludedText(options, notIncluded),
                },
                {
                  step: "deadline",
                  label: "Deadline",
                  value: deadlineMonths ? `${deadlineMonths} months` : "None",
                },
                ...(documentId
                  ? []
                  : [
                      {
                        step: "stories",
                        label: "What people can do",
                        value:
                          storyCount > 0
                            ? `${storyCount} user ${storyCount === 1 ? "story" : "stories"}`
                            : "Skipped",
                      },
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
    <div className="slab flex flex-col gap-3 border-primary/30 p-5 sm:p-6">
      <Label htmlFor="describe" className="text-base font-semibold">
        Describe your project in your own words
      </Label>
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
        className="w-full rounded-lg border bg-background px-4 py-3 text-base focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
      />
      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={suggest} disabled={!ready || busy}>
          {busy ? "Reading…" : "Find features"}
        </Button>
        <span className="text-sm text-muted-foreground">
          We only tick features; you can untick them or add others yourself.
        </span>
      </div>
      {message ? <p className="text-sm">{message}</p> : null}
      <ErrorNotice message={error} />
    </div>
  );
}

/** Under a feature found in the description: the user's words it came from. */
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

/** The "Something else" kind: every feature, nothing ticked to start with. */
const OTHER_TYPE = "other";

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
  const card =
    "slab group flex flex-col gap-3 p-5 text-left transition-colors hover:border-primary/50 sm:p-6";
  const icon =
    "flex size-10 items-center justify-center rounded-lg bg-tape-soft text-primary";
  return (
    <section className="flex flex-col gap-8">
      <div className="settle flex flex-col gap-2">
        <p className="eyebrow">New estimate</p>
        <h1 className="font-display text-3xl sm:text-4xl">
          How would you like to start?
        </h1>
        <p className="max-w-2xl text-muted-foreground">
          The quickest way is to upload the requirement document. We read it and
          fill in the details for you to check.
        </p>
      </div>
      <CountryChoice options={options} onChange={onCountry} />
      <div className="grid gap-4 md:grid-cols-2">
        <button type="button" onClick={onUpload} className={card}>
          <span className={icon}>
            <svg
              aria-hidden="true"
              viewBox="0 0 24 24"
              className="size-5"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M6 2.75h8.5L19.25 7.5v13.75H6zM14.5 2.75V7.5h4.75M9 12h7M9 15.5h7" />
            </svg>
          </span>
          <span className="flex flex-wrap items-center gap-2 text-lg font-semibold">
            Upload the requirement document
            <span className="rounded-full bg-tape-soft px-2 py-0.5 text-xs font-semibold text-primary">
              Recommended
            </span>
          </span>
          <span className="text-sm text-muted-foreground">
            PDF or Word. Every item links to its page.
          </span>
        </button>
        <button type="button" onClick={onManual} className={card}>
          <span className={icon}>
            <svg
              aria-hidden="true"
              viewBox="0 0 24 24"
              className="size-5"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M4 20l1-4.5L16.5 4a1.8 1.8 0 012.5 0l1 1a1.8 1.8 0 010 2.5L8.5 19zM14.5 6l3.5 3.5" />
            </svg>
          </span>
          <span className="text-lg font-semibold">
            No document, I&apos;ll describe it myself
          </span>
          <span className="text-sm text-muted-foreground">
            Tick what the software should do, then answer a few short questions,
            one at a time.
          </span>
        </button>
      </div>
      <SavedTemplates onUse={onTemplate} />
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
    return <Loading>Opening your template…</Loading>;
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
      <h2 className="text-lg font-semibold">Or start from a saved template</h2>
      <ul className="flex flex-col divide-y rounded-2xl border bg-card">
        {state.data.map((t) => (
          <li
            key={t.id}
            className="flex flex-wrap items-center justify-between gap-3 px-5 py-3"
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
    return <Loading>Opening your document…</Loading>;
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
  if (state.kind === "loading") return <Loading />;
  if (state.kind === "error") return <ErrorNotice message={state.message} />;
  return <Flow key={state.data.country} options={state.data} />;
}
