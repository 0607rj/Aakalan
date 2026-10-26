import Link from "next/link";
import { ArrowRightIcon, PlusIcon } from "@phosphor-icons/react/dist/ssr";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/*
 * The parts the public pages are made of. Structure comes from hairline rules and type, not
 * from boxes: a section is separated by a rule, a list by rules between its rows, and the only
 * framed things are the example windows, which stand for the product itself.
 */

/**
 * The top of an inner page: a large two-tone headline (the claim, then the rest in grey) and
 * one paragraph on a faint grid, with the page's own picture beside them on large screens.
 */
export function PageIntro({
  title,
  rest,
  children,
  art,
}: {
  title: string;
  /** Said after the title in grey, as one sentence with it. */
  rest?: string;
  children: React.ReactNode;
  art?: React.ReactNode;
}) {
  return (
    <section className="relative overflow-hidden border-b">
      <div aria-hidden="true" className="grid-lines absolute inset-0" />
      <div
        className={cn(
          "relative mx-auto grid max-w-6xl grid-cols-1 items-center gap-12 px-4 pt-16 pb-16 sm:px-6 sm:pt-24 sm:pb-20",
          art && "lg:grid-cols-[1.15fr_0.85fr]",
        )}
      >
        <div className="flex flex-col gap-6">
          <h1 className="rise-in font-display max-w-4xl text-[clamp(2.6rem,6.4vw,4.75rem)] leading-[1]">
            {title}
            {rest ? <span className="text-foreground/40"> {rest}</span> : null}
          </h1>
          <div
            className="rise-in max-w-xl text-lg leading-relaxed text-muted-foreground"
            style={{ "--rd": 1 } as React.CSSProperties}
          >
            {children}
          </div>
        </div>
        {art ? (
          <div
            className="rise-in mx-auto w-full max-w-md"
            style={{ "--rd": 2 } as React.CSSProperties}
          >
            {art}
          </div>
        ) : null}
      </div>
    </section>
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
    <section
      id={id}
      className={cn("mx-auto w-full max-w-6xl px-4 sm:px-6", className)}
    >
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
        "font-wide max-w-4xl text-[2rem] leading-[1.05] sm:text-[3.1rem]",
        center && "mx-auto text-center",
        className,
      )}
    >
      {claim}
      {children ? (
        <span className="text-foreground/40"> {children}</span>
      ) : null}
    </h2>
  );
}

/** A small mono label above a headline: "01 · Per feature". */
export function Kicker({
  n,
  children,
}: {
  n?: string;
  children: React.ReactNode;
}) {
  return (
    <p data-reveal className="eyebrow flex items-center gap-2">
      {n ? <span className="text-tape">{n}</span> : null}
      {n ? <span aria-hidden="true">·</span> : null}
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

/**
 * An example window of the product: a title bar with three dots and a mono title, and the
 * picture inside. The one framed thing on a page, so it reads as the product, not decoration.
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
        "overflow-hidden rounded-[14px] border bg-card shadow-[0_1px_0_rgb(255_255_255/0.8)_inset,0_30px_80px_-40px_rgb(27_36_51/0.35)]",
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

/**
 * One idea of a page: words on one side, its example window on the other (sides alternate),
 * with a rule above. `points` are short facts shown as a ticked list.
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
}) {
  return (
    <div className="grid grid-cols-1 items-center gap-10 border-t py-14 sm:py-20 lg:grid-cols-2 lg:gap-16">
      <div className={cn("flex flex-col gap-5", flip && "lg:order-2")}>
        {kicker ? <Kicker n={n}>{kicker}</Kicker> : null}
        <h2
          data-reveal
          className="font-wide max-w-xl text-[2rem] leading-[1.05] sm:text-[2.6rem]"
        >
          {title}
          {rest ? <span className="text-foreground/40"> {rest}</span> : null}
        </h2>
        <p
          data-reveal
          className="max-w-lg text-lg leading-relaxed text-muted-foreground"
        >
          {body}
        </p>
        {points?.length ? (
          <ul data-reveal className="flex flex-col gap-2 text-sm">
            {points.map((p) => (
              <li key={p} className="flex items-center gap-2.5">
                <span
                  aria-hidden="true"
                  className="size-1.5 shrink-0 rounded-full bg-tape"
                />
                {p}
              </li>
            ))}
          </ul>
        ) : null}
        {link ? (
          <span data-reveal className="mt-1">
            <TextLink href={link.href}>{link.label}</TextLink>
          </span>
        ) : null}
      </div>
      <div
        data-reveal
        style={{ "--rd": 1 } as React.CSSProperties}
        className={cn(flip && "lg:order-1")}
      >
        {art}
      </div>
    </div>
  );
}

/** Questions as a ruled list that opens one answer at a time, with the heading beside it. */
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
    <div className="grid grid-cols-1 gap-10 border-t py-14 sm:py-20 lg:grid-cols-[0.8fr_1.2fr] lg:gap-16">
      <h2
        data-reveal
        className="font-wide text-[2rem] leading-[1.05] sm:text-[2.6rem]"
      >
        {title}
        {rest ? <span className="text-foreground/40"> {rest}</span> : null}
      </h2>
      <div data-reveal className="flex flex-col border-t">
        {items.map((item) => (
          <details key={item.q} className="group border-b">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-6 py-5 font-semibold transition-colors hover:text-tape focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none [&::-webkit-details-marker]:hidden">
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
 * The closing band of every public page: a very large two-tone line on the faint grid, the
 * main action and a text link. `aside` is an optional picture on the right.
 */
export function StartBand({
  title = "Describe your software.",
  rest = "We'll do the sums.",
  aside,
}: {
  title?: string;
  rest?: string;
  aside?: React.ReactNode;
}) {
  return (
    <section className="relative overflow-hidden border-t">
      <div aria-hidden="true" className="grid-lines absolute inset-0" />
      <div
        className={cn(
          "relative mx-auto grid max-w-6xl grid-cols-1 items-center gap-12 px-4 py-20 sm:px-6 sm:py-28",
          aside && "lg:grid-cols-[1.3fr_0.7fr]",
        )}
      >
        <div className="flex flex-col items-start gap-8">
          <h2
            data-reveal
            className="font-display text-[clamp(2.75rem,7vw,5.5rem)] leading-[0.98]"
          >
            {title}
            <span className="block text-foreground/35">{rest}</span>
          </h2>
          <div
            data-reveal
            className="flex flex-wrap items-center gap-x-6 gap-y-4"
          >
            <Link
              href="/estimate/new"
              className={buttonVariants({ size: "lg" })}
            >
              Start an estimate
            </Link>
            <TextLink href="/contact">Talk to us</TextLink>
          </div>
          <p data-reveal className="font-mono text-xs text-muted-foreground">
            Your requirement documents are seen only by your company.
          </p>
        </div>
        {aside ? <div className="justify-self-center">{aside}</div> : null}
      </div>
    </section>
  );
}
