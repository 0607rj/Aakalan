"use client";

import * as React from "react";
import { HandCoinsIcon } from "@phosphor-icons/react/dist/ssr";

import { FormError, failure } from "@/components/auth-forms";
import { useCurrentUser } from "@/components/auth-guard";
import { IconTile } from "@/components/site/illustrations";
import { api, type CompanySettings } from "@/lib/api/client";
import { cn } from "@/lib/utils";

type Passthrough = NonNullable<CompanySettings["ai_passthrough"]>;

// The answers of the quick estimate's `ai_passthrough` question (backend quick_estimate.yaml).
const CHOICES: { value: Passthrough; label: string; hint: string }[] = [
  {
    value: "all",
    label: "All of it",
    hint: "Lowest price. Best when you must win on price, such as a competitive or government tender.",
  },
  {
    value: "most",
    label: "Most of it (75%)",
    hint: "Still a competitive price, with a little extra margin.",
  },
  { value: "half", label: "Half", hint: "Between the two." },
  {
    value: "keep",
    label: "Keep it",
    hint: "For private or negotiated work: the price stays at the usual level and the saving is your margin.",
  },
];

const EDITORS = new Set(["admin", "finance"]);

/** How much of the AI saving the company's prices pass on: one company setting, used by every
 * new estimate (it used to be asked on every estimate). */
export function AiSavingSetting() {
  const user = useCurrentUser();
  const canEdit = EDITORS.has(user.role);
  const [settings, setSettings] = React.useState<CompanySettings | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [saved, setSaved] = React.useState(false);
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    api.getSettings().then(setSettings, (err) => setError(failure(err)));
  }, []);

  const current: Passthrough = settings?.ai_passthrough ?? "all";

  async function choose(value: Passthrough) {
    if (!settings || value === current) return;
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      setSettings(
        await api.putSettings({ ...settings, ai_passthrough: value }),
      );
      setSaved(true);
    } catch (err) {
      setError(failure(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="slab flex w-full max-w-xl flex-col gap-6 p-6 sm:p-8">
      <div className="flex items-center gap-3">
        <IconTile icon={HandCoinsIcon} />
        <div className="flex flex-col gap-0.5">
          <h2 className="text-xl font-semibold">AI saving</h2>
          <p className="text-sm text-muted-foreground">
            AI tools make the build cheaper. How much of that saving do your
            prices pass on to the client? Used for every new estimate.
          </p>
        </div>
      </div>
      <fieldset
        className="flex flex-col gap-2"
        disabled={!canEdit || busy || !settings}
      >
        <legend className="sr-only">AI saving passed on to the client</legend>
        {CHOICES.map((c) => (
          <label
            key={c.value}
            className={cn(
              "flex cursor-pointer gap-3 rounded-lg border p-3.5 transition-colors",
              c.value === current
                ? "border-tape bg-tape-soft"
                : "hover:bg-muted/50",
              (!canEdit || !settings) && "cursor-default",
            )}
          >
            <input
              type="radio"
              name="ai-passthrough"
              value={c.value}
              checked={c.value === current}
              onChange={() => choose(c.value)}
              className="mt-1 accent-[var(--tape)]"
            />
            <span className="flex flex-col gap-0.5">
              <span className="font-medium">{c.label}</span>
              <span className="text-sm text-muted-foreground">{c.hint}</span>
            </span>
          </label>
        ))}
      </fieldset>
      {!canEdit ? (
        <p className="text-sm text-muted-foreground">
          Only finance or an admin can change this.
        </p>
      ) : null}
      <FormError message={error} />
      {saved ? (
        <p
          role="status"
          className="rounded-lg border border-success/25 bg-success/5 px-3.5 py-2.5 text-sm text-success"
        >
          Saved. New estimates use it.
        </p>
      ) : null}
    </section>
  );
}
