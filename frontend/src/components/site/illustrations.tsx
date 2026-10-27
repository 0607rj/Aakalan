/**
 * Pictures for the public pages, built from the idea behind Aakalan: software is a set of
 * features, and each has its own price. Figures are a worked example (a small clinic
 * booking app), labelled as such. Parts marked fig-* play once when their
 * `[data-reveal]` parent comes into view (globals.css).
 */
import type { CSSProperties } from "react";
import {
  BellIcon,
  BugIcon,
  CalendarCheckIcon,
  CodeIcon,
  CreditCardIcon,
  CurrencyInrIcon,
  DeviceMobileIcon,
  FilePdfIcon,
  FileTextIcon,
  FlagIcon,
  LightningIcon,
  PaintBrushIcon,
  PuzzlePieceIcon,
  QuestionIcon,
  ShieldCheckIcon,
  TagIcon,
  TimerIcon,
  UsersThreeIcon,
} from "@phosphor-icons/react/dist/ssr";

import { cn } from "@/lib/utils";

export type IconType = typeof FileTextIcon;

/** A delay step for the fig-* animations. */
const d = (n: number) => ({ "--d": n }) as CSSProperties;

const TONES = {
  tape: "bg-tape-soft text-tape",
  ai: "bg-ai-soft text-ai",
  warm: "bg-warm/12 text-warm",
  warning: "bg-warning-muted text-warning",
  plain: "bg-foreground/[0.05] text-foreground/70",
} as const;

export type Tone = keyof typeof TONES;

const TILE_SIZES = {
  sm: ["size-8 rounded-lg", 18],
  md: ["size-11 rounded-xl", 22],
  lg: ["size-14 rounded-2xl", 28],
} as const;

/** An icon on a tinted square: the one way icons appear on the public pages. */
export function IconTile({
  icon: Icon,
  tone = "tape",
  size = "md",
  className,
}: {
  icon: IconType;
  tone?: Tone;
  size?: keyof typeof TILE_SIZES;
  className?: string;
}) {
  const [box, px] = TILE_SIZES[size];
  return (
    <span
      aria-hidden="true"
      className={cn(
        "flex shrink-0 items-center justify-center",
        box,
        TONES[tone],
        className,
      )}
    >
      <Icon size={px} weight="duotone" />
    </span>
  );
}

const lakh = (n: number) =>
  `₹${n.toLocaleString("en-IN", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} L`;

const FEATURE_COSTS = [
  {
    name: "Bookings",
    icon: CalendarCheckIcon,
    level: "Standard",
    ai: 2.6,
    old: 3.3,
  },
  {
    name: "Online payment",
    icon: CreditCardIcon,
    level: "Basic",
    ai: 1.1,
    old: 1.4,
  },
  {
    name: "Mobile app",
    icon: DeviceMobileIcon,
    level: "Basic",
    ai: 3.0,
    old: 3.9,
  },
  { name: "SMS reminders", icon: BellIcon, level: "Basic", ai: 0.9, old: 1.1 },
];

/** Each feature on its own line, with and without AI tools. */
export function FeatureCostFigure({ className }: { className?: string }) {
  return (
    <figure data-reveal className={cn("flex flex-col", className)}>
      <span className="eyebrow flex justify-between border-b pb-2">
        <span>Feature</span>
        <span>With AI tools / without</span>
      </span>
      {FEATURE_COSTS.map((f, i) => (
        <div
          key={f.name}
          className="fig-step flex items-center gap-3 border-b py-3"
          style={d(i)}
        >
          <IconTile icon={f.icon} size="sm" />
          <span className="flex min-w-0 flex-col">
            <span className="truncate font-medium">{f.name}</span>
            <span className="text-xs text-muted-foreground">{f.level}</span>
          </span>
          <span className="ml-auto flex flex-col items-end">
            <span className="font-mono font-semibold tabular-nums">
              {lakh(f.ai)}
            </span>
            <span className="font-mono text-xs text-muted-foreground tabular-nums line-through decoration-muted-foreground/50">
              {lakh(f.old)}
            </span>
          </span>
        </div>
      ))}
      <figcaption className="mt-3 flex flex-wrap items-center gap-x-2 text-sm text-muted-foreground">
        Together
        <span className="font-mono font-semibold text-foreground">
          {lakh(FEATURE_COSTS.reduce((s, f) => s + f.ai, 0))}
        </span>
        with AI tools,
        <span className="font-mono line-through decoration-muted-foreground/50">
          {lakh(FEATURE_COSTS.reduce((s, f) => s + f.old, 0))}
        </span>
        without
      </figcaption>
    </figure>
  );
}

