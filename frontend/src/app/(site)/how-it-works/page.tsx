import type { Metadata } from "next";

import {
  DocumentFigure,
  FeatureCostFigure,
  NotPricedFigure,
  QuestionFigure,
} from "@/components/site/illustrations";
import { FlowFigure } from "@/components/site/page-art";
import {
  AppWindow,
  Kicker,
  PageIntro,
  Section,
  StartBand,
  Title,
} from "@/components/site/sections";

export const metadata: Metadata = {
  title: "How it works · Aakalan",
};

interface Step {
  title: string;
  body: string;
  tip: string;
  art?: { title: string; figure: React.ReactNode };
}

const STEPS: Step[] = [
  {
    title: "Choose how to start",
    body: "Upload the requirement document, or pick the kind of software: portal, staff tool, store, booking app, chatbot.",
    tip: "A saved template starts you with earlier answers.",
    art: { title: "requirement.pdf · page 4", figure: <DocumentFigure /> },
  },
  {
    title: "Tick what it should do",
    body: "The usual features come first. Write a few lines and Aakalan ticks the ones you describe.",
    tip: "From a document, each feature shows its page.",
  },
  {
    title: "Answer about ten questions",
    body: "First version or full product, users, hosting, years of support. One per screen.",
    tip: "Not sure? Say so: the range widens.",
    art: { title: "question 3 of 10", figure: <QuestionFigure /> },
  },
  {
    title: "Add details if you know them",
    body: "Uptime, security audit, people online at once, help at launch. Skip what you don't know.",
    tip: "Check every answer on one screen.",
  },
  {
    title: "Read the result",
    body: "Low, likely and high cost, each feature with and without AI tools, the team and the months.",
    tip: "Download the PDF report or Excel bill of quantities.",
    art: { title: "result · features", figure: <FeatureCostFigure /> },
  },
  {
    title: "Check what is not priced",
    body: "From a document: what it asks for that the price leaves out, and questions for the client.",
    tip: "Ask, update, calculate again.",
    art: {
      title: "requirement.pdf · not in the price",
      figure: <NotPricedFigure />,
    },
  },
];

const PROMISES = [
  {
    title: "Your document stays yours.",
    body: "Only your organisation sees it. The text goes only to the AI service your company set up, and is read as data, never as instructions.",
  },
  {
    title: "Rates with a source and a date.",
    body: "Every estimate keeps the rates it used, so it never changes later. Re-pricing at today's rates makes a new version.",
  },
];

const delay = (rd: number) => ({ "--rd": rd }) as React.CSSProperties;

export default function HowItWorksPage() {
  return (
    <>
      <PageIntro
        title="From an idea or a document to a price."
        rest="Step by step."
        art={<FlowFigure />}
      >
        AI only reads and suggests. Fixed formulas work out every number, so the
        same answers always give the same price.
      </PageIntro>

      {/* The steps: a big mono number, the words, and the screen when there is one */}
      <Section>
        <ol>
          {STEPS.map((step, i) => (
            <li
              key={step.title}
              className="grid grid-cols-1 gap-8 border-t py-12 first:border-t-0 sm:py-16 lg:grid-cols-[7rem_1fr_1fr] lg:gap-12"
            >
              <span
                data-reveal
                className={`font-display text-5xl leading-none ${i === 0 ? "text-tape" : "text-foreground/15"}`}
              >
                0{i + 1}
              </span>
              <div data-reveal className="flex flex-col gap-4">
                <h2 className="font-wide text-[1.75rem] leading-tight sm:text-[2.2rem]">
                  {step.title}
                </h2>
                <p className="max-w-md text-lg leading-relaxed text-muted-foreground">
                  {step.body}
                </p>
                <p className="flex items-center gap-2.5 text-sm">
                  <span
                    aria-hidden="true"
                    className="size-1.5 shrink-0 rounded-full bg-tape"
                  />
                  {step.tip}
                </p>
              </div>
              {step.art ? (
                <div data-reveal style={delay(1)}>
                  <AppWindow title={step.art.title}>
                    {step.art.figure}
                  </AppWindow>
                </div>
              ) : null}
            </li>
          ))}
        </ol>
      </Section>

      {/* Two promises, as columns between rules */}
      <Section className="border-t py-20 sm:py-28">
        <Kicker>Kept the same on every estimate</Kicker>
        <Title claim="Private by default." className="mt-5">
          Fixed once it is made.
        </Title>
        <div className="mt-14 grid gap-10 md:grid-cols-2 md:gap-8">
          {PROMISES.map((p, i) => (
            <div
              key={p.title}
              data-reveal
              style={delay(i)}
              className="flex flex-col gap-3 border-t-2 border-foreground/10 pt-6 first:border-tape"
            >
              <h3 className="font-wide text-2xl">{p.title}</h3>
              <p className="max-w-md text-muted-foreground">{p.body}</p>
            </div>
          ))}
        </div>
      </Section>

      <StartBand />
    </>
  );
}
