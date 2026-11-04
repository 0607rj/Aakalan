"use client";

import * as React from "react";

import { LevelSwitch } from "@/components/level-switch";
import { Button } from "@/components/ui/button";
import {
  api,
  type IndustrySuggestion,
  type QuickOptions,
  type QuickRequest,
  type SuggestionPrice,
} from "@/lib/api/client";
import { formatApprox } from "@/lib/format";

import type { CustomItem } from "./custom-features";
import { FeatureCard, SectionHeading } from "./parts";
import type { Level } from "./steps";

const LEVELS: { key: Level; label: string }[] = [
  { key: "basic", label: "Basic" },
  { key: "standard", label: "Standard" },
  { key: "advanced", label: "Advanced" },
];
// a module the list lacks is sized S / M / L; shown with the same three words
const SIZE_LEVEL: Record<CustomItem["size"], Level> = {
  S: "basic",
  M: "standard",
  L: "advanced",
};
const LEVEL_SIZE: Record<Level, CustomItem["size"]> = {
  basic: "S",
  standard: "M",
  advanced: "L",
};

/** Basic / standard / advanced for a ticked suggestion; nothing picked = the usual level. */
function LevelPicker({
  name,
  value,
  onChange,
}: {
  name: string;
  value: Level | null;
  onChange: (level: Level) => void;
}) {
  return (
    // a click here picks a level, it does not untick the card
    <div className="w-fit" onClick={(e) => e.stopPropagation()}>
      <LevelSwitch
        name={name}
        label="How big"
        options={LEVELS}
        value={value}
        onChange={onChange}
        size="sm"
      />
    </div>
  );
}

const PRICE_DEBOUNCE_MS = 600;
const COPIED_MS = 2000;

/** A suggestion's key in the price list and on the screen. */
const idOf = (s: { feature: string; label: string }) =>
  s.feature || `custom:${s.label.toLowerCase()}`;

/**
 * "Usually needed for this kind of software" (OPEN_QUESTIONS 207): modules the AI says software
 * like this usually has and the words never mention, checked in code. Never ticked for the
 * user; what each adds is priced by the engine (the form with and without it). On a document,
 * each can be copied as a pre-bid question to ask the client first.
 */
