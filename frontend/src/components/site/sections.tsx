import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/** The top of an inner page: a headline and one paragraph, left aligned. */
export function PageIntro({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="border-b bg-card/60">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-14 sm:px-6 sm:py-20">
        <h1 className="font-wide max-w-3xl text-4xl leading-[1.05] font-extrabold sm:text-5xl">
          {title}
        </h1>
        <div className="max-w-2xl text-lg text-muted-foreground">
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

/** The closing band on every public page. */
export function StartBand({
  title = "Describe your software in a few lines and see what it costs.",
}: {
  title?: string;
}) {
  return (
    <Section className="py-16 sm:py-20">
      <div className="relative overflow-hidden rounded-[28px] bg-foreground px-6 py-12 text-primary-foreground sm:px-12">
        <div
          aria-hidden="true"
          className="tape-ticks absolute inset-x-0 bottom-0 h-4 bg-tape opacity-90"
        />
        <h2 className="font-wide max-w-2xl text-3xl leading-tight font-extrabold sm:text-4xl">
          {title}
        </h2>
        <p className="mt-3 max-w-xl text-primary-foreground/75">
          Tick what it should do or upload the requirement document, answer ten
          short questions, and get the low, likely and high cost.
        </p>
        <div className="mt-8 flex flex-wrap gap-3 pb-4">
          <Link
            href="/estimate/new"
            className={cn(
              buttonVariants({ size: "lg" }),
              "bg-tape text-foreground hover:bg-tape/90",
            )}
          >
            Start an estimate
          </Link>
          <Link
            href="/contact"
            className={cn(
              buttonVariants({ size: "lg", variant: "outline" }),
              "border-primary-foreground/30 bg-transparent text-primary-foreground hover:bg-primary-foreground/10 hover:text-primary-foreground",
            )}
          >
            Talk to us
          </Link>
        </div>
      </div>
    </Section>
  );
}
