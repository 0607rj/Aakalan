"use client";

import * as React from "react";

import { ErrorNotice, Loading, SectionTitle } from "@/components/status";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  api,
  errorText,
  type AnswerIn,
  type Questionnaire,
  type QuestionnaireField,
} from "@/lib/api/client";
import { formatValue } from "@/lib/format";
import { useLoad } from "@/lib/use-load";

type Kind =
  | { kind: "select"; options: string[]; nullable: boolean }
  | { kind: "boolean" }
  | { kind: "number"; integer: boolean; nullable: boolean }
  | { kind: "json" };

type JsonSchema = Record<string, unknown>;

function asSchemas(value: unknown): JsonSchema[] {
  return Array.isArray(value)
    ? value.filter((v): v is JsonSchema => typeof v === "object" && v !== null)
    : [];
}

/** Map a field's JSON schema (from Pydantic) to an input kind. */
function fieldKind(schema: JsonSchema): Kind {
  const variants = schema.anyOf ? asSchemas(schema.anyOf) : [schema];
  const nullable = variants.some((v) => v.type === "null");
  const withEnum = variants.find((v) => Array.isArray(v.enum));
  if (withEnum && Array.isArray(withEnum.enum)) {
    return { kind: "select", options: withEnum.enum.map(String), nullable };
  }
  const types = variants.map((v) => v.type);
  if (types.includes("boolean")) return { kind: "boolean" };
  if (types.includes("array") || types.includes("object")) {
    return { kind: "json" };
  }
  if (types.includes("integer")) {
    return { kind: "number", integer: true, nullable };
  }
  return { kind: "number", integer: false, nullable };
}

function toDraft(value: unknown, kind: Kind): string | boolean {
  if (kind.kind === "boolean") return value === true;
  if (kind.kind === "json") return JSON.stringify(value ?? [], null, 2);
  if (value === null || value === undefined) return "";
  return String(value);
}

function fromDraft(draft: string | boolean, kind: Kind): unknown {
  if (kind.kind === "boolean") return draft === true;
  const text = String(draft).trim();
  if (kind.kind === "json") {
    try {
      return JSON.parse(text) as unknown;
    } catch {
      throw new Error("is not valid JSON");
    }
  }
  if (text === "") {
    if (kind.nullable) return null;
    throw new Error("is required");
  }
  if (kind.kind === "select") return text;
  const n = Number(text);
  if (!Number.isFinite(n)) throw new Error("must be a number");
  if (kind.integer && !Number.isInteger(n)) {
    throw new Error("must be a whole number");
  }
  return n;
}

type Draft = {
  value: string | boolean;
  dirty: boolean;
  reset: boolean; // revert to the parameter-set default
};

function initialDrafts(q: Questionnaire): Record<string, Draft> {
  return Object.fromEntries(
    q.fields.map((f) => [
      f.key,
      {
        value: toDraft(f.value, fieldKind(f.schema)),
        dirty: false,
        reset: false,
      },
    ]),
  );
}

