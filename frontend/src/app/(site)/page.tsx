import type { Metadata } from "next";
import Link from "next/link";
import { CheckIcon, MinusIcon } from "@phosphor-icons/react/dist/ssr";

import { CostSky } from "@/components/site/cost-sky";
import { FeatureWords } from "@/components/site/feature-words";
import {
  FeatureCostFigure,
  NotPricedFigure,
  TeamFigure,
  TraceFigure,
} from "@/components/site/illustrations";
import { Keypad } from "@/components/site/keypad";
import { LogoMark } from "@/components/site/logo";
import {
  AppWindow,
  Faq,
  FeatureRow,
  Kicker,
  Section,
  StartBand,
  TextLink,
  Title,
} from "@/components/site/sections";
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

/** The old way and Aakalan's, topic by topic. */
const COMPARE = [
  {
    topic: "The work",
    then: "Hours of typing, line by line",
    now: "Each feature at the level you need",
  },
  {
    topic: "AI tools",
    then: "Left out, or a guessed discount",
    now: "Saving per task, with the checking added back",
  },
  {
    topic: "The total",
    then: "Building only",
    now: "Build, launch, servers, support and tax",
  },
  {
    topic: "The numbers",
    then: "Ask whoever made the sheet",
    now: "Each one traced to its rate and source",
  },
];

const STEPS = [
  {
    title: "Say what to build",
    body: "Tick features, write a few lines, or upload the requirement document.",
  },
  {
    title: "Answer about ten questions",
    body: "Users, hosting, years of support. “Not sure” is a fine answer.",
  },
  {
    title: "Get the price",
    body: "Low, likely and high cost, feature by feature, with the team needed.",
  },
];

const FAQ = [
  {
    q: "Does AI make up the price?",
    a: "No. AI only reads your document and suggests features. Every number comes from fixed formulas, hours and dated rates, so the same answers always give the same price.",
  },
  {
    q: "What does the total include?",
    a: "Building it, launching it, the servers, the years of support you choose, and tax, as a low, likely and high cost. What the document asks for but the price leaves out is listed on its own.",
  },
  {
    q: "What if I don't know an answer?",
    a: "Choose “Not sure”. The usual answer is used and the range widens, instead of the estimate pretending to know.",
  },
  {
    q: "Can I use my own rates?",
    a: "Yes. Your company's day rates and margin are used for its estimates. An estimate keeps the rates it was made with, so it never changes later.",
  },
  {
    q: "Who sees my requirement document?",
    a: "Only your company. The text goes only to the AI service set up for reading it, and is treated as data, never as instructions.",
  },
  {
    q: "How exact is it?",
    a: "It is a guide before work starts, not a quote. Nobody knows the exact number yet, so you get a range with the reasons for its width.",
  },
];

const delay = (rd: number) => ({ "--rd": rd }) as React.CSSProperties;

