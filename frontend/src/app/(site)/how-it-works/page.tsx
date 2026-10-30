import type { Metadata } from "next";

import { StepNumber } from "@/components/site/step-number";
import {
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
}

const STEPS: Step[] = [
  {
    title: "Choose how to start",
    body: "Upload the requirement document, or pick the kind of software: portal, staff tool, store, booking app, chatbot.",
    tip: "A saved template starts you with earlier answers.",
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
  },
  {
    title: "Check what is not priced",
    body: "From a document: what it asks for that the price leaves out, and questions for the client.",
    tip: "Ask, update, calculate again.",
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

export default function HowItWorksPage() {
  return (
    <>
      <PageIntro
        title="From an idea or a document to a price."
        rest="Step by step."
        scene="path"
        sceneClassName="sm:top-[calc(50svh+15px)]"
      >
        AI only reads and suggests. Fixed formulas work out every number, so the
        same answers always give the same price.
      </PageIntro>

      {/* The steps on one line down the page, the current one's number large beside them */}
      <Section className="grid gap-16 pb-[clamp(72px,10vw,120px)] lg:grid-cols-[minmax(0,1fr)_minmax(0,0.7fr)]">
        <ol>
          {STEPS.map((step, i) => (
            <li
              key={step.title}
              data-reveal
              data-step={i}
              className="relative pb-16 pl-16 last:pb-0 sm:pl-24 lg:pb-20"
            >
              {i < STEPS.length - 1 ? (
                <span
                  aria-hidden="true"
                  className="absolute top-14 bottom-0 left-[21px] border-l border-dashed border-faint sm:top-16 sm:left-[27px]"
                />
              ) : null}
              <span className="soft-card absolute top-0 left-0 grid size-11 place-items-center rounded-full font-mono text-sm font-medium text-tape sm:size-14">
                0{i + 1}
              </span>
              <div className="flex flex-col gap-4">
                <h2 className="font-wide text-[clamp(1.7rem,3vw,2.3rem)] leading-[1.08]">
                  {step.title}
                </h2>
                <p className="max-w-2xl text-lg leading-relaxed text-muted-foreground">
                  {step.body}
                </p>
                <p className="flex items-center gap-2.5 text-sm">
                  <span
                    aria-hidden="true"
                    className="size-1.5 shrink-0 rounded-full bg-tape-bright"
                  />
                  {step.tip}
                </p>
              </div>
            </li>
          ))}
        </ol>
        <div className="hidden lg:flex lg:justify-center">
          <StepNumber titles={STEPS.map((s) => s.title)} />
        </div>
      </Section>

      {/* Two promises, side by side on one dark card */}
      <Section className="pb-[clamp(72px,10vw,120px)]">
        <Kicker>Kept the same on every estimate</Kicker>
        <Title claim="Private by default." className="mt-5">
          Fixed once it is made.
        </Title>
        <div
          data-reveal
          className="dark-card glow-low mt-12 grid md:grid-cols-2"
        >
          {PROMISES.map((p, i) => (
            <div
              key={p.title}
              className="flex flex-col gap-3 border-white/10 p-8 not-last:border-b sm:p-11 md:not-last:border-r md:not-last:border-b-0"
            >
              <span className="font-mono text-sm text-peach">0{i + 1}</span>
              <h3 className="font-wide text-2xl sm:text-3xl">{p.title}</h3>
              <p className="max-w-md text-white/72">{p.body}</p>
            </div>
          ))}
        </div>
      </Section>

      <StartBand
        title="Try it on a real project."
        rest="About ten questions."
      />
    </>
  );
}
