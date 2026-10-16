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
  type TenderDocument,
} from "@/lib/api/client";
import { useLoad } from "@/lib/use-load";
import { cn } from "@/lib/utils";

import {
  Calculating,
  type Choice,
  FeatureCard,
  MANUAL_STEPS,
  orderByImpact,
  QuestionGroup,
  StepIndicator,
  useQuestionImpact,
} from "./parts";
import { ReviewForm } from "./review";
import { UploadStep } from "./upload-step";

/** The tick-box path (no document, or the document could not be read). */
function ManualForm({
  options,
  documentId = null,
  initialName = "",
  notice = null,
}: {
  options: QuickOptions;
  documentId?: string | null;
  initialName?: string;
  notice?: string | null;
}) {
  const router = useRouter();
  const [step, setStep] = React.useState(1);
  const [name, setName] = React.useState(initialName);
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
  const impacts = useQuestionImpact(
    step === 2 && canContinue && deadlineValid
      ? {
          name: name.trim(),
          features,
          choices,
          deadline_months: deadlineMonths,
          document_id: documentId,
          overrides: {},
        }
      : null,
  );

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
        document_id: documentId,
        overrides: {},
      });
      router.push(`/estimate/${summary.estimate_id}`);
    } catch (e) {
      setError(errorText(e));
      setSubmitting(false);
    }
  }

  if (submitting) return <Calculating labels={MANUAL_STEPS} />;

  return (
    <div className="flex flex-col gap-8">
      <StepIndicator labels={MANUAL_STEPS} current={step} />
      <ErrorNotice message={notice} />

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
              We have picked the usual answers. Change any that don&apos;t fit —
              the ones that matter most for the price are first.
            </p>
          </div>
          {orderByImpact(options.questions, impacts).map((question) => (
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

function StartChoice({
  onUpload,
  onManual,
}: {
  onUpload: () => void;
  onManual: () => void;
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
          The quickest way is to upload the tender. We read it and fill in the
          details for you to check.
        </p>
      </div>
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
            Upload the tender document{" "}
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
            Tick what the software should do and answer a few questions.
          </span>
        </button>
      </div>
    </section>
  );
}

type Mode =
  | { kind: "start" }
  | { kind: "upload" }
  | { kind: "manual" }
  | { kind: "review"; doc: TenderDocument };

function Flow({ options }: { options: QuickOptions }) {
  const [mode, setMode] = React.useState<Mode>({ kind: "start" });

  function go(next: Mode) {
    setMode(next);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  switch (mode.kind) {
    case "start":
      return (
        <StartChoice
          onUpload={() => go({ kind: "upload" })}
          onManual={() => go({ kind: "manual" })}
        />
      );
    case "upload":
      return (
        <UploadStep
          onUploaded={(doc) => go({ kind: "review", doc })}
          onBack={() => go({ kind: "start" })}
        />
      );
    case "manual":
      return <ManualForm options={options} />;
    case "review": {
      const { doc } = mode;
      if (doc.status !== "extracted" || !doc.extraction) {
        return (
          <ManualForm
            options={options}
            documentId={doc.id}
            initialName={doc.project_name}
            notice={
              doc.error
                ? `We saved your document but could not read it: ${doc.error} Please tick what the software should do instead.`
                : "We saved your document but could not read it. Please tick what the software should do instead."
            }
          />
        );
      }
      return (
        <ReviewForm options={options} doc={doc} extraction={doc.extraction} />
      );
    }
  }
}

export function NewEstimateWizard() {
  const loader = React.useCallback(() => api.quickOptions(), []);
  const { state } = useLoad(loader);
  if (state.kind === "loading") return <Loading />;
  if (state.kind === "error") return <ErrorNotice message={state.message} />;
  return <Flow options={state.data} />;
}
