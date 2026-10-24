import type { Metadata } from "next";
import Link from "next/link";

import { CostSky } from "@/components/site/cost-sky";
import { Keypad } from "@/components/site/keypad";
import {
  DocumentMockup,
  EstimateMockup,
  FeatureBarsFigure,
  NotPricedMockup,
  QuestionMockup,
  RangeWidenFigure,
  TeamMockup,
  TraceFigure,
} from "@/components/site/mockups";
import { Section, Title } from "@/components/site/sections";
import { buttonVariants } from "@/components/ui/button";

export const metadata: Metadata = {
  title: "Aakalan · What should this software cost?",
};

const OLD_VS_NEW = [
  {
    topic: "How the work is counted",
    old: "Hours a person would spend typing every line",
    now: "Each feature at the level you need: basic, standard or advanced",
  },
  {
    topic: "AI tools",
    old: "Ignored, or a vague discount at the end",
    now: "Saving worked out task by task, with the time people spend checking the AI's work",
  },
  {
    topic: "What the total includes",
    old: "Building only",
    now: "Building, launch, servers, support for the years you choose, and tax",
  },
  {
    topic: "Where a number comes from",
    old: "Ask the person who made the sheet",
    now: "Every line traces back to a feature, a rate with its source, and a formula",
  },
];

const SHOWCASE = [
  {
    claim: "A low, likely and high cost.",
    rest: "For building, launch, servers, support for the years you choose, and tax.",
    art: <EstimateMockup />,
  },
  {
    claim: "Each feature on its own line.",
    rest: "With and without AI tools, so you can drop one and see the price move.",
    art: <FeatureBarsFigure />,
  },
  {
    claim: "Every number has an address.",
    rest: "AI only reads the document. Fixed formulas and dated rates work out every figure, so the same answers always give the same price.",
    art: <TraceFigure />,
  },
  {
    claim: "What is not priced is listed.",
    rest: "Penalties, warranty, handover: with the page they are on, plus questions to send the client.",
    art: <NotPricedMockup />,
  },
];

const STEPS = [
  {
    title: "Say what you want to build",
    body: "Pick the kind of software and tick its features, write a few lines about it, or upload the requirement document.",
    art: <DocumentMockup />,
  },
  {
    title: "Answer ten short questions",
    body: "How many people will use it, where it runs, how long it should be looked after. Not sure? Say so and the range widens.",
    art: <QuestionMockup />,
  },
  {
    title: "Get the range and the reasons",
    body: "Low, likely and high cost, each feature with and without AI tools, the team needed and what the document asks for that is not priced.",
    art: <TeamMockup />,
  },
];

const delay = (rd: number) => ({ "--rd": rd }) as React.CSSProperties;

