"use client";

import * as React from "react";

import { ErrorNotice } from "@/components/status";
import { Button } from "@/components/ui/button";
import { api, errorText } from "@/lib/api/client";

/** feature key (or a custom feature's name) -> its user stories, one per line as typed */
export type StoryText = Record<string, string>;

export type StoryFeature = { key: string; label: string };

/** The stories sent with the estimate: non-empty lines, for the features still chosen. */
export function sentStories(
  text: StoryText,
  features: StoryFeature[],
): Record<string, string[]> {
  const out: Record<string, string[]> = {};
  for (const f of features) {
    const lines = (text[f.key] ?? "")
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean);
    if (lines.length > 0) out[f.key] = lines;
  }
  return out;
}

/**
 * Optional: what people can do with each feature, one line each. The AI can write a first
 * draft from the description; the user edits it. The stories only double-check the size of
 * the build on the results page: they never change the price.
 */
export function StoriesStep({
  features,
  description,
  text,
  onChange,
}: {
  features: StoryFeature[];
  description: string;
  text: StoryText;
  onChange: (text: StoryText) => void;
}) {
  const [busy, setBusy] = React.useState(false);
  const [note, setNote] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  async function draft() {
    setBusy(true);
    setError(null);
    setNote(null);
    try {
      const out = await api.draftStories({ description, features });
      if (!out.available) {
        setNote(out.note ?? null);
        return;
      }
      // a feature the user already wrote for keeps their words
      const next = { ...text };
      for (const [key, stories] of Object.entries(out.stories)) {
        if (!(next[key] ?? "").trim()) next[key] = stories.join("\n");
      }
      onChange(next);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
          What can people do with it?
        </h1>
        <p className="mt-1 text-muted-foreground">
          Optional. One line per thing a person can do, e.g. “A patient can book
          an appointment”. We use these to double-check the size of the build.
          They don’t change the price.
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <Button variant="outline" onClick={draft} disabled={busy}>
          {busy ? "Writing…" : "Write them for me"}
        </Button>
        <span className="text-sm text-muted-foreground">
          A first draft from your description: check and edit it.
        </span>
      </div>
      {note ? <p className="text-sm">{note}</p> : null}
      <ErrorNotice message={error} />
      <div className="flex flex-col gap-5">
        {features.map((f) => (
          <label key={f.key} className="flex flex-col gap-2">
            <span className="text-base font-medium">{f.label}</span>
            <textarea
              value={text[f.key] ?? ""}
              onChange={(e) => onChange({ ...text, [f.key]: e.target.value })}
              rows={Math.min(
                8,
                Math.max(2, (text[f.key] ?? "").split("\n").length),
              )}
              placeholder="One line each"
              className="w-full rounded-lg border bg-background px-3 py-2 text-sm"
            />
          </label>
        ))}
      </div>
    </section>
  );
}
