import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * The top of an inner page: the headline and one paragraph under a soft glow, with the page's
 * own picture beside them on large screens (below them on small ones).
 */
export function PageIntro({
  title,
  children,
  art,
}: {
  title: string;
  children: React.ReactNode;
  art?: React.ReactNode;
}) {
  return (
    <section className="glow relative overflow-hidden border-b">
      <div
        className={cn(
          "mx-auto grid max-w-6xl items-center gap-12 px-4 pt-14 pb-14 sm:px-6 sm:pt-20 sm:pb-16",
          art && "lg:grid-cols-[1.1fr_0.9fr]",
        )}
      >
        <div className="flex flex-col gap-5">
          <h1 className="rise-in font-display max-w-4xl text-[clamp(2.5rem,6vw,4.25rem)] leading-[1.04]">
            {title}
          </h1>
          <div
            className="rise-in max-w-xl text-lg text-muted-foreground"
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
 * A section headline: the claim in white, the explanation after it in grey, one paragraph,
 * the way the closing lines of a good brief read.
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
        "font-wide max-w-4xl text-[1.75rem] leading-[1.12] font-semibold sm:text-[2.6rem]",
        center && "mx-auto text-center",
        className,
      )}
    >
      {claim}
      {children ? (
        <span className="text-muted-foreground"> {children}</span>
      ) : null}
    </h2>
  );
}

/** The closing band on every public page. */
export function StartBand({
  title = "Describe your software in a few lines and see what it costs.",
}: {
  title?: string;
}) {
  return (
    <Section className="py-12 sm:py-16">
      <div
        data-reveal
        className="panel relative overflow-hidden rounded-[28px] px-6 py-10 text-center sm:px-12"
      >
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(60%_80%_at_50%_120%,rgb(11_120_184/0.22),transparent_70%)]"
        />
        <h2 className="font-display relative mx-auto max-w-3xl text-4xl leading-[1.05] sm:text-6xl">
          {title}
        </h2>
        <p className="relative mx-auto mt-4 max-w-xl text-muted-foreground">
          Tick features or upload the document, answer ten questions, get the
          price.
        </p>
        <div className="relative mt-8 flex flex-wrap justify-center gap-3">
          <Link href="/estimate/new" className={buttonVariants({ size: "lg" })}>
            Start an estimate
          </Link>
          <Link
            href="/contact"
            className={buttonVariants({ size: "lg", variant: "outline" })}
          >
            Talk to us
          </Link>
        </div>
      </div>
    </Section>
  );
}
