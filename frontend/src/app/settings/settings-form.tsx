"use client";

import * as React from "react";

import { ErrorNotice, Loading } from "@/components/status";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import {
  api,
  ApiError,
  errorText,
  type CompanySettings,
  type RoleRate,
} from "@/lib/api/client";
import { formatPaise } from "@/lib/format";
import { useLoad } from "@/lib/use-load";

// Range the server accepts for the effort adjustments.
const EFFORT_MIN = 0.3;
const EFFORT_MAX = 3;
const CUSTOM = "custom";

const AI_CHOICES = [
  { value: "", label: "Typical for 2026 (medium)" },
  { value: "none", label: "We don't use AI tools" },
  { value: "low", label: "A little (some developers, sometimes)" },
  { value: "medium", label: "Regularly (most developers, most days)" },
  { value: "high", label: "Heavily (AI in every step of our work)" },
];

const EFFORT_CHOICES = [
  { value: "0.6", label: "Very lean" },
  { value: "0.8", label: "Lean" },
  { value: "1", label: "Typical" },
  { value: "1.2", label: "Thorough" },
  { value: "1.5", label: "Very thorough" },
];

/** "0.15" (a fraction from the API) → "15" for the percent box; null → "". */
function percentText(fraction: string | null | undefined): string {
  if (fraction === null || fraction === undefined) return "";
  return String(Number((Number(fraction) * 100).toFixed(4)));
}

/** "15" → "0.15"; "" → null. Throws a plain message when the number is not usable. */
function percentToFraction(text: string, what: string): string | null {
  if (text.trim() === "") return null;
  const n = Number(text);
  if (!Number.isFinite(n) || n < 0 || n > 100) {
    throw new Error(`${what} must be a number between 0 and 100.`);
  }
  return String(Number((n / 100).toFixed(6)));
}

interface EffortState {
  choice: string;
  custom: string;
}

function effortState(value: string): EffortState {
  const n = Number(value);
  const preset = EFFORT_CHOICES.find((c) => Number(c.value) === n);
  return preset
    ? { choice: preset.value, custom: "" }
    : { choice: CUSTOM, custom: String(n) };
}

type CompanySettingsAi = "none" | "low" | "medium" | "high" | null;

/** Own day rates that were filled in (rupees); throws a plain message for a bad number. */
type RateUnit = "day" | "hour";

/** Rates as typed (per day or per hour) -> day rates for the API (hour × hours per day). */
function roleRates(
  rates: Record<string, string>,
  roles: RoleRate[],
  unit: RateUnit,
): Record<string, string> {
  const out: Record<string, string> = {};
  for (const role of roles) {
    const text = (rates[role.key] ?? "").trim();
    if (text === "") continue;
    const n = Number(text);
    if (!Number.isFinite(n) || n <= 0) {
      throw new Error(
        `${role.label}: enter a rate per ${unit} in rupees, or leave it empty.`,
      );
    }
    out[role.key] = String(unit === "hour" ? n * role.hours_per_day : n);
  }
  return out;
}

/** Re-express the typed rates when the unit changes (rounded to whole rupees). */
function convertRates(
  rates: Record<string, string>,
  roles: RoleRate[],
  to: RateUnit,
): Record<string, string> {
  const out: Record<string, string> = {};
  for (const role of roles) {
    const n = Number((rates[role.key] ?? "").trim());
    out[role.key] =
      (rates[role.key] ?? "").trim() === "" || !Number.isFinite(n)
        ? (rates[role.key] ?? "")
        : String(
            Math.round(
              to === "hour" ? n / role.hours_per_day : n * role.hours_per_day,
            ),
          );
  }
  return out;
}

function effortValue(state: EffortState, what: string): string {
  const text = state.choice === CUSTOM ? state.custom : state.choice;
  const n = Number(text);
  if (
    text.trim() === "" ||
    !Number.isFinite(n) ||
    n < EFFORT_MIN ||
    n > EFFORT_MAX
  ) {
    throw new Error(
      `${what}: enter a number between ${EFFORT_MIN} and ${EFFORT_MAX} (1 is typical).`,
    );
  }
  return String(n);
}

