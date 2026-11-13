"use client";

import * as React from "react";
import { ScalesIcon, TrashIcon } from "@phosphor-icons/react/dist/ssr";

import { useCurrentUser } from "@/components/auth-guard";
import { ErrorNotice, Loading } from "@/components/status";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  api,
  downloadFile,
  errorText,
  type QuoteIn,
  type QuoteOut,
  type QuotesOut,
} from "@/lib/api/client";
import { currencySymbol, formatPaise, formatRange } from "@/lib/format";
import { useLoad } from "@/lib/use-load";
import { cn } from "@/lib/utils";

import { Disclosure } from "./cost-summary";

/*
 * Compare quotes (OPEN_QUESTIONS 241): prices someone quoted, typed in, each placed against
 * this estimate's range before tax. The backend decides below / in / above; this page only
 * draws it. Nothing here changes the estimate.
 */

const EDITORS = new Set(["admin", "estimator", "finance"]);
const MINOR_PER_MAJOR = 100; // paise per rupee, cents per dollar

type Covers = QuoteIn["covers"];
type Range = QuotesOut["ranges"][number];

const COVERS: Record<Covers, string> = {
  all: "Whole project",
  build: "Building and launch only",
};

const VERDICT: Record<
  NonNullable<QuoteOut["verdict"]>,
  { label: string; advice: string; className: string; dot: string }
> = {
  below: {
    label: "Below the range",
    advice: "Ask how they will deliver it for this price.",
    className: "bg-warning-muted text-warning",
    dot: "fill-background stroke-foreground",
  },
  in: {
    label: "In the range",
    advice: "A fair price for this scope.",
    className: "bg-success/10 text-success",
    dot: "fill-primary stroke-background",
  },
  above: {
    label: "Above the range",
    advice: "Ask what they priced that this estimate does not.",
    className: "bg-muted text-foreground",
    dot: "fill-background stroke-foreground",
  },
};

function versus(percent: number | null): string {
  if (percent === null) return "";
  if (percent === 0) return "same as likely";
  return `${Math.abs(percent)}% ${percent > 0 ? "above" : "below"} likely`;
}

