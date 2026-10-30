import Link from "next/link";
import { ArrowRightIcon, PlusIcon } from "@phosphor-icons/react/dist/ssr";

import { cn } from "@/lib/utils";

import type { DotSceneName } from "./dot-scene";
import { EmberHero } from "./ember-hero";
import { Keypad } from "./keypad";

/*
 * The parts the public pages are made of. Each page opens on the ember panel and sinks into the
 * off-white page; below, a section is a pill label, a two-tone headline and soft white cards,
 * and the product's ideas sit on dark cards with the product's own windows inside them.
 */

/** Tones of a feature: dark (the default) or warm cards, or `open`, on the page with no card. */
export type CardTone = "dark" | "warm" | "open";

const delay = (rd: number) => ({ "--rd": rd }) as React.CSSProperties;

/**
 * The top of an inner page, on the ember panel: a large two-tone headline (the claim in white,
 * the rest in peach) and one paragraph, with the page's own dot picture behind and beside them.
 * `center` puts the words in the middle, for a picture that sits below them.
 */
export function PageIntro({
  title,
  rest,
  children,
  scene,
  sceneClassName,
  center = false,
  className,
}: {
  title: string;
  /** Said after the title in peach, as one sentence with it. */
  rest?: string;
  children: React.ReactNode;
  scene: DotSceneName;
  sceneClassName?: string;
  center?: boolean;
  className?: string;
}) {
  return (
    <EmberHero scene={scene} sceneClassName={sceneClassName}>
      <div
        className={cn(
          "relative page-wrap pt-32 pb-[26rem] sm:flex sm:min-h-[calc(100svh+90px)] sm:flex-col sm:justify-center sm:pt-24 sm:pb-36",
          center && "text-center",
          className,
        )}
      >
        <h1
          className={cn(
            "rise-in font-display text-[clamp(2.6rem,6.4vw,4.75rem)] leading-[1]",
            center ? "mx-auto max-w-4xl" : "max-w-[40rem]",
          )}
        >
          {title}
          {rest ? <span className="text-peach"> {rest}</span> : null}
        </h1>
        <div
          className={cn(
            "rise-in mt-6 max-w-xl text-lg leading-relaxed text-white/75",
            center && "mx-auto",
          )}
          style={delay(1)}
        >
          {children}
        </div>
      </div>
    </EmberHero>
  );
}

export function Section({
  children,
  className,
  id,
}: {
  children: React.ReactNode;
  className?: string;
  id?: string;
}) {
  return (
    <section id={id} className={cn("page-wrap", className)}>
      {children}
    </section>
  );
}

/**
 * A section headline: the claim in full colour, the explanation after it in grey, one
 * sentence, the way the closing lines of a good brief read.
 */
export function Title({
  claim,
  children,
  className,
  center,
}: {
  claim: string;
  children?: React.ReactNode;
  className?: string;
  center?: boolean;
}) {
  return (
    <h2
      data-reveal
      className={cn(
        "font-wide max-w-4xl text-[clamp(2.1rem,4.8vw,3.5rem)] leading-[1.08]",
        center && "mx-auto max-w-[20ch] text-center",
        className,
      )}
    >
      {claim}
      {children ? <span className="text-faint"> {children}</span> : null}
    </h2>
  );
}

/** A small pill label above a headline: "01 What gets priced". */
export function Kicker({
  n,
  children,
  tone = "light",
}: {
  n?: string;
  children: React.ReactNode;
  tone?: "light" | "dark";
}) {
  return (
    <p
      data-reveal
      className={cn(
        "inline-flex w-fit items-center gap-2 rounded-full px-4 py-[7px] text-sm font-medium",
        tone === "dark"
          ? "glass-pill text-white"
          : "border bg-card text-foreground",
      )}
    >
      {n ? (
        <span
          className={cn(
            "font-mono text-xs",
            tone === "dark" ? "text-peach" : "text-tape",
          )}
        >
          {n}
        </span>
      ) : null}
      {children}
    </p>
  );
}

/** A plain text link with a rule under it and an arrow: "See every feature →". */
export function TextLink({
  href,
  children,
  className,
}: {
  href: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <Link href={href} className={cn("text-link", className)}>
      {children}
      <ArrowRightIcon size={16} weight="bold" aria-hidden="true" />
    </Link>
  );
}

/** A white pill link with an arrow, for dark cards and the ember panel. */
export function LightLink({
  href,
  children,
}: {
  href: string;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className="group inline-flex h-12 w-fit items-center gap-2 rounded-full bg-white px-6 font-medium text-foreground transition-transform hover:-translate-y-px"
    >
      {children}
      <ArrowRightIcon
        size={16}
        weight="bold"
        aria-hidden="true"
        className="transition-transform group-hover:translate-x-0.5"
      />
    </Link>
  );
}

/**
 * An example window of the product: a title bar with three dots and a mono title, and the
 * picture inside. It reads as the product itself, on the page or on a dark card.
 */
export function AppWindow({
  title,
  children,
  className,
  bodyClassName,
}: {
  title: string;
  children: React.ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <div
      className={cn(
        "overflow-hidden rounded-[20px] border bg-card text-foreground shadow-[0_1px_2px_rgb(0_0_0/0.05),0_24px_48px_-28px_rgb(0_0_0/0.4)]",
        className,
      )}
    >
      <div className="flex items-center gap-3 border-b bg-panel-2 px-4 py-2.5">
        <span aria-hidden="true" className="flex gap-1.5">
          <span className="size-2.5 rounded-full bg-foreground/15" />
          <span className="size-2.5 rounded-full bg-foreground/15" />
          <span className="size-2.5 rounded-full bg-foreground/15" />
        </span>
        <span className="truncate font-mono text-xs text-muted-foreground">
          {title}
        </span>
      </div>
      <div className={cn("p-5 sm:p-6", bodyClassName)}>{children}</div>
    </div>
  );
}