function FieldInput({
  field,
  kind,
  draft,
  disabled,
  onChange,
}: {
  field: QuestionnaireField;
  kind: Kind;
  draft: Draft;
  disabled: boolean;
  onChange: (value: string | boolean) => void;
}) {
  const id = `q-${field.key}`;
  if (kind.kind === "boolean") {
    return (
      <input
        id={id}
        type="checkbox"
        className="size-4 accent-primary"
        checked={draft.value === true}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
      />
    );
  }
  if (kind.kind === "select") {
    return (
      <Select
        id={id}
        value={String(draft.value)}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
      >
        {kind.nullable ? <option value="">(none)</option> : null}
        {kind.options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </Select>
    );
  }
  if (kind.kind === "json") {
    return (
      <Textarea
        id={id}
        className="min-h-24 font-mono text-xs"
        value={String(draft.value)}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }
  return (
    <Input
      id={id}
      type="number"
      step={kind.integer ? 1 : "any"}
      value={String(draft.value)}
      placeholder={kind.nullable ? "(none)" : undefined}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

function QuestionnaireForm({
  projectId,
  questionnaire,
  canEdit,
  onSaved,
}: {
  projectId: string;
  questionnaire: Questionnaire;
  canEdit: boolean;
  onSaved: (q: Questionnaire) => void;
}) {
  const [drafts, setDrafts] = React.useState(() =>
    initialDrafts(questionnaire),
  );
  const [error, setError] = React.useState<string | null>(null);
  const [saved, setSaved] = React.useState(false);
  const [saving, setSaving] = React.useState(false);

  const kinds = React.useMemo(
    () =>
      Object.fromEntries(
        questionnaire.fields.map((f) => [f.key, fieldKind(f.schema)]),
      ),
    [questionnaire],
  );

  function update(key: string, patch: Partial<Draft>) {
    setSaved(false);
    setDrafts((d) => ({ ...d, [key]: { ...d[key], ...patch } }));
  }

  async function save(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    const answers: AnswerIn[] = [];
    const problems: string[] = [];
    for (const field of questionnaire.fields) {
      const draft = drafts[field.key];
      const hidden = field.restricted && field.value === null;
      if (hidden || draft.reset) continue;
      if (!draft.dirty && field.source !== "user") continue;
      try {
        answers.push({
          key: field.key,
          value: fromDraft(draft.value, kinds[field.key]),
          requirement_ids: field.requirement_ids,
        });
      } catch (err) {
        problems.push(`${field.title} ${errorText(err)}`);
      }
    }
    if (problems.length) {
      setError(problems.join("; "));
      return;
    }
    setSaving(true);
    try {
      const updated = await api.putQuestionnaire(projectId, answers);
      setDrafts(initialDrafts(updated));
      setSaved(true);
      onSaved(updated);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={save} className="flex flex-col gap-4">
      <Card>
        <CardContent className="grid gap-x-6 gap-y-4 pt-6 md:grid-cols-2">
          {questionnaire.fields.map((field) => {
            const kind = kinds[field.key];
            const draft = drafts[field.key];
            const hidden = field.restricted && field.value === null;
            const isUser = field.source === "user" && !draft.reset;
            return (
              <div key={field.key} className="flex flex-col gap-1.5">
                <div className="flex flex-wrap items-center gap-2">
                  <label
                    htmlFor={`q-${field.key}`}
                    className="text-sm font-medium"
                  >
                    {field.title}
                  </label>
                  {field.restricted ? (
                    <Badge variant="outline">finance only</Badge>
                  ) : null}
                  {draft.dirty ? (
                    <Badge variant="secondary">edited</Badge>
                  ) : isUser ? (
                    <Badge variant="success">answered</Badge>
                  ) : (
                    <Badge variant="warning">default</Badge>
                  )}
                  {field.requirement_ids.length > 0 && !draft.reset ? (
                    <span className="text-xs text-muted-foreground">
                      cites {field.requirement_ids.length} requirement
                      {field.requirement_ids.length > 1 ? "s" : ""}
                    </span>
                  ) : null}
                </div>
                <FieldInput
                  field={field}
                  kind={kind}
                  draft={draft}
                  disabled={!canEdit || hidden}
                  onChange={(value) =>
                    update(field.key, { value, dirty: true, reset: false })
                  }
                />
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span>
                    {hidden
                      ? "Visible to finance and admin only."
                      : `Default: ${formatValue(field.default)}`}
                  </span>
                  {canEdit && !hidden && (isUser || draft.dirty) ? (
                    <button
                      type="button"
                      className="text-primary hover:underline"
                      onClick={() =>
                        update(field.key, {
                          value: toDraft(field.default, kind),
                          dirty: false,
                          reset: true,
                        })
                      }
                    >
                      Use default
                    </button>
                  ) : null}
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>
      <ErrorNotice message={error} />
      {canEdit ? (
        <div className="flex items-center gap-3">
          <Button type="submit" disabled={saving}>
            {saving ? "Saving…" : "Save answers"}
          </Button>
          {saved ? <span className="text-sm text-success">Saved.</span> : null}
        </div>
      ) : null}
    </form>
  );
}

export function QuestionnaireTab({
  projectId,
  canEdit,
}: {
  projectId: string;
  canEdit: boolean;
}) {
  const load = React.useCallback(
    () => api.getQuestionnaire(projectId),
    [projectId],
  );
  const { state, setData } = useLoad(load);

  if (state.kind === "loading") return <Loading />;
  if (state.kind === "error") return <ErrorNotice message={state.message} />;

  return (
    <div className="flex flex-col gap-4">
      <SectionTitle>Questionnaire</SectionTitle>
      <p className="text-sm text-muted-foreground">
        Project drivers. Anything you leave on its default (parameter set{" "}
        {state.data.parameter_set_version}) is listed as an assumption on the
        estimate.
      </p>
      <QuestionnaireForm
        projectId={projectId}
        questionnaire={state.data}
        canEdit={canEdit}
        onSaved={setData}
      />
    </div>
  );
}
