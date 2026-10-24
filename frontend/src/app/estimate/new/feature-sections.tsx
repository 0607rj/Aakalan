"use client";

import * as React from "react";

import type { NotIncluded, QuickOptions, QuickRequest } from "@/lib/api/client";
import { cn } from "@/lib/utils";

import {
  CustomFeaturesSection,
  type CustomItem,
  ResearchedFeatures,
} from "./custom-features";
import {
  type Choice,
  FeatureCard,
  SectionHeading,
  StandardBlocks,
} from "./parts";

/**
 * Ticking, unticking and "Not included" for features, the same on the manual form and the
 * upload review. A feature a question adds (mobile app, other software, old data) is ticked
 * through that question: ticking sets its usual answer (the first that adds the feature),
 * unticking the first plain answer without it; the question screen still changes its size.
 */
export function featureTicks({
  options,
  features,
  setFeatures,
  everything,
  notIncluded,
  setNotIncluded,
}: {
  options: QuickOptions;
  features: string[];
  setFeatures: React.Dispatch<React.SetStateAction<string[]>>;
  /** Every priced feature: the ticked ones plus those the answers add. */
  everything: string[];
  notIncluded: NotIncluded[];
  setNotIncluded: React.Dispatch<React.SetStateAction<NotIncluded[]>>;
}) {
  const hidden = new Set(
    options.features.filter((f) => f.hidden).map((f) => f.key),
  );
  const isOut = (kind: NotIncluded["kind"], key: string) =>
    notIncluded.some((n) => n.kind === kind && n.key === key);
  const unmark = (kind: NotIncluded["kind"], key: string) =>
    setNotIncluded((now) =>
      now.filter((n) => !(n.kind === kind && n.key === key)),
    );
  return {
    isOut,
    unmark,
    isTicked: (key: string) =>
      hidden.has(key) ? everything.includes(key) : features.includes(key),
    /** `change` answers a question (given at click time, not during render). */
    tick(key: string, change: (question: string, value: Choice) => void) {
      if (hidden.has(key)) {
        const q = options.questions.find((x) =>
          x.options.some((o) => key in (o.add_features ?? {})),
        );
        const on = everything.includes(key);
        const option = q?.options.find(
          (o) => key in (o.add_features ?? {}) !== on && !o.unsure,
        );
        if (q && option) change(q.key, option.value);
      } else {
        setFeatures((now) =>
          now.includes(key) ? now.filter((k) => k !== key) : [...now, key],
        );
      }
      unmark("feature", key);
    },
    toggleOut(kind: NotIncluded["kind"], key: string) {
      if (isOut(kind, key)) unmark(kind, key);
      else setNotIncluded((now) => [...now, { kind, key, quote: "" }]);
    },
  };
}

/** What is sent: a feature or scope item an answer still prices (e.g. an app) is not "out". */
export function sentNotIncluded(
  notIncluded: NotIncluded[],
  everything: string[],
  pricedScope: string[],
): NotIncluded[] {
  return notIncluded.filter((n) =>
    n.kind === "feature"
      ? !everything.includes(n.key)
      : n.kind === "scope"
        ? !pricedScope.includes(n.key)
        : true,
  );
}

/** The "Not included" line on the check screen. */
export function notIncludedText(
  options: QuickOptions,
  notIncluded: NotIncluded[],
): string {
  const scopeItems = (options.scope ?? []).flatMap((g) => g.items);
  const blocks = notIncluded.filter((n) => n.kind === "standard").length;
  return (
    [
      ...notIncluded
        .filter((n) => n.kind === "feature")
        .map(
          (n) => options.features.find((f) => f.key === n.key)?.label ?? n.key,
        ),
      ...notIncluded
        .filter((n) => n.kind === "scope")
        .map((n) => scopeItems.find((i) => i.key === n.key)?.label ?? n.key),
      ...(blocks > 0
        ? [`${blocks} standard part${blocks === 1 ? "" : "s"} left out`]
        : []),
    ].join(", ") || "Nothing marked"
  );
}

/** One feature from the list, with its three states; `children` say where it came from. */
export function FeatureChoice({
  options,
  featureKey,
  ticks,
  onTick,
  notIncluded,
  children,
}: {
  options: QuickOptions;
  featureKey: string;
  ticks: ReturnType<typeof featureTicks>;
  /** Tick or untick: `ticks.tick` with the form's answer handler. */
  onTick: (key: string) => void;
  notIncluded: NotIncluded[];
  children?: React.ReactNode;
}) {
  const feature = options.features.find((f) => f.key === featureKey);
  if (!feature) return null;
  const out = notIncluded.find(
    (n) => n.kind === "feature" && n.key === featureKey,
  );
  return (
    <FeatureCard
      label={feature.label}
      hint={feature.hint}
      checked={ticks.isTicked(featureKey)}
      onToggle={() => onTick(featureKey)}
      excluded={out !== undefined}
      onNotIncluded={() => ticks.toggleOut("feature", featureKey)}
    >
      {children}
    </FeatureCard>
  );
}

