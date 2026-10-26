import type { Metadata } from "next";
import Link from "next/link";
import {
  ArrowRightIcon,
  CalculatorIcon,
  ChatCircleDotsIcon,
  FileArrowUpIcon,
  KeyboardIcon,
  ListChecksIcon,
  MagnifyingGlassIcon,
  QuestionIcon,
  ReceiptIcon,
  RobotIcon,
} from "@phosphor-icons/react/dist/ssr";

import { CostSky } from "@/components/site/cost-sky";
import {
  FeatureCostFigure,
  IconTile,
  NotPricedFigure,
  TeamFigure,
  TraceFigure,
} from "@/components/site/illustrations";
import { Keypad } from "@/components/site/keypad";
import { Section, Title } from "@/components/site/sections";
import { buttonVariants } from "@/components/ui/button";

export const metadata: Metadata = {
  title: "Aakalan · What should this software cost?",
};

const FACTS = [
  { value: "1 line", label: "per feature, each with its own price" },
  { value: "10", label: "plain questions, one per screen" },
  { value: "0", label: "prices made up by AI: formulas do the sums" },
  { value: "PDF + Excel", label: "report and bill of quantities to share" },
];

const THEN_NOW = [
  {
    icon: KeyboardIcon,
    topic: "The work",
    then: "Hours of typing",
    now: "Features at the level you need",
  },
  {
    icon: RobotIcon,
    topic: "AI tools",
    then: "Ignored",
    now: "Saving per task, checking added back",
  },
  {
    icon: ReceiptIcon,
    topic: "The total",
    then: "Building only",
    now: "Build, launch, servers, support, tax",
  },
  {
    icon: MagnifyingGlassIcon,
    topic: "The numbers",
    then: "Ask who made the sheet",
    now: "Each one traced to its source",
  },
];

const STEPS = [
  {
    icon: FileArrowUpIcon,
    title: "Say what to build",
    body: "Tick features, write a few lines, or upload the requirement document.",
  },
  {
    icon: ChatCircleDotsIcon,
    title: "Answer ten questions",
    body: "Users, hosting, years of support. Not sure is a fine answer.",
  },
  {
    icon: ListChecksIcon,
    title: "Get the price",
    body: "Low, likely and high cost, feature by feature, with the team needed.",
  },
];

const HONEST = [
  {
    icon: CalculatorIcon,
    text: "Worked out from hours and dated rates, never guessed by AI.",
  },
  {
    icon: MagnifyingGlassIcon,
    text: "Every line shows its rate, where the rate came from, and the formula.",
  },
  {
    icon: QuestionIcon,
    text: "Answer “not sure” and the range widens instead of guessing.",
  },
];

const delay = (rd: number) => ({ "--rd": rd }) as React.CSSProperties;

