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
  type QuickOptions,
  type QuickRequest,
  type Suggestion,
  type Template,
  type TenderDocument,
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
  optionsCurrency,
  QuestionGroup,
  QuestionHeading,
  relevantQuestions,
  setChoice,
  StepIndicator,
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
  CustomFeaturesSection,
  type CustomItem,
  itemsFromTemplate,
  ResearchedFeatures,
  toCustomFeatures,
} from "./custom-features";
import { ReviewForm } from "./review";
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
  const [showAll, setShowAll] = React.useState(false);
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
  const overrides = saved?.overrides ?? {};
  const [deadline, setDeadline] = React.useState(
    saved?.deadline_months ? String(saved.deadline_months) : "",
  );
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const deadlineMonths = deadline.trim() === "" ? null : Number(deadline);
  const deadlineValid =
    deadlineMonths === null ||
    (Number.isInteger(deadlineMonths) &&
      deadlineMonths >= 1 &&
      deadlineMonths <= 60);
  const typeDone = name.trim().length > 0 && projectType !== null;
  const canContinue =
    typeDone && (features.length > 0 || customFeatures.length > 0);
  const kind = options.project_types.find((t) => t.key === projectType);
  const tickable = options.features.filter((f) => !f.hidden);
  const firstShown =
    kind && kind.features.length > 0
      ? tickable.filter((f) => kind.features.includes(f.key))
      : tickable;
  const moreShown = tickable.filter((f) => !firstShown.includes(f));
  const everything = allFeatures(options, features, choices);
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
  const request: QuickRequest = {
    name: name.trim(),
    project_type: projectType,
    country: options.country,
    features,
    feature_levels: featureLevels,
    custom_features: customFeatures,
    choices,
    scope: chosenScope(scopeGroups, scope),
    deadline_months: deadlineValid ? deadlineMonths : null,
    document_id: documentId,
    overrides,
    mode: "vendor",
  };
  const impacts = useQuestionImpact(
    (current.startsWith("q:") || current === "details") && canContinue
      ? request
      : null,
  );

  function change(key: string, value: Choice) {
    answered.current.add(key);
    if (key === VERSION) setLevels({}); // a new overall level resets hand-picked ones
    setChoices((now) =>
      setChoice(options.questions, now, answered.current, key, value),
    );
  }
  const currency = optionsCurrency(options);

  function toggle(key: string) {
    setFeatures((now) =>
      now.includes(key) ? now.filter((k) => k !== key) : [...now, key],
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

      {current === "type" ? (
        <section className="flex flex-col gap-6">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
              What do you want to build?
            </h1>
            <p className="mt-1 text-muted-foreground">
              Give it a name and pick the closest kind. Next, you choose what it
              should do.
            </p>
          </div>
          <div className="flex max-w-xl flex-col gap-2">
            <Label htmlFor="project-name" className="text-base">
              Project name
            </Label>
            <Input
              id="project-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Booking app for a clinic"
              className="h-11 text-base"
            />
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
                  onClick={() => {
                    setProjectType(t.key);
                    setShowAll(false);
                    // start with the usual features, unless some are already ticked
                    if (features.length === 0) setFeatures(t.suggested);
                  }}
                  className={cn(
                    "flex flex-col gap-1 rounded-xl border bg-card p-4 text-left transition-colors",
                    active
                      ? "border-primary bg-primary/5 ring-1 ring-primary"
                      : "hover:border-primary/40 hover:bg-muted/40",
                  )}
                >
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
            hint={typeDone ? null : "Enter a name and pick a kind to continue."}
          />
        </section>
      ) : current === "features" ? (
        <section className="flex flex-col gap-6">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
              What should it do?
            </h1>
            <p className="mt-1 text-muted-foreground">
              {kind && kind.features.length > 0
                ? `The usual features for ${kind.label.toLowerCase()}. We ticked the most common; change anything.`
                : "Tick everything the software should do."}
            </p>
          </div>
          <DescribeBox
            onSuggested={(s) => {
              const tickable = new Set(
                options.features.filter((f) => !f.hidden).map((f) => f.key),
              );
              const keys = s.features.map((f) => f.key);
              setReasons(
                Object.fromEntries(s.features.map((f) => [f.key, f.quote])),
              );
              setFeatures((now) => [
                ...new Set([...now, ...keys.filter((k) => tickable.has(k))]),
              ]);
              // a mobile app, other software or old data: answer those questions
              const implied = {
                ...presetFromFeatures(
                  options,
                  keys.filter((k) => !tickable.has(k)),
                ),
                ...s.choices,
              };
              for (const key of Object.keys(implied)) answered.current.add(key);
              setChoices((now) => ({ ...now, ...implied }));
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
              if (keys.some((k) => moreShown.some((f) => f.key === k))) {
                setShowAll(true);
              }
              if (s.other_features.length > 0) {
                setCustomItems((now) => [
                  ...now,
                  ...s.other_features.map((o, i) => ({
                    id: `described-${Date.now()}-${i}`,
                    name: o.name,
                    category: o.category,
                    size: o.size as "S" | "M" | "L",
                    foundIndex: null,
                    description: o.description,
                    evidence: [],
                    included: true,
                  })),
                ]);
              }
            }}
          />
          <div className="grid gap-3 sm:grid-cols-2">
            {firstShown.map((feature) => (
              <FeatureCard
                key={feature.key}
                label={feature.label}
                hint={feature.hint}
                checked={features.includes(feature.key)}
                onToggle={() => toggle(feature.key)}
              >
                <SuggestedBecause quote={reasons[feature.key]} />
              </FeatureCard>
            ))}
          </div>
          {moreShown.length > 0 ? (
            <div className="flex flex-col gap-3">
              <button
                type="button"
                onClick={() => setShowAll((v) => !v)}
                className="w-fit text-sm font-medium text-primary hover:underline"
              >
                {showAll
                  ? "Hide more features"
                  : `More features (${moreShown.length})${
                      moreShown.some((f) => features.includes(f.key))
                        ? " — some ticked"
                        : ""
                    }`}
              </button>
              {showAll ? (
                <div className="grid gap-3 sm:grid-cols-2">
                  {moreShown.map((feature) => (
                    <FeatureCard
                      key={feature.key}
                      label={feature.label}
                      hint={feature.hint}
                      checked={features.includes(feature.key)}
                      onToggle={() => toggle(feature.key)}
                    >
                      <SuggestedBecause quote={reasons[feature.key]} />
                    </FeatureCard>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
          <ResearchedFeatures
            researched={options.researched ?? []}
            items={customItems}
            onChange={setCustomItems}
          />
          <CustomFeaturesSection
            items={customItems}
            onChange={setCustomItems}
            types={options.custom_feature_types}
          />
          <StepButtons
            onBack={steps.prev}
            onNext={steps.next}
            nextDisabled={!canContinue}
            hint={
              canContinue
                ? `${features.length + customFeatures.length} selected`
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
                <SuggestedBecause key={k} quote={quote} />,
              ]),
            )}
            onToggle={(key) =>
              setScope((now) =>
                now.includes(key)
                  ? now.filter((k) => k !== key)
                  : [...now, key],
              )
            }
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
            value={choices[question.key] ?? question.default}
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
          <StepButtons onBack={steps.prev} onNext={steps.next} />
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
      ) : current === "deadline" ? (
        <section className="flex flex-col gap-6">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
              Is there a deadline?
            </h1>
            <p className="mt-1 text-muted-foreground">
              A tight deadline needs a bigger team, which costs more. Leave it
              empty if there is no fixed date.
            </p>
          </div>
          <div className="flex max-w-sm flex-col gap-2">
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
                step: "deadline",
                label: "Deadline",
                value: deadlineMonths ? `${deadlineMonths} months` : "None",
              },
            ]}
            onChange={steps.goTo}
          />
          <ErrorNotice message={error} />
          <StepButtons
            onBack={steps.prev}
            onNext={submit}
            nextLabel="Calculate my cost"
            nextDisabled={!deadlineValid}
          />
        </>
      )}
    </div>
  );
}

/** A few lines about the software -> features ticked for the user to check. */
function DescribeBox({
  onSuggested,
}: {
  onSuggested: (s: Suggestion) => void;
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
          : `We ticked ${found} feature${found === 1 ? "" : "s"} from your description. Check them below and add anything missing.`) +
          (s.note ? ` ${s.note}` : ""),
      );
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-primary/30 bg-primary/5 p-4">
      <Label htmlFor="describe" className="text-base font-semibold">
        Describe it in a few lines (optional)
      </Label>
      <textarea
        id="describe"
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={3}
        maxLength={4000}
        placeholder="e.g. An app for my clinic where patients book an appointment with a doctor, pay the fee online and get an SMS reminder."
        className="w-full rounded-lg border bg-background px-3 py-2 text-base"
      />
      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={suggest} disabled={!ready || busy}>
          {busy ? "Reading…" : "Suggest features"}
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

/** Under a feature ticked from the description: the user's words that asked for it. */
function SuggestedBecause({ quote }: { quote?: string }) {
  if (!quote) return null;
  return (
    <span className="text-sm text-primary">
      Suggested because you wrote: “{quote}”
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
    "flex flex-col gap-2 rounded-2xl border bg-card p-6 text-left shadow-sm transition-colors hover:border-primary/50 hover:bg-muted/40";
  return (
    <section className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
          How would you like to start?
        </h1>
        <p className="mt-1 text-muted-foreground">
          The quickest way is to upload the requirement document. We read it and
          fill in the details for you to check.
        </p>
      </div>
      <CountryChoice options={options} onChange={onCountry} />
      <div className="grid gap-4 md:grid-cols-2">
        <button
          type="button"
          onClick={onUpload}
          className={cn(card, "border-primary/40 ring-1 ring-primary/20")}
        >
          <span className="text-3xl" aria-hidden>
            📄
          </span>
          <span className="text-lg font-semibold">
            Upload the requirement document{" "}
            <span className="text-sm font-normal text-primary">
              (recommended)
            </span>
          </span>
          <span className="text-muted-foreground">
            PDF or Word. We find what it asks for and show the page each item
            came from.
          </span>
        </button>
        <button type="button" onClick={onManual} className={card}>
          <span className="text-3xl" aria-hidden>
            ✏️
          </span>
          <span className="text-lg font-semibold">
            No document — I&apos;ll describe it myself
          </span>
          <span className="text-muted-foreground">
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
  const toStart = () => go({});

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
  const loader = React.useCallback(() => api.getDocument(docId), [docId]);
  const { state } = useLoad(loader);
  if (state.kind === "loading")
    return <Loading>Opening your document…</Loading>;
  if (state.kind === "error") return <ErrorNotice message={state.message} />;
  const doc: TenderDocument = state.data;
  if (doc.status !== "extracted" || !doc.extraction) {
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