/** Not found by us and not added by the user: from neither the description nor the document. */
const isOwn = (i: CustomItem) =>
  i.fromDescription === undefined && i.foundIndex === null;

/**
 * The features screen, the same for a description and a document: found (with where each came
 * from), included by default, a short list nothing mentioned, browse all (closed), add your own.
 */
export function FeatureSections({
  options,
  foundTitle,
  foundKeys,
  foundCount,
  found,
  foundNote,
  emptyHint,
  card,
  isTicked,
  kindFeatures = [],
  blocksBody,
  removedBlocks,
  onToggleBlock,
  customItems,
  onCustomItems,
  approximatePages = false,
}: {
  options: QuickOptions;
  foundTitle: string;
  /** Features from the list that were found (they leave the short list and browse all). */
  foundKeys: string[];
  foundCount: number;
  /** The found cards. */
  found: React.ReactNode;
  /** Under the found cards (e.g. asked for but not priced). */
  foundNote?: React.ReactNode;
  emptyHint: string;
  card: (key: string) => React.ReactNode;
  isTicked: (key: string) => boolean;
  /** The kind of software's usual features: only the short list's order. */
  kindFeatures?: string[];
  /** The request for the standard blocks; null until it can be priced. */
  blocksBody: QuickRequest | null;
  removedBlocks: string[];
  onToggleBlock: (key: string) => void;
  customItems: CustomItem[];
  onCustomItems: React.Dispatch<React.SetStateAction<CustomItem[]>>;
  approximatePages?: boolean;
}) {
  // "Browse all features" starts closed
  const [showAll, setShowAll] = React.useState(false);
  const rank = (key: string) => {
    const i = kindFeatures.indexOf(key);
    return i < 0 ? Number.MAX_SAFE_INTEGER : i;
  };
  const shortlist = (options.commonly_needed ?? [])
    .filter((k) => !foundKeys.includes(k))
    .sort((a, b) => rank(a) - rank(b));
  const browse = options.features.filter(
    (f) =>
      !f.hidden && !foundKeys.includes(f.key) && !shortlist.includes(f.key),
  );
  const browseTicked = browse.filter((f) => isTicked(f.key)).length;

  return (
    <>
      {foundCount > 0 || foundNote ? (
        <section className="flex flex-col gap-3">
          <SectionHeading title={foundTitle} count={foundCount} />
          {foundCount > 0 ? (
            <div className="grid gap-3 sm:grid-cols-2">{found}</div>
          ) : null}
          {foundNote}
        </section>
      ) : (
        <p className="text-sm text-muted-foreground">{emptyHint}</p>
      )}

      <StandardBlocks
        body={blocksBody}
        removed={removedBlocks}
        onToggle={onToggleBlock}
      />

      {shortlist.length > 0 ? (
        <section className="flex flex-col gap-3">
          <SectionHeading
            title="Not mentioned: do you need these?"
            count={shortlist.length}
          />
          <div className="grid gap-3 sm:grid-cols-2">
            {shortlist.map((key) => (
              <React.Fragment key={key}>{card(key)}</React.Fragment>
            ))}
          </div>
        </section>
      ) : null}

      <section className="flex flex-col gap-3">
        <button
          type="button"
          onClick={() => setShowAll((v) => !v)}
          aria-expanded={showAll}
          className="flex w-full flex-wrap items-baseline justify-between gap-x-4 border-b pb-2 text-left"
        >
          <span className="text-base font-semibold">
            <svg
              aria-hidden="true"
              viewBox="0 0 16 16"
              className={cn(
                "mr-1.5 inline-block size-3.5 align-[-2px] transition-transform duration-300",
                showAll && "rotate-90",
              )}
              fill="none"
              stroke="currentColor"
              strokeWidth="1.75"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M6 3.5 10.5 8 6 12.5" />
            </svg>
            Browse all features
            <span className="ml-2 text-muted-foreground tabular-nums">
              ({browse.length})
            </span>
          </span>
          {browseTicked > 0 ? (
            <span className="text-sm text-muted-foreground">
              {browseTicked} ticked
            </span>
          ) : null}
        </button>
        {showAll ? (
          <>
            <div className="grid gap-3 sm:grid-cols-2">
              {browse.map((f) => (
                <React.Fragment key={f.key}>{card(f.key)}</React.Fragment>
              ))}
            </div>
            <ResearchedFeatures
              researched={options.researched ?? []}
              items={customItems}
              onChange={onCustomItems}
            />
          </>
        ) : null}
      </section>

      <section className="flex flex-col gap-3">
        <SectionHeading title="Something missing? Add your own" />
        <CustomFeaturesSection
          items={customItems.filter(isOwn)}
          onChange={(next) =>
            onCustomItems((now) => [...now.filter((i) => !isOwn(i)), ...next])
          }
          types={options.custom_feature_types}
          approximatePages={approximatePages}
        />
      </section>
    </>
  );
}
