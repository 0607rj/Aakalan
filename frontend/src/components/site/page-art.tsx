/**
 * The pictures at the top of the inner pages and the sign-in screens, one per page, in the
 * same style as the home page: icons on tinted tiles, cards, and example figures labelled as
 * examples. Pieces marked fig-step play once when their `[data-reveal]` parent comes into view.
 */
import type { CSSProperties } from "react";
import {
  ArrowDownIcon,
  BellIcon,
  CalendarCheckIcon,
  ChatCircleDotsIcon,
  CreditCardIcon,
  DeviceMobileIcon,
  EnvelopeSimpleIcon,
  FilePdfIcon,
  MagnifyingGlassIcon,
  MapPinIcon,
  ReceiptIcon,
  RobotIcon,
  ScalesIcon,
  SealCheckIcon,
  ShieldCheckIcon,
  SignInIcon,
  StorefrontIcon,
  UsersThreeIcon,
} from "@phosphor-icons/react/dist/ssr";

import { cn } from "@/lib/utils";

import { IconTile, type IconType, type Tone } from "./illustrations";

const d = (n: number) => ({ "--d": n }) as CSSProperties;

const CARD = "rounded-2xl border bg-card shadow-[0_1px_2px_rgb(0_0_0/0.06)]";

const MOSAIC: {
  name: string;
  icon: IconType;
  price?: string;
  tone?: Tone;
  at: string;
}[] = [
  { name: "Sign-in", icon: SignInIcon, at: "col-start-1 row-start-1" },
  {
    name: "Bookings",
    icon: CalendarCheckIcon,
    price: "₹2.6 L",
    at: "col-start-2 row-start-1 translate-y-4",
  },
  {
    name: "AI chatbot",
    icon: RobotIcon,
    price: "₹1.4 L",
    tone: "ai",
    at: "col-start-3 row-start-1 -translate-y-2",
  },
  {
    name: "Online payment",
    icon: CreditCardIcon,
    at: "col-start-1 row-start-2 translate-x-6",
  },
  {
    name: "Maps",
    icon: MapPinIcon,
    tone: "warm",
    at: "col-start-2 row-start-2 translate-y-6",
  },
  {
    name: "Mobile app",
    icon: DeviceMobileIcon,
    price: "₹3.0 L",
    at: "col-start-3 row-start-2 translate-y-2",
  },
  { name: "SMS", icon: BellIcon, at: "col-start-1 row-start-3 translate-x-2" },
  {
    name: "Online store",
    icon: StorefrontIcon,
    at: "col-start-2 row-start-3 translate-y-8",
  },
];

/** Features, each on its own card, some with their price: what Aakalan prices. */
export function FeatureMosaic({ className }: { className?: string }) {
  return (
    <figure
      data-reveal
      aria-hidden="true"
      className={cn("grid grid-cols-3 gap-3", className)}
    >
      {MOSAIC.map((m, i) => (
        <span
          key={m.name}
          className={cn("fig-step flex flex-col gap-2 p-3", CARD, m.at)}
          style={d(i)}
        >
          <IconTile icon={m.icon} size="sm" tone={m.tone ?? "tape"} />
          <span className="text-sm font-medium">{m.name}</span>
          {m.price ? (
            <span className="font-mono text-xs text-muted-foreground tabular-nums">
              {m.price}
            </span>
          ) : null}
        </span>
      ))}
    </figure>
  );
}

const FLOW: { icon: IconType; title: string; sub: string; tone: Tone }[] = [
  {
    icon: FilePdfIcon,
    title: "requirement.pdf",
    sub: "or a few lines, or ticked features",
    tone: "plain",
  },
  {
    icon: ChatCircleDotsIcon,
    title: "About ten questions",
    sub: "users, hosting, years of support",
    tone: "tape",
  },
  {
    icon: ReceiptIcon,
    title: "₹14.6 L likely",
    sub: "feature by feature, with the team",
    tone: "ai",
  },
];

/** From a document to a price: three cards joined by arrows. */
export function FlowFigure({ className }: { className?: string }) {
  return (
    <figure
      data-reveal
      aria-hidden="true"
      className={cn("flex flex-col items-stretch", className)}
    >
      {FLOW.map((f, i) => (
        <span key={f.title} className="contents">
          {i > 0 ? (
            <span
              className="fig-step flex justify-center py-1.5 text-tape"
              style={d(i * 2 - 1)}
            >
              <ArrowDownIcon size={20} weight="bold" />
            </span>
          ) : null}
          <span
            className={cn(
              "fig-step flex items-center gap-4 p-4",
              CARD,
              i === 1 && "ml-8",
              i === 2 && "ml-16",
            )}
            style={d(i * 2)}
          >
            <IconTile icon={f.icon} tone={f.tone} />
            <span className="flex flex-col">
              <span className={cn("font-semibold", i === 2 && "font-mono")}>
                {f.title}
              </span>
              <span className="text-sm text-muted-foreground">{f.sub}</span>
            </span>
          </span>
        </span>
      ))}
    </figure>
  );
}

