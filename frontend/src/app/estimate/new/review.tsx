"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

import { ErrorNotice, WarningNotice } from "@/components/status";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  api,
  errorText,
  type FoundValue,
  type QuickOptions,
  type TenderDocument,
  type TenderExtraction,
} from "@/lib/api/client";

import {
  Calculating,
  type Choice,
  Citation,
  DOCUMENT_STEPS,
  FeatureCard,
  orderByImpact,
  QuestionGroup,
  StepIndicator,
  useQuestionImpact,
} from "./parts";
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
  /** Only show when the tender mentioned it. */
  onlyIfFound?: boolean;
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
  { key: "emd_paise", label: "EMD amount (₹)", unit: "rupees", min: 0, integer: false },
  { key: "pbg_percent", label: "Performance guarantee (%)", unit: "percent", min: 0, max: 100, integer: false },
];

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

export function ReviewForm({
  options,
  doc,
  extraction,
}: {
  options: QuickOptions;
  doc: TenderDocument;
  extraction: TenderExtraction;
}) {
  const router = useRouter();
  const approx = doc.approximate_pages;
  const foundFeatures = React.useMemo(
    () => new Map(extraction.features.map((f) => [f.key, f])),
    [extraction.features],
  );

  const [name, setName] = React.useState(extraction.project_name);
  const [features, setFeatures] = React.useState<string[]>(() =>
    options.features.map((f) => f.key).filter((k) => foundFeatures.has(k)),
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
  const [choices, setChoices] = React.useState<Record<string, Choice>>(() =>
    Object.fromEntries(
      options.questions.map((q) => [
        q.key,
        asChoice(extraction.choices[q.key]) ?? q.default,
      ]),
    ),
  );
  const [changing, setChanging] = React.useState<Record<string, boolean>>({});
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const visibleFacts = FACTS.filter(
    (f) =>
      (!f.needsFeature || features.includes(f.needsFeature)) &&
      (!f.onlyIfFound || extraction.numbers[f.key] !== undefined),
  );
  const errors = Object.fromEntries(
    visibleFacts.map((f) => [f.key, factError(f, facts[f.key] ?? "")]),
  );
  const hasErrors = Object.values(errors).some(Boolean);
  const omYearsGiven = (facts.om_years ?? "").trim() !== "";
  const questions = options.questions.filter(
    (q) => !(q.key === "support_years" && omYearsGiven),
  );
  const openQuestions = questions.filter(
    (q) => extraction.choices[q.key] === undefined,
  );
  const foundQuestions = questions.filter(
    (q) => extraction.choices[q.key] !== undefined,
  );
  const canSubmit = name.trim().length > 0 && features.length > 0 && !hasErrors;

  const overrides: Record<string, number> = {};
  for (const fact of visibleFacts) {
    const text = (facts[fact.key] ?? "").trim();
    if (text !== "" && !errors[fact.key]) {
      overrides[fact.key] = toApi(fact, Number(text));
    }
  }
  const impacts = useQuestionImpact(
    features.length > 0 && !hasErrors
      ? {
          name: name.trim() || "Estimate",
          document_id: doc.id,
          features,
          choices,
          overrides,
        }
      : null,
  );
  const orderedOpenQuestions = orderByImpact(openQuestions, impacts);

  function toggle(key: string) {
    setFeatures((current) =>
      current.includes(key)
        ? current.filter((k) => k !== key)
        : [...current, key],
    );
  }

  async function submit() {
    setSubmitting(true);
    setError(null);
    try {
      const summary = await api.createQuickEstimate({
        name: name.trim(),
        document_id: doc.id,
        features,
        choices,
        overrides,
      });
      router.push(`/estimate/${summary.estimate_id}`);
    } catch (e) {
      setError(errorText(e));
      setSubmitting(false);
    }
  }

  if (submitting) return <Calculating labels={DOCUMENT_STEPS} />;

  return (
    <div className="flex flex-col gap-10">
      <StepIndicator labels={DOCUMENT_STEPS} current={2} />

      <section className="flex flex-col gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
            Here&apos;s what we found in {doc.filename}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {doc.pages} {approx ? "approximate " : ""}page
            {doc.pages === 1 ? "" : "s"} ·{" "}
            {extraction.reader === "ai" ? "Read by AI" : "Basic reading"} ·
            Please check everything below, then calculate.
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

      <section className="flex flex-col gap-4">
        <div>
          <h2 className="text-xl font-semibold">What the tender asks for</h2>
          <p className="text-sm text-muted-foreground">
            We ticked what the tender mentions. Untick anything wrong and tick
            anything we missed.
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {options.features.map((feature) => {
            const found = foundFeatures.get(feature.key);
            return (
              <FeatureCard
                key={feature.key}
                label={feature.label}
                hint={feature.hint}
                checked={features.includes(feature.key)}
                onToggle={() => toggle(feature.key)}
              >
                {found ? (
                  <Citation
                    evidence={found.evidence}
                    approximatePages={approx}
                  />
                ) : null}
              </FeatureCard>
            );
          })}
        </div>
        {features.length === 0 ? (
          <span className="text-sm text-destructive">
            Tick at least one thing the software should do.
          </span>
        ) : null}
      </section>

      <section className="flex flex-col gap-4">
        <div>
          <h2 className="text-xl font-semibold">Key facts</h2>
          <p className="text-sm text-muted-foreground">
            Numbers from the tender. Leave a box empty if it is not stated — we
            will use a typical value.
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
                </Label>
                <Input
                  id={`fact-${fact.key}`}
                  type="number"
                  inputMode="decimal"
                  min={fact.min}
                  max={fact.max}
                  value={value}
                  placeholder="Not stated in the tender"
                  onChange={(e) =>
                    setFacts((current) => ({
                      ...current,
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
                    Changed by you (tender says {initialFacts[fact.key]})
                  </span>
                ) : null}
              </div>
            );
          })}
        </div>
      </section>

      {openQuestions.length > 0 ? (
        <section className="flex flex-col gap-6">
          <div>
            <h2 className="text-xl font-semibold">
              Please answer — the tender doesn&apos;t say
            </h2>
            <p className="text-sm text-muted-foreground">
              We have picked the usual answers. Change any that don&apos;t fit —
              the ones that matter most for the price are first.
            </p>
          </div>
          {orderedOpenQuestions.map((question) => (
            <QuestionGroup
              key={question.key}
              question={question}
              value={choices[question.key] ?? question.default}
              impact={impacts.get(question.key)}
              onChange={(value) =>
                setChoices((current) => ({ ...current, [question.key]: value }))
              }
            />
          ))}
        </section>
      ) : null}

      {foundQuestions.length > 0 ? (
        <section className="flex flex-col gap-3">
          <h2 className="text-xl font-semibold">Also found in the tender</h2>
          {foundQuestions.map((question) => {
            const found = extraction.choices[question.key];
            const selected = question.options.find(
              (o) => o.value === choices[question.key],
            );
            const open = changing[question.key] ?? false;
            return (
              <div
                key={question.key}
                className="flex flex-col gap-3 rounded-xl border bg-card p-4"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="flex flex-col gap-1">
                    <span className="text-sm text-muted-foreground">
                      {question.label}
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
                    {found && choices[question.key] === asChoice(found) ? (
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
                      setChanging((current) => ({
                        ...current,
                        [question.key]: !open,
                      }))
                    }
                  >
                    {open ? "Done" : "Change"}
                  </Button>
                </div>
                {open ? (
                  <QuestionGroup
                    question={question}
                    value={choices[question.key] ?? question.default}
                    onChange={(value) =>
                      setChoices((current) => ({
                        ...current,
                        [question.key]: value,
                      }))
                    }
                    hideLegend
                    impact={impacts.get(question.key)}
                  />
                ) : null}
              </div>
            );
          })}
        </section>
      ) : null}

      <PrebidQueries
        documentId={doc.id}
        approximatePages={approx}
        fallback={extraction.unclear_points}
      />

      <ErrorNotice message={error} />
      <div className="flex flex-wrap items-center gap-4">
        <Button
          size="lg"
          className="h-11"
          disabled={!canSubmit}
          onClick={submit}
        >
          Calculate my cost
        </Button>
        {!canSubmit ? (
          <span className="text-sm text-muted-foreground">
            {name.trim() === ""
              ? "Enter a project name."
              : features.length === 0
                ? "Tick at least one thing the software should do."
                : "Fix the highlighted numbers."}
          </span>
        ) : null}
      </div>
    </div>
  );
}