export default function HomePage() {
  return (
    <>
      {/* Hero: the claim beside an app laid brick by brick, each feature with its price */}
      <section className="glow relative overflow-hidden">
        <div className="mx-auto grid max-w-6xl items-center gap-12 px-4 pt-12 pb-16 sm:px-6 sm:pt-16 lg:grid-cols-[1fr_1.05fr] lg:pt-20">
          <div className="flex flex-col items-start">
            <h1 className="rise-in font-display text-[clamp(2.8rem,7vw,5rem)] leading-[1.02]">
              Price what gets <em className="text-tape">built</em>.
            </h1>
            <p
              className="rise-in mt-6 max-w-md text-lg text-muted-foreground sm:text-xl"
              style={delay(1)}
            >
              Software priced feature by feature, the way teams build it today
              with AI tools.
            </p>
            <div className="rise-in mt-8 flex flex-wrap gap-3" style={delay(2)}>
              <Link
                href="/estimate/new"
                className={buttonVariants({ size: "lg" })}
              >
                Start an estimate
              </Link>
              <Link
                href="/how-it-works"
                className={buttonVariants({ size: "lg", variant: "outline" })}
              >
                See how it works
              </Link>
            </div>
          </div>
          {/* the sky of possible costs of one project, as a picture */}
          <div
            className="rise-in relative aspect-[3/2] w-full overflow-hidden rounded-[22px] bg-card shadow-[0_0_0_1px_rgb(27_36_51/0.08),0_40px_120px_rgb(27_36_51/0.16)]"
            style={delay(1)}
          >
            <CostSky />
          </div>
        </div>
      </section>

      {/* Facts strip */}
      <Section className="pb-14 sm:pb-20">
        <dl className="grid grid-cols-2 gap-x-6 gap-y-8 border-t pt-8 lg:grid-cols-4">
          {FACTS.map((f, i) => (
            <div
              key={f.label}
              data-reveal
              style={delay(i)}
              className="flex flex-col gap-1"
            >
              <dt className="font-display text-3xl text-tape sm:text-4xl">
                {f.value}
              </dt>
              <dd className="max-w-[16rem] text-sm text-muted-foreground">
                {f.label}
              </dd>
            </div>
          ))}
        </dl>
      </Section>

      {/* The problem: then and now, side by side per topic */}
      <Section className="pb-14 sm:pb-20">
        <Title claim="Hourly rates were made for people typing every line.">
          AI drafts much of it now. Someone still checks it.
        </Title>
        <div className="mt-10 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {THEN_NOW.map((row, i) => (
            <div
              key={row.topic}
              data-reveal
              style={delay(i)}
              className="flex flex-col gap-4 rounded-[22px] border bg-card p-5"
            >
              <span className="flex items-center gap-3">
                <IconTile icon={row.icon} />
                <span className="font-semibold">{row.topic}</span>
              </span>
              <span className="text-sm text-muted-foreground line-through decoration-muted-foreground/50">
                {row.then}
              </span>
              <span className="flex items-start gap-2 font-medium">
                <ArrowRightIcon
                  size={18}
                  weight="bold"
                  className="mt-0.5 shrink-0 text-tape"
                />
                {row.now}
              </span>
            </div>
          ))}
        </div>
      </Section>

      {/* What you get: a bento of the four things the result shows */}
      <Section className="pb-14 sm:pb-20">
        <Title center claim="Nothing hidden inside the total." />
        <div className="mt-10 grid gap-4 lg:grid-cols-5">
          <article
            data-reveal
            className="flex flex-col gap-5 rounded-[26px] bg-tape-soft/70 p-6 sm:p-8 lg:col-span-3 lg:row-span-2"
          >
            <h3 className="text-xl font-semibold">
              Each feature, its own price.
            </h3>
            <p className="-mt-3 text-muted-foreground">
              With AI tools and without. Drop one, watch the total move.
            </p>
            <FeatureCostFigure className="mt-auto" />
          </article>
          <article
            data-reveal
            style={delay(1)}
            className="flex flex-col gap-6 rounded-[26px] border bg-card p-6 lg:col-span-2"
          >
            <h3 className="text-xl font-semibold">
              Every number has an address.
            </h3>
            <TraceFigure />
          </article>
          <article
            data-reveal
            style={delay(2)}
            className="flex flex-col gap-5 rounded-[26px] bg-warning-muted/70 p-6 lg:col-span-2"
          >
            <h3 className="text-xl font-semibold">
              What isn&apos;t priced is listed.
            </h3>
            <NotPricedFigure />
          </article>
          <article
            data-reveal
            className="flex flex-col gap-5 rounded-[26px] border bg-card p-6 sm:p-8 lg:col-span-5 lg:flex-row lg:items-center lg:justify-between"
          >
            <h3 className="text-xl font-semibold lg:max-w-xs">
              The team and the time it takes.
            </h3>
            <TeamFigure />
          </article>
        </div>
      </Section>

      {/* How it works: three steps on one line */}
      <Section className="pb-14 sm:pb-20">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <Title claim="Three steps, about as long as making tea." />
          <Link
            href="/how-it-works"
            className="flex items-center gap-1.5 text-sm font-semibold text-tape underline-offset-4 hover:underline"
          >
            The full walk-through <ArrowRightIcon size={16} weight="bold" />
          </Link>
        </div>
        <ol className="relative mt-12 grid gap-10 md:grid-cols-3">
          <span
            aria-hidden="true"
            className="absolute top-7 right-[16%] left-[16%] hidden h-0.5 bg-[repeating-linear-gradient(90deg,var(--border)_0_8px,transparent_8px_14px)] md:block"
          />
          {STEPS.map((s, i) => (
            <li
              key={s.title}
              data-reveal
              style={delay(i)}
              className="relative flex flex-col items-center gap-3 text-center"
            >
              <IconTile
                icon={s.icon}
                size="lg"
                className={
                  i === 2
                    ? "bg-tape text-primary-foreground ring-8 ring-background"
                    : "ring-8 ring-background"
                }
              />
              <h3 className="mt-2 text-lg font-semibold">{s.title}</h3>
              <p className="max-w-xs text-muted-foreground">{s.body}</p>
            </li>
          ))}
        </ol>
      </Section>

      {/* Honest about accuracy */}
      <Section className="grid items-center gap-10 pb-14 sm:pb-20 lg:grid-cols-2">
        <div className="flex flex-col gap-5">
          <Title claim="Nobody knows the exact number yet. So you get a range." />
          <Link
            data-reveal
            href="/about"
            className="flex w-fit items-center gap-1.5 text-sm font-semibold text-tape underline-offset-4 hover:underline"
          >
            How we test the prices <ArrowRightIcon size={16} weight="bold" />
          </Link>
        </div>
        <ul className="flex flex-col gap-3">
          {HONEST.map((h, i) => (
            <li
              key={h.text}
              data-reveal
              style={delay(i)}
              className="flex items-center gap-4 rounded-2xl border bg-card p-4"
            >
              <IconTile icon={h.icon} tone={i === 2 ? "warm" : "tape"} />
              <span>{h.text}</span>
            </li>
          ))}
        </ul>
      </Section>

      {/* Closing: the keypad presses itself, then anyone can use it */}
      <section className="relative overflow-hidden border-t">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(50%_45%_at_50%_30%,rgb(11_120_184/0.09),transparent_70%)]"
        />
        <div className="relative mx-auto flex max-w-6xl flex-col items-center gap-8 px-4 py-14 text-center sm:px-6 sm:py-20">
          <Keypad />
          <div className="flex flex-col items-center gap-4">
            <h2
              data-reveal
              className="font-display text-5xl leading-[1.05] sm:text-7xl"
            >
              Put the spreadsheet down.
            </h2>
            <p data-reveal className="max-w-xl text-lg text-muted-foreground">
              Describe your software in a few lines and let Aakalan do the sums.
            </p>
            <div
              data-reveal
              className="mt-4 flex flex-wrap justify-center gap-3"
            >
              <Link
                href="/estimate/new"
                className={buttonVariants({ size: "lg" })}
              >
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
        </div>
      </section>
    </>
  );
}
