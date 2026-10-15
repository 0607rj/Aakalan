"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

import { ErrorNotice, Loading } from "@/components/status";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  api,
  errorText,
  type QuickOptions,
  type QuickQuestion,
} from "@/lib/api/client";
import { useLoad } from "@/lib/use-load";
import { cn } from "@/lib/utils";

const STEP_LABELS = ["What to build", "A few questions", "Your cost"];

type Choice = string | number;

function StepIndicator({ current }: { current: number }) {
  return (
    <ol className="flex flex-wrap items-center gap-2 text-sm">
      {STEP_LABELS.map((label, i) => {
        const n = i + 1;
        const done = n < current;
        const active = n === current;
        return (
          <li key={label} className="flex items-center gap-2">
            <span
              className={cn(
                "flex size-7 items-center justify-center rounded-full border text-xs font-semibold",
                active && "border-primary bg-primary text-primary-foreground",
                done && "border-primary text-primary",
                !active && !done && "text-muted-foreground",
              )}
            >
              {done ? "✓" : n}
            </span>
            <span
              className={cn(
                active ? "font-medium" : "text-muted-foreground",
                "mr-2",
              )}
            >
              {label}
            </span>
            {n < STEP_LABELS.length ? (
              <span className="mr-2 hidden h-px w-8 bg-border sm:inline-block" />
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}

function FeatureCard({
  label,
  hint,
  checked,
  onToggle,
}: {
  label: string;
  hint: string;
  checked: boolean;
  onToggle: () => void;
}) {
  return (
    <label
      className={cn(
        "flex cursor-pointer items-start gap-3 rounded-xl border bg-card p-4 transition-colors",
        checked
          ? "border-primary bg-primary/5 ring-1 ring-primary"
          : "hover:border-primary/40 hover:bg-muted/40",
      )}
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={onToggle}
        className="mt-1 size-4 accent-primary"
      />
      <span className="flex flex-col gap-1">
        <span className="font-semibold">{label}</span>
        <span className="text-sm text-muted-foreground">{hint}</span>
      </span>
    </label>
  );
}

function QuestionGroup({
  question,
  value,
  onChange,
}: {
  question: QuickQuestion;
  value: Choice;
  onChange: (value: Choice) => void;
}) {
  return (
    <fieldset className="flex flex-col gap-3">
      <legend className="mb-3 text-base font-semibold">{question.label}</legend>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {question.options.map((option) => {
          const selected = option.value === value;
          return (
            <label
              key={String(option.value)}
              className={cn(
                "flex cursor-pointer flex-col gap-1 rounded-xl border bg-card p-4 transition-colors",
                selected
                  ? "border-primary bg-primary/5 ring-1 ring-primary"
                  : "hover:border-primary/40 hover:bg-muted/40",
              )}
            >
              <span className="flex items-center gap-2">
                <input
                  type="radio"
                  name={question.key}
                  checked={selected}
                  onChange={() => onChange(option.value)}
                  className="size-4 accent-primary"
                />
                <span className="font-semibold">{option.label}</span>
              </span>
              {option.hint ? (
                <span className="pl-6 text-sm text-muted-foreground">
                  {option.hint}
                </span>
              ) : null}
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

function WizardForm({ options }: { options: QuickOptions }) {
  const router = useRouter();
  const [step, setStep] = React.useState(1);
  const [name, setName] = React.useState("");
  const [features, setFeatures] = React.useState<string[]>([]);
  const [choices, setChoices] = React.useState<Record<string, Choice>>(() =>
    Object.fromEntries(options.questions.map((q) => [q.key, q.default])),
  );
  const [deadline, setDeadline] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const deadlineMonths = deadline.trim() === "" ? null : Number(deadline);
  const deadlineValid =
    deadlineMonths === null ||
    (Number.isInteger(deadlineMonths) &&
      deadlineMonths >= 1 &&
      deadlineMonths <= 60);
  const canContinue = name.trim().length > 0 && features.length > 0;

  function toggle(key: string) {
    setFeatures((current) =>
      current.includes(key)
        ? current.filter((k) => k !== key)
        : [...current, key],
    );
  }

  function goTo(n: number) {
    setStep(n);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function submit() {
    setSubmitting(true);
    setError(null);
    try {
      const summary = await api.createQuickEstimate({
        name: name.trim(),
        features,
        choices,
        deadline_months: deadlineMonths,
      });
      router.push(`/estimate/${summary.estimate_id}`);
    } catch (e) {
      setError(errorText(e));
      setSubmitting(false);
    }
  }

  if (submitting) {
    return (
      <div className="flex flex-col items-center gap-4 py-24 text-center">
        <StepIndicator current={3} />
        <div className="mt-8 size-10 animate-spin rounded-full border-4 border-muted border-t-primary" />
        <p className="text-lg font-medium">Working out your cost…</p>
        <p className="text-sm text-muted-foreground">
          This takes a few seconds.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8">
      <StepIndicator current={step} />

      {step === 1 ? (
        <section className="flex flex-col gap-6">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
              What do you want to build?
            </h1>
            <p className="mt-1 text-muted-foreground">
              Give it a name and tick everything the software should do.
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
              placeholder="e.g. Vendor registration portal for the department"
              className="h-11 text-base"
            />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {options.features.map((feature) => (
              <FeatureCard
                key={feature.key}
                label={feature.label}
                hint={feature.hint}
                checked={features.includes(feature.key)}
                onToggle={() => toggle(feature.key)}
              />
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-4">
            <Button
              size="lg"
              className="h-11"
              disabled={!canContinue}
              onClick={() => goTo(2)}
            >
              Continue
            </Button>
            {!canContinue ? (
              <span className="text-sm text-muted-foreground">
                Enter a name and tick at least one feature to continue.
              </span>
            ) : (
              <span className="text-sm text-muted-foreground">
                {features.length} selected
              </span>
            )}
          </div>
        </section>
      ) : (
        <section className="flex flex-col gap-8">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
              A few questions
            </h1>
            <p className="mt-1 text-muted-foreground">
              We have picked the usual answers. Change any that don&apos;t fit.
            </p>
          </div>
          {options.questions.map((question) => (
            <QuestionGroup
              key={question.key}
              question={question}
              value={choices[question.key] ?? question.default}
              onChange={(value) =>
                setChoices((current) => ({ ...current, [question.key]: value }))
              }
            />
          ))}
          <div className="flex max-w-sm flex-col gap-2">
            <Label htmlFor="deadline" className="text-base font-semibold">
              Is there a deadline?
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
            <span className="text-sm text-muted-foreground">
              Leave empty if there is no fixed deadline.
            </span>
            {!deadlineValid ? (
              <span className="text-sm text-destructive">
                Enter a whole number of months between 1 and 60.
              </span>
            ) : null}
          </div>
          <ErrorNotice message={error} />
          <div className="flex flex-wrap gap-3">
            <Button
              variant="outline"
              size="lg"
              className="h-11"
              onClick={() => goTo(1)}
            >
              Back
            </Button>
            <Button
              size="lg"
              className="h-11"
              disabled={!deadlineValid}
              onClick={submit}
            >
              Calculate my cost
            </Button>
          </div>
        </section>
      )}
    </div>
  );
}

export function NewEstimateWizard() {
  const loader = React.useCallback(() => api.quickOptions(), []);
  const { state } = useLoad(loader);
  if (state.kind === "loading") return <Loading />;
  if (state.kind === "error") return <ErrorNotice message={state.message} />;
  return <WizardForm options={state.data} />;
}