const TRAIL = [
  { icon: FileTextIcon, label: "Clause 4.2", tone: "plain" },
  { icon: PuzzlePieceIcon, label: "Bookings", tone: "tape" },
  { icon: TagIcon, label: "₹1,150 an hour", tone: "warm" },
  { icon: CurrencyInrIcon, label: "₹2.6 L", tone: "ai" },
] as const;

/** Where one number comes from: the clause, the feature, the dated rate, the cost line. */
export function TraceFigure({ className }: { className?: string }) {
  return (
    <figure data-reveal className={cn("relative", className)}>
      <span
        aria-hidden="true"
        className="fig-bar absolute top-7 right-[12%] left-[12%] h-0.5 rounded-full bg-[repeating-linear-gradient(90deg,var(--tape)_0_6px,transparent_6px_11px)]"
      />
      <ol className="relative grid grid-cols-4 gap-2">
        {TRAIL.map((s, i) => (
          <li
            key={s.label}
            className="fig-step flex flex-col items-center gap-2 text-center"
            style={d(i)}
          >
            <IconTile
              icon={s.icon}
              tone={s.tone}
              size="lg"
              className="ring-4 ring-card"
            />
            <span className="text-xs leading-tight font-medium">{s.label}</span>
          </li>
        ))}
      </ol>
    </figure>
  );
}

/** What the document asks for that the price leaves out, flagged with its page. */
export function NotPricedFigure({ className }: { className?: string }) {
  const flags = [
    ["Penalties for delay", "p. 12", "-rotate-2"],
    ["One year of warranty", "p. 13", "rotate-1"],
    ["Source code handover", "p. 15", "-rotate-1"],
  ];
  return (
    <figure data-reveal className={cn("flex items-center gap-4", className)}>
      <span className="relative flex h-32 w-24 shrink-0 flex-col gap-1.5 rounded-lg border bg-card p-3 shadow-[0_1px_2px_rgb(27_36_51/0.06)]">
        <FileTextIcon
          size={22}
          weight="duotone"
          className="text-muted-foreground"
        />
        <span className="h-1 w-full rounded bg-foreground/[0.08]" />
        <span className="h-1 w-4/5 rounded bg-foreground/[0.08]" />
        <span className="h-1 w-full rounded bg-warning/40" />
        <span className="h-1 w-3/5 rounded bg-foreground/[0.08]" />
        <span className="h-1 w-full rounded bg-warning/40" />
      </span>
      <ul className="flex flex-col gap-2">
        {flags.map(([what, page, tilt], i) => (
          <li
            key={what}
            className={cn(
              "fig-step flex items-center gap-2 rounded-lg border border-warning/30 bg-card px-3 py-1.5 text-sm shadow-sm",
              tilt,
            )}
            style={d(i)}
          >
            <FlagIcon
              size={16}
              weight="fill"
              className="shrink-0 text-warning"
            />
            <span>{what}</span>
            <span className="font-mono text-xs text-muted-foreground">
              {page}
            </span>
          </li>
        ))}
      </ul>
    </figure>
  );
}

const TEAM = [
  { role: "Developers", icon: CodeIcon, count: 2 },
  { role: "Checks AI code", icon: ShieldCheckIcon, count: 1 },
  { role: "Tester", icon: BugIcon, count: 1 },
  { role: "Designer", icon: PaintBrushIcon, count: 1 },
];