function slug(name: string): string {
  return (
    name
      .replace(/[^A-Za-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 60) || "project"
  );
}

/*
 * The picture: a bell with the fair range shaded and each quote as a dot. A quote sits by where
 * it falls in the range for what it covers (low, likely, high at fixed places), so whole-project
 * and building-only quotes share one picture.
 */
const W = 640;
const BASE = 150;
const X_LOW = 0.27;
const X_LIKELY = 0.45;
const X_HIGH = 0.7;

function placeX(amount: number, r: Range): number {
  const u =
    amount < r.likely_paise
      ? (amount - r.likely_paise) / Math.max(1, r.likely_paise - r.low_paise)
      : (amount - r.likely_paise) / Math.max(1, r.high_paise - r.likely_paise);
  const share = X_LIKELY + u * (u < 0 ? X_LIKELY - X_LOW : X_HIGH - X_LIKELY);
  return Math.min(0.97, Math.max(0.03, share)) * W;
}

function bell(): string {
  const shape: [number, number][] = [
    [0, BASE],
    [0.12, BASE - 6],
    [0.22, BASE - 40],
    [0.33, BASE - 104],
    [X_LIKELY, BASE - 128],
    [0.56, BASE - 100],
    [0.68, BASE - 52],
    [0.8, BASE - 18],
    [0.92, BASE - 4],
    [1, BASE],
  ];
  const pts = shape.map(([x, y]): [number, number] => [x * W, y]);
  let d = `M${pts[0][0]} ${pts[0][1]}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(0, i - 1)];
    const [p1, p2] = [pts[i], pts[i + 1]];
    const p3 = pts[Math.min(pts.length - 1, i + 2)];
    const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
    const c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
    d += ` C${c1[0]} ${c1[1]}, ${c2[0]} ${c2[1]}, ${p2[0]} ${p2[1]}`;
  }
  return d;
}

function QuotesPicture({
  data,
  currency,
}: {
  data: QuotesOut;
  currency: string;
}) {
  const whole = data.ranges.find((r) => r.covers === "all");
  if (!whole) return null;
  const byCover = Object.fromEntries(data.ranges.map((r) => [r.covers, r]));
  const curve = bell();
  return (
    <figure className="flex flex-col gap-2">
      <svg
        viewBox={`0 0 ${W} ${BASE + 40}`}
        className="w-full"
        role="img"
        aria-label="Each quote placed on the estimate's range"
      >
        <defs>
          <clipPath id="quote-band">
            <rect
              x={X_LOW * W}
              y={0}
              width={(X_HIGH - X_LOW) * W}
              height={BASE}
            />
          </clipPath>
        </defs>
        <path d={`${curve} Z`} className="fill-primary/10" />
        <path
          d={`${curve} Z`}
          className="fill-primary/25"
          clipPath="url(#quote-band)"
        />
        <path d={curve} className="fill-none stroke-primary" strokeWidth={2} />
        {[
          { x: X_LOW, label: `Low ${formatPaise(whole.low_paise, currency)}` },
          {
            x: X_LIKELY,
            label: `Likely ${formatPaise(whole.likely_paise, currency)}`,
          },
          {
            x: X_HIGH,
            label: `High ${formatPaise(whole.high_paise, currency)}`,
          },
        ].map((m) => (
          <g key={m.label}>
            <line
              x1={m.x * W}
              x2={m.x * W}
              y1={14}
              y2={BASE}
              className="stroke-foreground/30"
              strokeDasharray="3 4"
            />
            <text
              x={m.x * W}
              y={10}
              textAnchor="middle"
              className="fill-muted-foreground font-mono text-[10px]"
            >
              {m.label}
            </text>
          </g>
        ))}
        <line
          x1={0}
          x2={W}
          y1={BASE + 0.5}
          y2={BASE + 0.5}
          className="stroke-border"
        />
        {data.quotes.map((q, i) => {
          const r = byCover[q.covers] ?? whole;
          const x = placeX(q.amount_paise, r);
          const v = q.verdict ? VERDICT[q.verdict] : VERDICT.in;
          return (
            <g key={`${q.name}-${i}`}>
              <circle
                cx={x}
                cy={BASE}
                r={6.5}
                strokeWidth={2}
                className={v.dot}
              />
              <text
                x={x}
                y={BASE + 22}
                textAnchor="middle"
                className="fill-foreground text-[11px] font-medium"
              >
                {q.name.length > 14 ? `${q.name.slice(0, 13)}…` : q.name}
              </text>
            </g>
          );
        })}
      </svg>
      <figcaption className="text-sm text-muted-foreground">
        The shaded part is the fair range, before tax.{" "}
        {byCover.build
          ? `Building and launch only: ${formatRange(byCover.build.low_paise, byCover.build.high_paise, currency)}, likely ${formatPaise(byCover.build.likely_paise, currency)}. Each quote is placed on the range for what it covers.`
          : null}
      </figcaption>
    </figure>
  );
}

function QuoteRow({
  quote,
  currency,
  onRemove,
  busy,
}: {
  quote: QuoteOut;
  currency: string;
  onRemove: (() => void) | null;
  busy: boolean;
}) {
  const v = quote.verdict ? VERDICT[quote.verdict] : null;
  return (
    <li className="flex flex-wrap items-center gap-x-4 gap-y-2 py-3">
      <span className="flex min-w-40 flex-1 flex-col">
        <span className="font-medium">{quote.name}</span>
        <span className="text-sm text-muted-foreground">
          {COVERS[quote.covers]}
        </span>
      </span>
      <span className="flex flex-col items-end">
        <span className="font-mono font-semibold tabular-nums">
          {formatPaise(quote.amount_paise, currency)}
        </span>
        <span className="text-sm text-muted-foreground">
          {versus(quote.versus_likely_percent)}
        </span>
      </span>
      {v ? (
        <span className="flex max-w-64 flex-col gap-0.5">
          <span
            className={cn(
              "self-start rounded-full px-2.5 py-0.5 text-sm font-medium",
              v.className,
            )}
          >
            {v.label}
          </span>
          <span className="text-sm text-muted-foreground">{v.advice}</span>
        </span>
      ) : null}
      {onRemove ? (
        <Button
          variant="ghost"
          size="sm"
          disabled={busy}
          onClick={onRemove}
          aria-label={`Remove the quote from ${quote.name}`}
        >
          <TrashIcon />
        </Button>
      ) : null}
    </li>
  );
}

function AddQuote({
  currency,
  canSplit,
  busy,
  onAdd,
}: {
  currency: string;
  canSplit: boolean;
  busy: boolean;
  onAdd: (quote: QuoteIn) => Promise<boolean>;
}) {
  const [name, setName] = React.useState("");
  const [amount, setAmount] = React.useState("");
  const [covers, setCovers] = React.useState<Covers>("all");
  const value = Number(amount);
  const valid =
    name.trim() !== "" &&
    amount.trim() !== "" &&
    Number.isFinite(value) &&
    value > 0;
  const tax = currency === "INR" ? "GST" : "tax";

  async function add() {
    if (!valid) return;
    const ok = await onAdd({
      name: name.trim(),
      amount_paise: Math.round(value * MINOR_PER_MAJOR),
      covers,
    });
    if (ok) {
      setName("");
      setAmount("");
    }
  }

  return (
    <form
      className="flex flex-col gap-4 rounded-2xl bg-muted/40 p-4"
      onSubmit={(e) => {
        e.preventDefault();
        void add();
      }}
    >
      <div className="grid gap-4 sm:grid-cols-[1fr_1fr]">
        <div className="flex flex-col gap-2">
          <Label htmlFor="quote-name">Quote from</Label>
          <Input
            id="quote-name"
            value={name}
            maxLength={120}
            placeholder="e.g. a company or freelancer"
            onChange={(e) => setName(e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="quote-amount">
            Amount ({currencySymbol(currency)}, before {tax})
          </Label>
          <Input
            id="quote-amount"
            type="number"
            inputMode="decimal"
            min={0}
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
          />
          {valid ? (
            <span className="text-sm text-muted-foreground">
              {formatPaise(Math.round(value * MINOR_PER_MAJOR), currency)}
            </span>
          ) : null}
        </div>
      </div>
      {canSplit ? (
        <fieldset className="flex flex-col gap-2">
          <legend className="mb-2 text-sm font-medium">
            What does the quote cover?
          </legend>
          <div className="flex flex-wrap gap-3">
            {(Object.keys(COVERS) as Covers[]).map((c) => (
              <label
                key={c}
                className={cn(
                  "flex cursor-pointer items-center gap-2 rounded-lg border bg-card px-4 py-2 text-sm",
                  covers === c
                    ? "border-primary ring-1 ring-primary"
                    : "hover:bg-muted/40",
                )}
              >
                <input
                  type="radio"
                  name="quote-covers"
                  checked={covers === c}
                  onChange={() => setCovers(c)}
                  className="size-4 accent-primary"
                />
                {c === "all"
                  ? "Whole project (build, hosting and support)"
                  : COVERS[c]}
              </label>
            ))}
          </div>
        </fieldset>
      ) : null}
      <Button type="submit" className="self-start" disabled={!valid || busy}>
        {busy ? "Saving…" : "Add quote"}
      </Button>
    </form>
  );
}

export function CompareQuotes({
  estimateId,
  name,
}: {
  estimateId: string;
  name: string;
}) {
  const user = useCurrentUser();
  const canEdit = EDITORS.has(user.role) && !user.viewed_by_owner;
  const loader = React.useCallback(
    () => api.getQuotes(estimateId),
    [estimateId],
  );
  const { state, setData } = useLoad(loader);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [downloading, setDownloading] = React.useState(false);

  async function save(quotes: QuoteIn[]): Promise<boolean> {
    setBusy(true);
    setError(null);
    try {
      setData(await api.saveQuotes(estimateId, quotes));
      return true;
    } catch (e) {
      setError(errorText(e));
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function downloadForm() {
    setDownloading(true);
    setError(null);
    try {
      await downloadFile(
        `/estimates/${estimateId}/quote-form.xlsx`,
        `${slug(name)}-items-to-quote.xlsx`,
      );
    } catch (e) {
      setError(`Could not download the feature list: ${errorText(e)}`);
    } finally {
      setDownloading(false);
    }
  }

  const data = state.kind === "ready" ? state.data : null;
  const plain = (q: QuoteOut): QuoteIn => ({
    name: q.name,
    amount_paise: q.amount_paise,
    covers: q.covers,
  });

  return (
    <Disclosure
      title="Compare quotes you received"
      icon={ScalesIcon}
      hint="Type in the prices others quoted and see which ones are fair"
      defaultOpen={(data?.quotes.length ?? 0) > 0}
    >
      {state.kind === "loading" ? <Loading /> : null}
      {state.kind === "error" ? <ErrorNotice message={state.message} /> : null}
      {data ? (
        <div className="flex flex-col gap-6">
          <div className="flex flex-col gap-2">
            <p className="max-w-2xl text-muted-foreground">
              Each quote is placed against this estimate&apos;s range. A price
              far below it can mean missed work or a team that cannot deliver;
              far above it, extra work you did not ask for.
            </p>
            <button
              type="button"
              onClick={downloadForm}
              disabled={downloading}
              className="self-start text-sm text-primary underline hover:text-primary/80 disabled:opacity-60"
            >
              {downloading
                ? "Preparing the feature list…"
                : "Download the feature list to send for quotes (Excel, without your prices)"}
            </button>
          </div>
          {data.ranges.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              This estimate has no price range to compare with.
            </p>
          ) : null}
          {data.quotes.length > 0 ? (
            <QuotesPicture data={data} currency={data.currency} />
          ) : null}
          {data.quotes.length > 0 ? (
            <ul className="flex flex-col divide-y">
              {data.quotes.map((q, i) => (
                <QuoteRow
                  key={`${q.name}-${i}`}
                  quote={q}
                  currency={data.currency}
                  busy={busy}
                  onRemove={
                    canEdit
                      ? () =>
                          void save(
                            data.quotes.filter((_, j) => j !== i).map(plain),
                          )
                      : null
                  }
                />
              ))}
            </ul>
          ) : null}
          {canEdit && data.ranges.length > 0 ? (
            data.quotes.length < 20 ? (
              <AddQuote
                currency={data.currency}
                canSplit={data.ranges.some((r) => r.covers === "build")}
                busy={busy}
                onAdd={(q) => save([...data.quotes.map(plain), q])}
              />
            ) : (
              <p className="text-sm text-muted-foreground">
                Up to 20 quotes can be compared.
              </p>
            )
          ) : null}
          <ErrorNotice message={error} />
        </div>
      ) : null}
    </Disclosure>
  );
}