export default function HomePage() {
  return (
    <>
      {/* Hero: the sky of possible costs, the claim across its foot */}
      <section className="relative">
        <div className="mx-auto flex max-w-6xl flex-col items-center px-4 pt-8 text-center sm:px-6 sm:pt-12">
          <div className="rise-in relative aspect-[4/3] w-full max-w-5xl overflow-hidden rounded-[22px] bg-card shadow-[0_0_0_1px_rgb(27_36_51/0.08),0_40px_120px_rgb(27_36_51/0.16)] sm:aspect-[2/1]">
            <CostSky />
            <div
              aria-hidden="true"
              className="pointer-events-none absolute inset-0 bg-[linear-gradient(transparent_45%,rgb(255_255_255/0.85)_100%)]"
            />
            <span className="eyebrow absolute top-4 left-4 flex items-center gap-2 text-left text-foreground/70">
              <span
                className="pulse-dot size-1.5 rounded-full bg-tape"
                aria-hidden="true"
              />
              30,000 possible costs of one project
            </span>
          </div>
          <h1
            className="rise-in font-display relative -mt-[0.6em] text-[clamp(3.2rem,10.5vw,7.5rem)] leading-[0.95]"
            style={delay(1.5)}
          >
            Price what gets <em className="text-tape-2">built</em>.
          </h1>
          <p
            className="rise-in mt-6 max-w-2xl text-lg text-muted-foreground sm:text-xl"
            style={delay(2.5)}
          >
            What should this software cost, now that AI writes much of the code?
            Aakalan prices it feature by feature, the way teams build it today,
            with the low, likely and high cost.
          </p>
          <div
            className="rise-in mt-8 flex flex-wrap justify-center gap-3"
            style={delay(3)}
          >
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
          <p className="rise-in eyebrow mt-6 normal-case" style={delay(3.5)}>
            Feature by feature · AI-era hours · checked against 56 real Indian
            projects
          </p>
        </div>
      </section>

      {/* The problem */}
      <Section className="pt-14 pb-12 sm:pt-20 sm:pb-16">
        <Title claim="Hourly rates were made for a world where people typed every line.">
          AI tools now draft code, tests and documents in minutes, and someone
          still has to read, test and fix what they write. A fair price counts
          both.
        </Title>
        <div className="mt-12 grid gap-4 md:grid-cols-2">
          <div data-reveal className="rounded-[22px] border p-6 sm:p-8">
            <p className="eyebrow">Priced by the hour</p>
            <dl className="mt-5 flex flex-col divide-y">
              {OLD_VS_NEW.map((row) => (
                <div key={row.topic} className="flex flex-col gap-1 py-4">
                  <dt className="text-sm text-muted-foreground">{row.topic}</dt>
                  <dd className="text-foreground/55 line-through decoration-foreground/30">
                    {row.old}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
          <div
            data-reveal
            style={delay(1)}
            className="panel relative overflow-hidden rounded-[22px] border-tape/30 p-6 sm:p-8"
          >
            <div
              aria-hidden="true"
              className="pointer-events-none absolute inset-0 bg-[radial-gradient(70%_60%_at_100%_0%,rgb(11_120_184/0.12),transparent_70%)]"
            />
            <p className="eyebrow relative text-tape">Priced by Aakalan</p>
            <dl className="relative mt-5 flex flex-col divide-y">
              {OLD_VS_NEW.map((row) => (
                <div key={row.topic} className="flex flex-col gap-1 py-4">
                  <dt className="text-sm text-muted-foreground">{row.topic}</dt>
                  <dd>{row.now}</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      </Section>

      {/* What you get, each with its picture */}
      <Section className="pb-12 sm:pb-16">
        <Title center claim="Nothing hidden inside the total.">
          Every part of the price is on the page, with its reason.
        </Title>
        <div className="mt-14 grid gap-5 lg:grid-cols-2">
          {SHOWCASE.map((s, i) => (
            <article
              key={s.claim}
              data-reveal
              style={delay(i % 2)}
              className="flex flex-col gap-6 rounded-[26px] border bg-foreground/[0.015] p-6 sm:p-8"
            >
              <p className="max-w-md text-lg leading-snug">
                <span className="font-semibold">{s.claim}</span>{" "}
                <span className="text-muted-foreground">{s.rest}</span>
              </p>
              <div className="mt-auto">{s.art}</div>
            </article>
          ))}
        </div>
      </Section>

      {/* How it works, short */}
      <Section className="pb-12 sm:pb-16">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <Title claim="Three steps,">about as long as making tea.</Title>
          <Link
            href="/how-it-works"
            className="text-sm font-semibold text-tape-2 underline-offset-4 hover:underline"
          >
            The full walk-through →
          </Link>
        </div>
        <ol className="mt-12 grid gap-10 lg:grid-cols-3">
          {STEPS.map((step, i) => (
            <li
              key={step.title}
              data-reveal
              style={delay(i)}
              className="flex flex-col gap-4"
            >
              <span className="font-mono text-sm text-tape">0{i + 1}</span>
              <h3 className="text-xl font-semibold">{step.title}</h3>
              <p className="text-muted-foreground">{step.body}</p>
              <div className="mt-2">{step.art}</div>
            </li>
          ))}
        </ol>
      </Section>

      {/* Honest about accuracy */}
      <Section className="grid items-center gap-12 pb-12 sm:pb-16 lg:grid-cols-2">
        <div className="flex flex-col gap-5">
          <Title claim="A range, because nobody knows the exact number yet." />
          <p data-reveal className="text-muted-foreground">
            Aakalan prices the hours the work takes, not what vendors charged,
            and shows what 56 real Indian projects of the same size were bought
            for next to it, as published. Contract prices are not hours, so they
            cannot prove the estimate, and the range has not yet been checked
            against what finished projects really cost. So Aakalan shows a
            range, says where it comes from, and widens it when you answer
            &ldquo;not sure&rdquo;.
          </p>
          <Link
            data-reveal
            href="/about"
            className="w-fit text-sm font-semibold text-tape-2 underline-offset-4 hover:underline"
          >
            How we test the prices →
          </Link>
        </div>
        <RangeWidenFigure />
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
              className="font-display text-5xl leading-[1] sm:text-7xl"
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
