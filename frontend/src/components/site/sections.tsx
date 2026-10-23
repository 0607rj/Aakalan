import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/** The top of an inner page: a big serif headline and one paragraph, under a soft glow. */
export function PageIntro({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="glow relative overflow-hidden border-b">
      <div className="mx-auto flex max-w-6xl flex-col gap-5 px-4 pt-20 pb-16 sm:px-6 sm:pt-28 sm:pb-20">
        <h1 className="rise-in font-display max-w-4xl text-5xl leading-[1.02] sm:text-7xl">
          {title}
        </h1>
        <div
          className="rise-in max-w-2xl text-lg text-muted-foreground"
          style={{ "--rd": 1 } as React.CSSProperties}
        >
          {children}
        </div>
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
    <Section className="py-16 sm:py-24">
      <div
        data-reveal
        className="panel relative overflow-hidden rounded-[28px] px-6 py-14 text-center sm:px-12"
      >
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(60%_80%_at_50%_120%,rgb(255_107_107/0.22),transparent_70%)]"
        />
        <h2 className="font-display relative mx-auto max-w-3xl text-4xl leading-[1.05] sm:text-6xl">
          {title}
        </h2>
        <p className="relative mx-auto mt-4 max-w-xl text-muted-foreground">
          Tick what it should do or upload the requirement document, answer ten
          short questions, and get the low, likely and high cost.
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