function EffortField({
  id,
  label,
  help,
  value,
  onChange,
}: {
  id: string;
  label: string;
  help: string;
  value: EffortState;
  onChange: (value: EffortState) => void;
}) {
  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor={id}>{label}</Label>
      <div className="flex flex-wrap items-center gap-3">
        <Select
          id={id}
          className="w-56"
          value={value.choice}
          onChange={(e) => onChange({ ...value, choice: e.target.value })}
        >
          {EFFORT_CHOICES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label} ({c.value}×)
            </option>
          ))}
          <option value={CUSTOM}>My own number</option>
        </Select>
        {value.choice === CUSTOM ? (
          <Input
            aria-label={`${label} (own number)`}
            inputMode="decimal"
            className="w-28"
            placeholder="e.g. 0.9"
            value={value.custom}
            onChange={(e) => onChange({ ...value, custom: e.target.value })}
          />
        ) : null}
      </div>
      <span className="text-sm text-muted-foreground">{help}</span>
    </div>
  );
}

/** "4749.00" rupees -> "4749"; empty when not set. */
function rupeesText(value: string | undefined): string {
  return value === undefined ? "" : String(Number(value));
}

function Form({
  initial,
  roles,
}: {
  initial: CompanySettings;
  roles: RoleRate[];
}) {
  const [aiLevel, setAiLevel] = React.useState(initial.team_ai_maturity ?? "");
  const [rates, setRates] = React.useState<Record<string, string>>(() =>
    Object.fromEntries(
      roles.map((r) => [r.key, rupeesText(initial.role_day_rates?.[r.key])]),
    ),
  );
  const [margin, setMargin] = React.useState(
    percentText(initial.margin_percent),
  );
  const [buffer, setBuffer] = React.useState(
    percentText(initial.contingency_percent),
  );
  const [build, setBuild] = React.useState(
    effortState(initial.build_effort_multiplier),
  );
  const [support, setSupport] = React.useState(
    effortState(initial.support_effort_multiplier),
  );
  const [unit, setUnit] = React.useState<RateUnit>("day");
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [saved, setSaved] = React.useState(false);

  async function save(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setSaved(false);
    let body;
    try {
      body = {
        margin_percent: percentToFraction(margin, "Profit margin"),
        contingency_percent: percentToFraction(buffer, "Safety buffer"),
        build_effort_multiplier: effortValue(build, "Building"),
        support_effort_multiplier: effortValue(support, "Support"),
        team_ai_maturity: (aiLevel || null) as CompanySettingsAi,
        role_day_rates: roleRates(rates, roles, unit),
      };
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      return;
    }
    setSaving(true);
    try {
      await api.putSettings(body);
      setSaved(true);
    } catch (e) {
      setError(
        e instanceof ApiError && e.status === 403
          ? "Only an administrator can change these settings."
          : errorText(e),
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <form
      onSubmit={save}
      className="flex flex-col gap-6 rounded-2xl border bg-card px-6 py-6 shadow-sm sm:px-8"
    >
      <div className="flex flex-col gap-2">
        <Label htmlFor="margin">Your profit margin (%)</Label>
        <Input
          id="margin"
          inputMode="decimal"
          className="w-28"
          placeholder="Default"
          value={margin}
          onChange={(e) => {
            setMargin(e.target.value);
            setSaved(false);
          }}
        />
        <span className="text-sm text-muted-foreground">
          Leave empty to use the default: 15% for India, 10% for the US.
        </span>
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="buffer">Safety buffer (%)</Label>
        <Input
          id="buffer"
          inputMode="decimal"
          className="w-28"
          placeholder="Automatic"
          value={buffer}
          onChange={(e) => {
            setBuffer(e.target.value);
            setSaved(false);
          }}
        />
        <span className="text-sm text-muted-foreground">
          Extra money set aside for surprises. Leave empty and we choose it from
          how clear the requirements are.
        </span>
      </div>

      <EffortField
        id="build-effort"
        label="How lean is your team for building?"
        help="A leaner team needs fewer working days to build the same thing."
        value={build}
        onChange={(v) => {
          setBuild(v);
          setSaved(false);
        }}
      />

      <EffortField
        id="support-effort"
        label="How lean is your team for support and maintenance?"
        help="The same idea for looking after the software once it is live."
        value={support}
        onChange={(v) => {
          setSupport(v);
          setSaved(false);
        }}
      />

      <div className="flex flex-col gap-2">
        <Label htmlFor="ai-level">How much does your team use AI tools?</Label>
        <Select
          id="ai-level"
          className="w-80"
          value={aiLevel}
          onChange={(e) => {
            setAiLevel(e.target.value);
            setSaved(false);
          }}
        >
          {AI_CHOICES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </Select>
        <span className="text-sm text-muted-foreground">
          More AI use means fewer working days to build the same thing.
        </span>
      </div>

      <fieldset className="flex flex-col gap-3 border-t pt-5">
        <legend className="font-medium">
          Your team&apos;s rates (₹ per{" "}
          {unit === "day" ? "working day" : "hour"})
        </legend>
        <p className="text-sm text-muted-foreground">
          What one person costs your company (salary plus office and overheads),
          or what you charge, per day or per hour. A working day is{" "}
          {roles[0]?.hours_per_day ?? 8} hours. Leave a role empty to use the
          market average shown.
        </p>
        <div
          role="radiogroup"
          aria-label="Rate unit"
          className="inline-flex w-fit rounded-full border bg-card p-1"
        >
          {(["day", "hour"] as const).map((u) => (
            <button
              key={u}
              type="button"
              role="radio"
              aria-checked={unit === u}
              onClick={() => {
                if (u === unit) return;
                setRates((r) => convertRates(r, roles, u));
                setUnit(u);
                setSaved(false);
              }}
              className={
                unit === u
                  ? "rounded-full bg-foreground px-4 py-1.5 text-sm font-semibold text-primary-foreground"
                  : "rounded-full px-4 py-1.5 text-sm font-medium text-muted-foreground hover:text-foreground"
              }
            >
              Per {u}
            </button>
          ))}
        </div>
        <div className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
          {roles.map((role) => (
            <div key={role.key} className="flex flex-col gap-1">
              <Label htmlFor={`rate-${role.key}`}>{role.label}</Label>
              <Input
                id={`rate-${role.key}`}
                inputMode="decimal"
                className="w-40"
                placeholder={String(
                  Math.round(
                    unit === "day"
                      ? Number(role.market_rupees_per_day)
                      : Number(role.market_rupees_per_day) / role.hours_per_day,
                  ),
                )}
                value={rates[role.key] ?? ""}
                onChange={(e) => {
                  setRates((r) => ({ ...r, [role.key]: e.target.value }));
                  setSaved(false);
                }}
              />
              <span className="text-xs text-muted-foreground">
                Market average{" "}
                {formatPaise(
                  Math.round(
                    unit === "day"
                      ? Number(role.market_rupees_per_day)
                      : Number(role.market_rupees_per_day) / role.hours_per_day,
                  ) * 100,
                )}{" "}
                per {unit}
              </span>
            </div>
          ))}
        </div>
      </fieldset>

      <div className="flex flex-col gap-3 border-t pt-5">
        <p className="text-sm text-muted-foreground">
          These apply to new estimates only. Past estimates never change.
        </p>
        {error ? <ErrorNotice message={error} /> : null}
        {saved ? (
          <p role="status" className="text-sm font-medium text-success">
            Saved. New estimates will use these settings.
          </p>
        ) : null}
        <Button type="submit" className="w-fit" disabled={saving}>
          {saving ? "Saving…" : "Save settings"}
        </Button>
      </div>
    </form>
  );
}

export function SettingsForm() {
  const loader = React.useCallback(
    () => Promise.all([api.getSettings(), api.getRoleRates()]),
    [],
  );
  const { state } = useLoad(loader);
  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          How your company prices its work.
        </p>
      </div>
      {state.kind === "loading" ? <Loading /> : null}
      {state.kind === "error" ? <ErrorNotice message={state.message} /> : null}
      {state.kind === "ready" ? (
        <Form initial={state.data[0]} roles={state.data[1]} />
      ) : null}
    </div>
  );
}