const VALUES: { icon: IconType; label: string; tone: Tone; at: string }[] = [
  { icon: ScalesIcon, label: "Fair", tone: "tape", at: "-top-4 -left-3" },
  { icon: RobotIcon, label: "AI reads", tone: "ai", at: "-top-5 -right-2" },
  {
    icon: MagnifyingGlassIcon,
    label: "Traced",
    tone: "warm",
    at: "-bottom-5 -left-1",
  },
  {
    icon: SealCheckIcon,
    label: "Honest",
    tone: "tape",
    at: "-right-4 -bottom-4",
  },
];

/** The name and what it means, with what we hold to around it. */
export function MeaningFigure({ className }: { className?: string }) {
  return (
    <figure
      data-reveal
      aria-hidden="true"
      className={cn("relative mx-6 my-6", className)}
    >
      <span
        className={cn(
          "fig-step flex flex-col items-center gap-2 px-8 py-12 text-center",
          CARD,
        )}
      >
        <span className="font-display text-6xl text-tape">आकलन</span>
        <span className="font-mono text-sm text-muted-foreground">
          aa-ka-lan
        </span>
        <span className="mt-2 text-lg font-semibold">
          estimation, assessment
        </span>
      </span>
      {VALUES.map((v, i) => (
        <span
          key={v.label}
          className={cn(
            "fig-step absolute flex items-center gap-2 py-1.5 pr-3.5 pl-1.5",
            CARD,
            "rounded-full",
            v.at,
          )}
          style={d(i + 1)}
        >
          <IconTile
            icon={v.icon}
            size="sm"
            tone={v.tone}
            className="rounded-full"
          />
          <span className="text-sm font-medium">{v.label}</span>
        </span>
      ))}
    </figure>
  );
}

/** A question about one line of an estimate, and a person answering it. */
export function ChatFigure({ className }: { className?: string }) {
  return (
    <figure
      data-reveal
      aria-hidden="true"
      className={cn("flex flex-col gap-3", className)}
    >
      <span className="fig-step flex items-end gap-3" style={d(0)}>
        <IconTile
          icon={UsersThreeIcon}
          size="sm"
          tone="plain"
          className="rounded-full"
        />
        <span className={cn("max-w-xs rounded-bl-md p-4 text-sm", CARD)}>
          Why is hosting ₹3.0 L a year on our clinic app?
        </span>
      </span>
      <span
        className="fig-step flex flex-row-reverse items-end gap-3"
        style={d(1)}
      >
        <IconTile
          icon={EnvelopeSimpleIcon}
          size="sm"
          className="rounded-full"
        />
        <span className="max-w-xs rounded-2xl rounded-br-md bg-tape p-4 text-sm text-primary-foreground">
          It was priced on two servers. At your load one is enough: we show you
          the rate and its source.
        </span>
      </span>
      <span
        className="fig-step ml-11 flex items-center gap-2 text-xs text-muted-foreground"
        style={d(2)}
      >
        <ShieldCheckIcon size={16} weight="duotone" className="text-ai" />A
        person reads every message
      </span>
    </figure>
  );
}

const SAVED = [
  {
    name: "Clinic booking app",
    price: "₹14.6 L",
    icon: CalendarCheckIcon,
    tone: "tape",
  },
  {
    name: "Grievance portal",
    price: "₹1.1 Cr",
    icon: UsersThreeIcon,
    tone: "warm",
  },
  {
    name: "Store with chatbot",
    price: "₹22 L",
    icon: StorefrontIcon,
    tone: "ai",
  },
] as const;

/** Saved estimates waiting where you left them (example names). */
export function SavedEstimatesFigure({ className }: { className?: string }) {
  return (
    <figure
      aria-hidden="true"
      className={cn("flex flex-col gap-2.5", className)}
    >
      {SAVED.map((s, i) => (
        <span
          key={s.name}
          className={cn(
            "settle flex items-center gap-3 p-3",
            CARD,
            i === 1 && "ml-6",
            i === 2 && "ml-12",
          )}
          style={d(i + 1)}
        >
          <IconTile icon={s.icon} tone={s.tone} size="sm" />
          <span className="text-sm font-medium">{s.name}</span>
          <span className="ml-auto font-mono text-sm font-semibold tabular-nums">
            {s.price}
          </span>
        </span>
      ))}
    </figure>
  );
}

/** A code in the inbox: the way back in, and the way to confirm an address. */
export function CodeFigure({ className }: { className?: string }) {
  return (
    <figure aria-hidden="true" className={cn("flex flex-col gap-4", className)}>
      <span
        className={cn("settle flex items-center gap-3 p-4", CARD)}
        style={d(1)}
      >
        <IconTile icon={EnvelopeSimpleIcon} />
        <span className="flex flex-col">
          <span className="text-sm font-semibold">Your Aakalan code</span>
          <span className="text-xs text-muted-foreground">
            Valid for a few minutes
          </span>
        </span>
      </span>
      <span className="settle ml-8 flex gap-2" style={d(2)}>
        {["4", "8", "2", "9", "1", "7"].map((n, i) => (
          <span
            key={i}
            className={cn(
              "flex size-11 items-center justify-center font-mono text-lg font-semibold",
              CARD,
              "rounded-xl",
            )}
          >
            {n}
          </span>
        ))}
      </span>
    </figure>
  );
}