export function IndustrySuggestions({
  options,
  suggestions,
  domain,
  forDocument,
  body,
  hiddenKeys,
  isTicked,
  onTick,
  customItems,
  onCustomItems,
  fromIndustry = false,
  levels,
  onLevel,
}: {
  options: QuickOptions;
  suggestions: IndustrySuggestion[];
  domain: string;
  forDocument: boolean;
  /** The form as it stands, for the prices; null until it can be priced. */
  body: QuickRequest | null;
  /** Already found: not suggested again. */
  hiddenKeys: string[];
  isTicked: (key: string) => boolean;
  onTick: (key: string) => void;
  customItems: CustomItem[];
  onCustomItems: React.Dispatch<React.SetStateAction<CustomItem[]>>;
  /** The picked industry's list on the manual form, not the AI's (OPEN_QUESTIONS 212). */
  fromIndustry?: boolean;
  levels?: Record<string, Level>;
  onLevel?: (key: string, level: Level) => void;
}) {
  const shown = suggestions.filter(
    (s) => !s.feature || !hiddenKeys.includes(s.feature),
  );
  const [prices, setPrices] = React.useState<Record<string, SuggestionPrice>>(
    {},
  );
  const [copied, setCopied] = React.useState<string | null>(null);
  const key = body && shown.length > 0 ? JSON.stringify({ body, shown }) : null;
  React.useEffect(() => {
    if (key === null) return;
    const { body: form, shown: items } = JSON.parse(key) as {
      body: QuickRequest;
      shown: IndustrySuggestion[];
    };
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      api
        .suggestionPrices(form, items, controller.signal)
        .then((list) =>
          setPrices(Object.fromEntries(list.map((p) => [idOf(p), p]))),
        )
        .catch(() => {
          // Keep the previous prices silently.
        });
    }, PRICE_DEBOUNCE_MS);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [key]);

  if (shown.length === 0) return null;

  const customAdded = (s: IndustrySuggestion) =>
    customItems.some(
      (i) => i.suggested !== undefined && i.name === s.label && i.included,
    );
  const toggleCustom = (s: IndustrySuggestion) =>
    onCustomItems((now) =>
      customAdded(s)
        ? now.filter((i) => !(i.suggested !== undefined && i.name === s.label))
        : [
            ...now,
            {
              id: `suggested-${idOf(s)}`,
              name: s.label,
              category: s.category,
              size: (s.size || "M") as CustomItem["size"],
              foundIndex: null,
              description: s.why,
              evidence: [],
              included: true,
              suggested: s.why,
              catalogKey: s.catalog_key || null,
            },
          ],
    );
  const copy = async (s: IndustrySuggestion) => {
    const text = `The document does not mention ${s.label.toLowerCase()}. Please confirm whether it is required within the scope of work.`;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(idOf(s));
      window.setTimeout(() => setCopied(null), COPIED_MS);
    } catch {
      // Clipboard blocked: nothing to do.
    }
  };
  const kind = domain ? `${domain} software` : "software like this";
  // a ticked one's level: a listed feature's own levels, a module's size (OPEN_QUESTIONS 212)
  const levelOf = (s: IndustrySuggestion): Level | null => {
    if (s.feature) return levels?.[s.feature] ?? null;
    const item = customItems.find(
      (i) => i.suggested !== undefined && i.name === s.label,
    );
    return item ? SIZE_LEVEL[item.size] : null;
  };
  const setLevel = (s: IndustrySuggestion, level: Level) => {
    if (s.feature) {
      onLevel?.(s.feature, level);
      return;
    }
    onCustomItems((now) =>
      now.map((i) =>
        i.suggested !== undefined && i.name === s.label
          ? { ...i, size: LEVEL_SIZE[level] }
          : i,
      ),
    );
  };
  const canLevel = (s: IndustrySuggestion) =>
    onLevel !== undefined &&
    (!s.feature ||
      (options.features.find((f) => f.key === s.feature)?.levels.length ?? 0) >
        0);

  return (
    <section className="flex flex-col gap-3">
      <SectionHeading
        title={
          fromIndustry
            ? `Popular for ${kind}`
            : forDocument
              ? `Not in the document, but common for ${kind}`
              : `Not in your description, but ${kind} usually has these`
        }
        count={shown.length}
        aside="tick only what you need"
      />
      <p className="text-sm text-muted-foreground">
        {fromIndustry
          ? "What software for this industry usually has, and what the AI adds from your description. The main ones are ticked for you: untick any you do not need, and pick how big each one is. Login, user roles and the admin panel are always included."
          : forDocument
            ? "Suggested by the AI from the kind of software, not asked for by the client. Check with the client before adding any to a bid."
            : "Suggested by the AI from the kind of software. Nothing is added unless you tick it."}
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        {shown.map((s) => {
          const id = idOf(s);
          const checked = s.feature ? isTicked(s.feature) : customAdded(s);
          const price = prices[id]?.adds_paise;
          const catalog = options.features.find((f) => f.key === s.feature);
          return (
            <FeatureCard
              key={id}
              label={s.label}
              hint={
                s.feature
                  ? (catalog?.hint ?? "")
                  : "Custom: priced from a general size estimate, less certain"
              }
              checked={checked}
              onToggle={() => (s.feature ? onTick(s.feature) : toggleCustom(s))}
            >
              <p className="text-sm">{s.why}</p>
              {checked && canLevel(s) ? (
                <LevelPicker
                  name={`level-${id}`}
                  value={levelOf(s)}
                  onChange={(level) => setLevel(s, level)}
                />
              ) : null}
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
                {price !== undefined && price !== null && !checked ? (
                  <span className="font-medium tabular-nums">
                    {price > 0
                      ? `adds ${formatApprox(price)}`
                      : "no extra cost: your other features already cover it"}
                  </span>
                ) : null}
                {forDocument ? (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-7 px-2"
                    onClick={() => void copy(s)}
                  >
                    {copied === id ? "Copied" : "Copy as pre-bid question"}
                  </Button>
                ) : null}
              </div>
            </FeatureCard>
          );
        })}
      </div>
    </section>
  );
}