/** The team behind the work, by role, and how long it takes. */
export function TeamFigure({ className }: { className?: string }) {
  return (
    <figure
      data-reveal
      className={cn("flex flex-wrap items-end gap-x-6 gap-y-4", className)}
    >
      {TEAM.map((t, i) => (
        <span
          key={t.role}
          className="fig-step flex flex-col items-center gap-2"
          style={d(i)}
        >
          <span className="flex -space-x-3">
            {Array.from({ length: t.count }, (_, k) => (
              <IconTile
                key={k}
                icon={t.icon}
                tone="tape"
                className="rounded-full ring-4 ring-card"
              />
            ))}
          </span>
          <span className="text-xs text-muted-foreground">{t.role}</span>
        </span>
      ))}
      <span
        className="fig-step flex items-center gap-2 rounded-full bg-foreground px-3.5 py-2 text-sm text-background"
        style={d(TEAM.length)}
      >
        <TimerIcon size={18} weight="duotone" />3 months to build
      </span>
    </figure>
  );
}

/** A page of the requirement document with the sentence a feature came from. */
export function DocumentFigure({ className }: { className?: string }) {
  return (
    <figure data-reveal className={cn(className)}>
      <span className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
        <FilePdfIcon size={16} weight="duotone" className="text-destructive" />
        requirement.pdf, page 4
      </span>
      <span className="mt-3 block h-1.5 w-4/5 rounded bg-foreground/[0.07]" />
      <span className="fig-mark mt-2 block rounded-md px-1.5 py-1 text-sm leading-snug">
        <b className="font-mono text-tape">4.2</b> Patients book, move and
        cancel appointments online, and get an SMS reminder.
      </span>
      <span className="mt-2 block h-1.5 w-2/3 rounded bg-foreground/[0.07]" />
      <span className="mt-4 flex flex-wrap gap-2 text-xs">
        {["Bookings", "SMS reminders"].map((f, i) => (
          <span
            key={f}
            className="fig-step flex items-center gap-1.5 rounded-full bg-tape-soft px-2.5 py-1 font-medium text-tape"
            style={d(i + 2)}
          >
            <PuzzlePieceIcon size={14} weight="duotone" />
            {f}, clause 4.2
          </span>
        ))}
      </span>
    </figure>
  );
}

/** One question, the way the form asks it. */
export function QuestionFigure({ className }: { className?: string }) {
  const options = ["Up to 100", "100 to 1,000", "1,000 to 10,000", "Not sure"];
  return (
    <figure data-reveal className={cn("flex flex-col gap-3", className)}>
      <span className="flex items-center gap-2 font-semibold">
        <UsersThreeIcon size={20} weight="duotone" className="text-tape" />
        How many people will use it?
      </span>
      <span className="flex flex-wrap gap-2 text-sm">
        {options.map((o, i) => (
          <span
            key={o}
            className={cn(
              "fig-step flex items-center gap-1.5 rounded-full border bg-card px-3.5 py-1.5",
              i === 2 && "border-tape bg-tape text-primary-foreground",
            )}
            style={d(i)}
          >
            {o === "Not sure" ? <QuestionIcon size={15} weight="bold" /> : null}
            {o}
          </span>
        ))}
      </span>
    </figure>
  );
}

const SAVINGS = [
  { task: "Documents", meter: 3 },
  { task: "Forms and screens", meter: 2 },
  { task: "Design decisions", meter: 1 },
];

/** Where AI tools save the most, and the checking that is added back. */
export function AiSavingFigure({ className }: { className?: string }) {
  return (
    <figure data-reveal className={cn("flex flex-col", className)}>
      {SAVINGS.map((s, i) => (
        <span
          key={s.task}
          className="fig-step flex items-center justify-between gap-3 border-b py-2.5 text-sm"
          style={d(i)}
        >
          {s.task}
          <span className="flex text-ai" aria-label={`${s.meter} of 3`}>
            {Array.from({ length: 3 }, (_, k) => (
              <LightningIcon
                key={k}
                size={16}
                weight="fill"
                className={k < s.meter ? undefined : "opacity-20"}
              />
            ))}
          </span>
        </span>
      ))}
      <span
        className="fig-step flex items-center justify-between gap-3 py-2.5 text-sm text-muted-foreground"
        style={d(3)}
      >
        People checking the AI&apos;s work
        <span className="font-semibold text-foreground">added back</span>
      </span>
    </figure>
  );
}