export default function HomePage() {
  return (
    <>
      {/* Hero: the claim on a faint grid, the sky of possible costs in a product window */}
      <section className="relative overflow-hidden">
        <div aria-hidden="true" className="grid-lines absolute inset-0" />
        <div className="relative mx-auto grid max-w-6xl grid-cols-1 items-center gap-14 px-4 pt-16 pb-20 sm:px-6 sm:pt-24 lg:grid-cols-[1fr_1.05fr] lg:pb-28">
          <div className="flex flex-col items-start">
            <p className="rise-in eyebrow flex items-center gap-2">
              <span className="size-1.5 rounded-full bg-warm" />
              Software cost, feature by feature
            </p>
            <h1
              className="rise-in font-display mt-6 text-[clamp(3rem,8vw,6rem)] leading-[0.95]"
              style={delay(1)}
            >
              Price what gets <span className="text-tape">built.</span>
            </h1>
            <p
              className="rise-in mt-7 max-w-md text-lg leading-relaxed text-muted-foreground sm:text-xl"
              style={delay(2)}
            >
              Every feature gets its own price.{" "}
              <span className="text-foreground">
                Worked out the way teams build today, with AI tools.
              </span>
            </p>
            <div
              className="rise-in mt-9 flex flex-wrap items-center gap-x-7 gap-y-4"
              style={delay(3)}
            >
              <Link
                href="/estimate/new"
                className={buttonVariants({ size: "lg" })}
              >
                Start an estimate
              </Link>
              <TextLink href="/how-it-works">See how it works</TextLink>
            </div>
            <p
              className="rise-in mt-8 flex flex-wrap items-center gap-2 text-sm text-muted-foreground"
              style={delay(4)}
            >
              Don&apos;t know an answer? Press{" "}
              <span className="kbd">Not sure</span>
              and the range widens.
            </p>
          </div>

          <div className="rise-in relative" style={delay(2)}>
            <AppWindow
              title="clinic-booking-app · 30,000 possible costs"
              bodyClassName="relative aspect-[3/2] overflow-hidden p-0"
            >
              <CostSky />
            </AppWindow>
            {/* the result, as the app would tell it (an example) */}
            <div className="absolute -bottom-8 left-4 flex w-[17rem] items-start gap-3 rounded-xl border bg-card/95 p-4 shadow-[0_1px_2px_rgb(0_0_0/0.06),0_10px_24px_-16px_rgb(0_0_0/0.25)] backdrop-blur sm:-left-8">
              <LogoMark className="size-8 shrink-0" />
              <span className="flex flex-col gap-0.5">
                <span className="font-mono text-[11px] text-muted-foreground">
                  Aakalan · example
                </span>
                <span className="font-semibold">Likely ₹14.6 L</span>
                <span className="text-xs text-muted-foreground">
                  Low ₹11.2 L, high ₹19.8 L, with 3 years of support
                </span>
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Facts: four cells between rules */}
      <Section>
        <dl className="grid grid-cols-2 border-y lg:grid-cols-4">
          {FACTS.map((f, i) => (
            <div
              key={f.label}
              data-reveal
              style={delay(i)}
              className="flex flex-col gap-1 border-foreground/[0.08] px-1 py-8 odd:border-r sm:px-6 lg:border-r lg:last:border-r-0"
            >
              <dt className="font-display text-3xl sm:text-4xl">{f.value}</dt>
              <dd className="max-w-[15rem] text-sm text-muted-foreground">
                {f.label}
              </dd>
            </div>
          ))}
        </dl>
      </Section>

      {/* The problem, as a plain comparison */}
      <Section className="py-20 sm:py-28">
        <Kicker n="01">Why prices stopped adding up</Kicker>
        <Title
          claim="Hourly rates were made for people typing every line."
          className="mt-5"
        >
          AI drafts much of it now. Someone still checks it.
        </Title>
        {/* a table on wide screens; on a phone each topic stacks its two answers */}
        <div data-reveal className="mt-12 border-t">
          <div className="eyebrow hidden border-b py-3 sm:grid sm:grid-cols-[1fr_2fr_2fr] sm:gap-6">
            <span />
            <span>A spreadsheet estimate</span>
            <span className="text-tape">Aakalan</span>
          </div>
          {COMPARE.map((row) => (
            <div
              key={row.topic}
              className="grid grid-cols-1 gap-2 border-b py-5 sm:grid-cols-[1fr_2fr_2fr] sm:gap-6"
            >
              <span className="font-semibold">{row.topic}</span>
              <span className="flex items-start gap-2.5 text-muted-foreground">
                <MinusIcon
                  size={16}
                  weight="bold"
                  aria-hidden="true"
                  className="mt-1 shrink-0 text-foreground/30"
                />
                <span>
                  <span className="sr-only">A spreadsheet estimate: </span>
                  {row.then}
                </span>
              </span>
              <span className="flex items-start gap-2.5 font-medium">
                <CheckIcon
                  size={16}
                  weight="bold"
                  aria-hidden="true"
                  className="mt-1 shrink-0 text-tape"
                />
                <span>
                  <span className="sr-only">Aakalan: </span>
                  {row.now}
                </span>
              </span>
            </div>
          ))}
        </div>
      </Section>

      {/* What gets priced: the features set large, one lit at a time */}
      <Section className="border-t py-20 sm:py-28">
        <Kicker n="02">What gets priced</Kicker>
        <Title claim="You say what the software should do." className="mt-5">
          Aakalan splits it into features, prices each one from hours and dated
          rates, and shows the working.
        </Title>
        <FeatureWords className="mt-14" />
      </Section>

      {/* What the result shows: words beside the product, sides alternating */}
      <Section>
        <FeatureRow
          kicker="Per feature"
          n="03"
          title="Each feature, its own price."
          rest="With AI tools and without."
          body="Drop a feature and watch the total move. Pick basic, standard or advanced for each one, so you pay for the level you need."
          link={{ href: "/features", label: "See every feature" }}
          art={
            <AppWindow title="result · features">
              <FeatureCostFigure />
            </AppWindow>
          }
        />
        <FeatureRow
          flip
          kicker="Traceable"
          n="04"
          title="Every number has an address."
          body="Each cost line keeps the clause it came from, the feature, the dated rate and the formula. Nothing is a black box."
          link={{ href: "/how-it-works", label: "How it works" }}
          art={
            <AppWindow title="trace · bookings" bodyClassName="py-10">
              <TraceFigure />
            </AppWindow>
          }
        />
        <FeatureRow
          kicker="Nothing quiet"
          n="05"
          title="What isn't priced is listed."
          rest="With its page."
          body="Penalties, warranty, source code handover: what the document asks for but the price leaves out comes back as a list, with questions to ask the client."
          art={
            <AppWindow title="requirement.pdf · not in the price">
              <NotPricedFigure />
            </AppWindow>
          }
        />
        <FeatureRow
          flip
          kicker="People and time"
          n="06"
          title="The team and the time it takes."
          body="Developers, the people who check AI-written code, testers and designers, by role, with the months to build."
          art={
            <AppWindow title="result · team" bodyClassName="py-10">
              <TeamFigure />
            </AppWindow>
          }
        />
      </Section>

      {/* Three steps, as columns between rules */}
      <Section className="border-t py-20 sm:py-28">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div className="flex flex-col gap-5">
            <Kicker n="07">How it goes</Kicker>
            <Title claim="Three steps.">About as long as making tea.</Title>
          </div>
          <TextLink href="/how-it-works">The full walk-through</TextLink>
        </div>
        <ol className="mt-14 grid gap-10 md:grid-cols-3 md:gap-8">
          {STEPS.map((s, i) => (
            <li
              key={s.title}
              data-reveal
              style={delay(i)}
              className="flex flex-col gap-3 border-t-2 border-foreground/10 pt-6 first:border-tape"
            >
              <span className="font-mono text-sm text-muted-foreground">
                0{i + 1}
              </span>
              <h3 className="font-wide text-2xl">{s.title}</h3>
              <p className="text-muted-foreground">{s.body}</p>
            </li>
          ))}
        </ol>
      </Section>

      {/* Questions people ask first */}
      <Section>
        <Faq
          title="Questions people ask first."
          rest="Straight answers."
          items={FAQ}
        />
      </Section>

      <StartBand
        title="Put the spreadsheet down."
        rest="Let Aakalan do the sums."
        aside={<Keypad />}
      />
    </>
  );
}