/** The frame of a feature card in its tone. */
export function cardTone(tone: CardTone): string {
  if (tone === "open") return "text-foreground";
  return cn("dark-card", tone === "warm" ? "warm" : "glow-low");
}

/**
 * One idea of a page: words on one side, its example window on the other (sides alternate).
 * Dark and warm cards carry white words; `points` are short facts in a list.
 */
export function FeatureRow({
  kicker,
  n,
  title,
  rest,
  body,
  points,
  link,
  art,
  flip = false,
  tone = "dark",
}: {
  kicker?: string;
  n?: string;
  title: string;
  rest?: string;
  body: React.ReactNode;
  points?: string[];
  link?: { href: string; label: string };
  art: React.ReactNode;
  flip?: boolean;
  tone?: CardTone;
}) {
  const dark = tone !== "open";
  return (
    <div
      data-reveal
      className={cn(
        "mt-6 grid grid-cols-1 items-center gap-10 first:mt-0 lg:grid-cols-2 lg:gap-14",
        dark ? "p-7 sm:p-11" : "px-1 py-10 sm:py-14",
        cardTone(tone),
      )}
    >
      <div className={cn("flex flex-col gap-5", flip && "lg:order-2")}>
        {kicker ? (
          <p
            className={cn(
              "font-mono text-xs tracking-[0.06em] uppercase",
              dark ? "text-white/55" : "text-muted-foreground",
            )}
          >
            {n ? `${n} · ` : null}
            {kicker}
          </p>
        ) : null}
        <h2 className="font-wide max-w-xl text-[2rem] leading-[1.05] sm:text-[2.5rem]">
          {title}
          {rest ? (
            <span className={dark ? "text-white/50" : "text-faint"}>
              {" "}
              {rest}
            </span>
          ) : null}
        </h2>
        <p
          className={cn(
            "max-w-lg text-lg leading-relaxed",
            dark ? "text-white/72" : "text-muted-foreground",
          )}
        >
          {body}
        </p>
        {points?.length ? (
          <ul className="flex flex-col gap-2 text-sm">
            {points.map((p) => (
              <li key={p} className="flex items-center gap-2.5">
                <span
                  aria-hidden="true"
                  className="size-1.5 shrink-0 rounded-full bg-tape-bright"
                />
                {p}
              </li>
            ))}
          </ul>
        ) : null}
        {link ? (
          <span className="mt-1">
            {dark ? (
              <LightLink href={link.href}>{link.label}</LightLink>
            ) : (
              <TextLink href={link.href}>{link.label}</TextLink>
            )}
          </span>
        ) : null}
      </div>
      <div style={delay(1)} className={cn("min-w-0", flip && "lg:order-1")}>
        {art}
      </div>
    </div>
  );
}

/** Questions on one white card, opening one answer at a time, with the heading beside it. */
export function Faq({
  title,
  rest,
  items,
}: {
  title: string;
  rest?: string;
  items: { q: string; a: React.ReactNode }[];
}) {
  return (
    <div className="grid grid-cols-1 gap-10 lg:grid-cols-[1fr_1.4fr] lg:gap-16">
      <h2
        data-reveal
        className="font-wide text-[clamp(2.1rem,4.8vw,3.5rem)] leading-[1.08]"
      >
        {title}
        {rest ? <span className="text-faint"> {rest}</span> : null}
      </h2>
      <div data-reveal className="soft-card flex flex-col px-[26px] py-1.5">
        {items.map((item) => (
          <details key={item.q} className="group border-b last:border-b-0">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-6 py-5 text-[1.05rem] font-medium transition-colors hover:text-tape focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none [&::-webkit-details-marker]:hidden">
              {item.q}
              <PlusIcon
                size={16}
                weight="bold"
                aria-hidden="true"
                className="shrink-0 text-muted-foreground transition-transform duration-300 group-open:rotate-45"
              />
            </summary>
            <div className="max-w-2xl pb-6 leading-relaxed text-muted-foreground">
              {item.a}
            </div>
          </details>
        ))}
      </div>
    </div>
  );
}

/**
 * The closing card of a page, on the ember again: a very large two-tone line, the main action
 * and a text link, and the keypad.
 */
export function StartBand({
  title = "Describe your software.",
  rest = "We'll do the sums.",
}: {
  title?: string;
  rest?: string;
}) {
  return (
    <section className="page-wrap pt-6 pb-[clamp(72px,10vw,120px)]">
      <div
        data-reveal
        className="closing grid grid-cols-1 items-center gap-10 p-[clamp(32px,6vw,72px)] lg:grid-cols-[1.3fr_1fr]"
      >
        <div>
          <h2 className="font-wide text-[clamp(2.6rem,6vw,4.6rem)] leading-[1]">
            {title}
            <span className="block text-peach">{rest}</span>
          </h2>
          <div className="mt-8 flex flex-wrap items-center gap-x-[26px] gap-y-4">
            <Link
              href="/estimate/new"
              className="inline-flex h-[52px] items-center rounded-full bg-white px-[26px] font-medium text-foreground transition-transform hover:-translate-y-px"
            >
              Start an estimate
            </Link>
            <Link
              href="/contact"
              className="inline-flex items-center gap-1.5 border-b border-current pb-0.5 font-medium"
            >
              Talk to us <span aria-hidden="true">→</span>
            </Link>
          </div>
          <p className="mt-[26px] text-[13px] text-white/72">
            Your requirement documents are seen only by your company.
          </p>
        </div>
        <Keypad />
      </div>
    </section>
  );
}
