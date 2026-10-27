"use client";

import * as React from "react";
import { ListBulletsIcon } from "@phosphor-icons/react/dist/ssr";

import { useCurrentUser } from "@/components/auth-guard";
import { ErrorNotice } from "@/components/status";
import { Button } from "@/components/ui/button";
import {
  api,
  errorText,
  type EstimateStories,
  type FeatureStories,
  type QuickSummary,
} from "@/lib/api/client";
import { formatApprox } from "@/lib/format";

import { Chevron, Disclosure } from "./cost-summary";

/** feature key -> its stories, one per line, as being edited */
type Draft = Record<string, string>;

const EDITORS = new Set(["admin", "estimator", "finance"]);

function lines(text: string): string[] {
  return text
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);
}

/**
 * What people can do with each feature (its user stories), beside the feature's building cost:
 * the document's, or the user's own. Without any, the AI can draft them for the user to check.
 * Stories only feed the build-size check: they never change the price.
 */
export function FeatureStoriesSection({
  summary,
  onChange,
}: {
  summary: QuickSummary;
  onChange: (summary: QuickSummary) => void;
}) {
  const user = useCurrentUser();
  const canEdit = EDITORS.has(user.role) && !user.viewed_by_owner;
  const [data, setData] = React.useState<EstimateStories | null>(null);
  const [draft, setDraft] = React.useState<Draft | null>(null);
  const [busy, setBusy] = React.useState<"draft" | "save" | null>(null);
  const [note, setNote] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const id = summary.estimate_id;

  React.useEffect(() => {
    api.getStories(id).then(setData, (e) => setError(errorText(e)));
  }, [id]);

  if (!data || data.features.length === 0) {
    return error ? <ErrorNotice message={error} /> : null;
  }
  const cost = new Map(summary.feature_costs.map((f) => [f.label, f]));
  const money = (paise: number) => formatApprox(paise, summary.currency);
  const total = data.features.reduce((s, f) => s + f.stories.length, 0);
  const missing = data.features.filter((f) => f.stories.length === 0);

  function edit(start?: Draft) {
    setNote(null);
    setError(null);
    setDraft(
      start ??
        Object.fromEntries(
          data!.features.map((f) => [f.key, f.stories.join("\n")]),
        ),
    );
  }

  async function writeForMe() {
    setBusy("draft");
    setNote(null);
    setError(null);
    try {
      const out = await api.draftStories({
        description: data!.description || summary.name,
        features: missing.map((f) => ({ key: f.key, label: f.label })),
      });
      if (!out.available) {
        setNote(out.note ?? null);
        return;
      }
      // the draft opens for checking; nothing is saved until the user saves it
      const start = Object.fromEntries(
        data!.features.map((f) => [
          f.key,
          f.stories.length > 0
            ? f.stories.join("\n")
            : (out.stories[f.key] ?? []).join("\n"),
        ]),
      );
      edit(start);
      setNote("A first draft: check it, change anything wrong, then save.");
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(null);
    }
  }

  async function save() {
    if (!draft) return;
    setBusy("save");
    setError(null);
    try {
      const changed = Object.fromEntries(
        data!.features
          .filter(
            (f) =>
              lines(draft[f.key] ?? "").join("\n") !== f.stories.join("\n"),
          )
          .map((f) => [f.key, lines(draft[f.key] ?? "")]),
      );
      if (Object.keys(changed).length > 0) {
        setData(await api.saveStories(id, changed));
        onChange(await api.getEstimateSummary(id));
      }
      setDraft(null);
      setNote(null);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <Disclosure
      title="What each feature includes"
      icon={ListBulletsIcon}
      hint={
        total > 0
          ? `${total} thing${total === 1 ? "" : "s"} people can do, feature by feature`
          : "Break each feature into what people can do with it"
      }
    >
      <div className="flex flex-col gap-5">
        <p className="max-w-2xl text-sm text-muted-foreground">
          One line per thing a person can do (a user story). They show what each
          feature&apos;s price covers and double-check the size of the build.
          Changing them never changes the price.
        </p>

        {draft ? (
          <div className="flex flex-col gap-4">
            {data.features.map((f) => (
              <label key={f.key} className="flex flex-col gap-2">
                <span className="font-medium">{f.label}</span>
                <textarea
                  value={draft[f.key] ?? ""}
                  onChange={(e) =>
                    setDraft({ ...draft, [f.key]: e.target.value })
                  }
                  rows={Math.min(
                    10,
                    Math.max(2, (draft[f.key] ?? "").split("\n").length),
                  )}
                  placeholder="One line each, e.g. “A candidate can apply for a job”"
                  className="w-full rounded-lg border bg-background px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
                />
              </label>
            ))}
          </div>
        ) : (
          <ul className="flex flex-col divide-y border-y">
            {data.features.map((f) => (
              <FeatureRow
                key={f.key}
                feature={f}
                amount={cost.get(f.label)?.amount_paise ?? null}
                money={money}
              />
            ))}
          </ul>
        )}

        {note ? <p className="text-sm">{note}</p> : null}
        <ErrorNotice message={error} />

        {canEdit ? (
          <div className="flex flex-wrap items-center gap-3">
            {draft ? (
              <>
                <Button onClick={save} disabled={busy !== null}>
                  {busy === "save" ? "Saving…" : "Save"}
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => {
                    setDraft(null);
                    setNote(null);
                  }}
                  disabled={busy !== null}
                >
                  Cancel
                </Button>
              </>
            ) : (
              <>
                {missing.length > 0 && data.can_draft ? (
                  <Button onClick={writeForMe} disabled={busy !== null}>
                    {busy === "draft"
                      ? "Writing…"
                      : "Break it into user stories"}
                  </Button>
                ) : null}
                <Button
                  variant="outline"
                  onClick={() => edit()}
                  disabled={busy !== null}
                >
                  {total > 0 ? "Edit" : "Write them myself"}
                </Button>
              </>
            )}
          </div>
        ) : null}
      </div>
    </Disclosure>
  );
}

/** One feature: its cost, and its stories on request. */
function FeatureRow({
  feature,
  amount,
  money,
}: {
  feature: FeatureStories;
  amount: number | null;
  money: (paise: number) => string;
}) {
  const count = feature.stories.length;
  return (
    <li className="py-3">
      <details className="group/story">
        <summary
          className={
            count > 0
              ? "flex cursor-pointer list-none flex-wrap items-baseline justify-between gap-x-4 gap-y-1 [&::-webkit-details-marker]:hidden"
              : "pointer-events-none flex list-none flex-wrap items-baseline justify-between gap-x-4 gap-y-1 [&::-webkit-details-marker]:hidden"
          }
        >
          <span className="flex flex-col gap-0.5">
            <span className="font-medium">{feature.label}</span>
            <span className="inline-flex items-center gap-1 text-sm text-muted-foreground">
              {count > 0 ? (
                <>
                  <span className="inline-block transition-transform group-open/story:rotate-90">
                    <Chevron />
                  </span>
                  What people can do ({count})
                  {feature.source === "document" ? " · from the document" : ""}
                </>
              ) : (
                "No user stories yet"
              )}
            </span>
          </span>
          {amount !== null ? (
            <span className="font-medium tabular-nums">{money(amount)}</span>
          ) : null}
        </summary>
        {count > 0 ? (
          <ul className="mt-3 flex list-disc flex-col gap-1 pl-9 text-sm text-muted-foreground">
            {feature.stories.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        ) : null}
      </details>
    </li>
  );
}
