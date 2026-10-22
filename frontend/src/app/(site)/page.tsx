import type { Metadata } from "next";
import Link from "next/link";

import {
  DocumentMockup,
  EstimateMockup,
  NotPricedMockup,
  QuestionMockup,
  RangeTape,
  TeamMockup,
} from "@/components/site/mockups";
import { Section, StartBand } from "@/components/site/sections";
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
    body: "Low, likely and high cost, the cost of each feature with and without AI tools, the team needed and what the document asks for that is not priced.",
    art: <TeamMockup />,
  },
];

export default function HomePage() {
  return (
    <>
      {/* Hero */}
      <Section className="grid items-center gap-12 pt-14 pb-16 sm:pt-20 lg:grid-cols-[1.05fr_1fr] lg:pb-24">
        <div className="flex flex-col gap-6">
          <h1 className="font-wide text-[2.6rem] leading-[1.02] font-extrabold sm:text-6xl">
            What should this software cost, now that AI writes much of the code?
          </h1>
          <p className="max-w-xl text-lg text-muted-foreground">
            Aakalan prices software by what is built, feature by feature, the
            way teams build it today. You get the low, likely and high cost, and
            what the same work would have cost without AI tools.
          </p>
          <div className="flex flex-wrap gap-3">
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
          <p className="text-sm text-muted-foreground">
            Checked against 56 real Indian projects with published prices.
          </p>
        </div>
        <EstimateMockup className="lg:ml-6" />
      </Section>

      {/* The problem */}
      <div className="border-y bg-card">
        <Section className="grid gap-10 py-16 sm:py-20 lg:grid-cols-[0.8fr_1.2fr]">
          <div className="flex flex-col gap-4">
            <h2 className="font-wide text-3xl leading-tight font-extrabold sm:text-4xl">
              Hourly rates were made for a world where people typed every line.
            </h2>
            <p className="text-muted-foreground">
              AI tools now draft code, tests and documents in minutes, and
              someone still has to read, test and fix what they write. A fair
              price has to count both.
            </p>
          </div>
          <div className="min-w-0 overflow-x-auto">
            <table className="w-full min-w-[34rem] text-left text-sm">
              <thead>
                <tr className="border-b text-muted-foreground">
                  <th className="py-3 pr-4 font-medium" />
                  <th className="py-3 pr-4 font-medium">Priced by the hour</th>
                  <th className="py-3 font-semibold text-foreground">
                    Priced by Aakalan
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {OLD_VS_NEW.map((row) => (
                  <tr key={row.topic} className="align-top">
                    <th scope="row" className="py-4 pr-4 font-semibold">
                      {row.topic}
                    </th>
                    <td className="py-4 pr-4 text-muted-foreground">
                      {row.old}
                    </td>
                    <td className="py-4">{row.now}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      </div>

      {/* How it works, short */}
      <Section className="py-16 sm:py-24">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <h2 className="font-wide max-w-xl text-3xl leading-tight font-extrabold sm:text-4xl">
            Three steps, about as long as making tea.
          </h2>
          <Link
            href="/how-it-works"
            className="text-sm font-semibold underline underline-offset-4"
          >
            The full walk-through
          </Link>
        </div>
        <ol className="mt-10 grid gap-10 lg:grid-cols-3">
          {STEPS.map((step, i) => (
            <li key={step.title} className="flex flex-col gap-4">
              <div className="flex items-baseline gap-3">
                <span className="font-wide flex size-9 shrink-0 items-center justify-center rounded-full bg-tape text-sm font-extrabold">
                  {i + 1}
                </span>
                <h3 className="text-lg font-bold">{step.title}</h3>
              </div>
              <p className="text-muted-foreground">{step.body}</p>
              {step.art}
            </li>
          ))}
        </ol>
      </Section>

      {/* What is inside */}
      <div className="border-y bg-card">
        <Section className="grid items-start gap-12 py-16 sm:py-20 lg:grid-cols-2">
          <div className="flex flex-col gap-5">
            <h2 className="font-wide text-3xl leading-tight font-extrabold sm:text-4xl">
              Nothing hidden inside the total.
            </h2>
            <ul className="flex flex-col gap-4 text-muted-foreground">
              <li>
                <strong className="text-foreground">
                  Each feature on its own line,
                </strong>{" "}
                with and without AI tools, so you can drop one and see the price
                move.
              </li>
              <li>
                <strong className="text-foreground">
                  The people behind it:
                </strong>{" "}
                how many developers, testers and designers, and for how long.
              </li>
              <li>
                <strong className="text-foreground">
                  Paid to others, listed apart:
                </strong>{" "}
                SMS, maps, app stores and servers you already own.
              </li>
              <li>
                <strong className="text-foreground">
                  What the document asks for that is not priced,
                </strong>{" "}
                with its page, plus questions to send the client.
              </li>
            </ul>
          </div>
          <div className="grid items-start gap-5 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
            <TeamMockup />
            <NotPricedMockup />
          </div>
        </Section>
      </div>

      {/* Honest about accuracy */}
      <Section className="grid gap-10 py-16 sm:py-24 lg:grid-cols-[1fr_1fr]">
        <div className="flex flex-col gap-4">
          <h2 className="font-wide text-3xl leading-tight font-extrabold sm:text-4xl">
            A range, because nobody knows the exact number yet.
          </h2>
          <p className="text-muted-foreground">
            Aakalan prices the hours the work takes, not what vendors charged,
            and shows what 56 real Indian projects of the same size were bought
            for next to it, as published. Contract prices are not hours, so they
            cannot prove the estimate, and the range has not yet been checked
            against what finished projects really cost. So Aakalan shows a
            range, says where it comes from, and widens it when you answer
            &ldquo;not sure&rdquo;.
          </p>
          <Link
            href="/about"
            className="w-fit text-sm font-semibold underline underline-offset-4"
          >
            How we test the prices
          </Link>
        </div>
        <div className="flex flex-col justify-center gap-2 rounded-[22px] border bg-card p-6">
          <span className="text-sm text-muted-foreground">
            Example: the same app, answered with three &ldquo;not sure&rdquo;s
          </span>
          <RangeTape
            low={1_200_000}
            likely={1_900_000}
            high={3_000_000}
            scaleMax={3_300_000}
          />
          <span className="text-sm text-muted-foreground">
            Find out the answers and calculate again for a narrower range.
          </span>
        </div>
      </Section>

      <StartBand />
    </>
  );
}
