import type { Metadata } from "next";
import Link from "next/link";

import {
  DocumentMockup,
  EstimateMockup,
  NotPricedMockup,
  QuestionMockup,
  TeamMockup,
} from "@/components/site/mockups";
import { PageIntro, Section, StartBand } from "@/components/site/sections";

export const metadata: Metadata = {
  title: "How it works · Aakalan",
};

const STEPS = [
  {
    title: "Choose how to start",
    body: "Upload the requirement document if you have one. If not, pick the kind of software: a public portal, software for your staff, an online store, a booking app, an AI chatbot or something else.",
    tip: "A saved template starts you with an earlier estimate's answers.",
    art: <DocumentMockup />,
  },
  {
    title: "Tick what it should do",
    body: "The usual features for your kind of software come first, with the most common already ticked. Write a few lines about it and Aakalan ticks the ones you describe, showing the words it matched. Anything missing, add it yourself.",
    tip: "With a document, every feature found shows its page and sentence.",
    art: <EstimateMockup />,
  },
  {
    title: "Answer about ten questions",
    body: "A first version or the full product, website or app too, how many people will use it, other software to connect, old data, where it runs and how long it should be looked after. One question per screen, in plain words.",
    tip: "Not sure? Choose “Not sure”: we use the usual answer and widen the range.",
    art: <QuestionMockup />,
  },
  {
    title: "Add details if you know them",
    body: "How bad an hour of downtime is, a security audit, monthly reports, a ready design, how much the chatbot will be used, help at launch. Skip anything you don't know.",
    tip: "Check every answer on one screen before calculating.",
    art: null,
  },
  {
    title: "Read the result",
    body: "The low, likely and high cost; the building cost of each feature with and without AI tools; the team by role and months to build; everything inside the price; costs paid to others; and similar real projects.",
    tip: "Download the PDF report or the Excel bill of quantities to share.",
    art: <TeamMockup />,
  },
  {
    title: "Check what is not priced",
    body: "When you upload a document, Aakalan lists what it asks for that the estimate leaves out, such as penalties or warranty, and drafts questions to send the client about vague or missing points.",
    tip: "Ask, update the answers, and calculate again for a narrower range.",
    art: <NotPricedMockup />,
  },
];

export default function HowItWorksPage() {
  return (
    <>
      <PageIntro title="From an idea or a document to a cost range, step by step.">
        Six steps, most of them a single click. Aakalan&apos;s AI only reads and
        suggests; every number is worked out by a fixed set of formulas, so the
        same answers always give the same price.
      </PageIntro>

      <Section className="py-12 sm:py-16">
        <ol className="relative flex flex-col gap-16 border-l-2 border-dashed border-border pl-8 sm:pl-12">
          {STEPS.map((step, i) => (
            <li
              key={step.title}
              className="relative grid gap-8 lg:grid-cols-[1fr_0.9fr]"
            >
              <span
                aria-hidden="true"
                className="font-wide absolute top-0 -left-[3.05rem] flex size-10 items-center justify-center rounded-full bg-tape text-sm font-semibold text-primary-foreground ring-4 ring-background sm:-left-[4.05rem]"
              >
                {i + 1}
              </span>
              <div className="flex flex-col gap-3">
                <h2 data-reveal className="font-wide text-2xl font-semibold">
                  {step.title}
                </h2>
                <p className="text-lg text-muted-foreground">{step.body}</p>
                <p className="w-fit rounded-xl bg-tape-soft px-3 py-2 text-sm">
                  {step.tip}
                </p>
              </div>
              {step.art ? <div className="max-w-md">{step.art}</div> : null}
            </li>
          ))}
        </ol>
      </Section>

      <div className="border-y bg-card">
        <Section className="grid gap-8 py-16 md:grid-cols-2">
          <div>
            <h2 data-reveal className="font-wide text-2xl font-semibold">
              What happens to your document
            </h2>
            <p className="mt-3 text-muted-foreground">
              It stays inside your organisation&apos;s account. The text is sent
              only to the AI service your company has set up, to read it, and is
              treated as data, never as instructions. Without an AI key, a
              keyword reader runs on our own server instead.
            </p>
          </div>
          <div>
            <h2 data-reveal className="font-wide text-2xl font-semibold">
              Where the prices come from
            </h2>
            <p className="mt-3 text-muted-foreground">
              Day rates, cloud prices and service fees are stored with their
              source and date. Each estimate keeps the versions it used, so it
              never changes later; re-pricing at today&apos;s rates makes a new
              version. See{" "}
              <Link
                href="/features"
                className="font-semibold underline underline-offset-4"
              >
                all features
              </Link>
              .
            </p>
          </div>
        </Section>
      </div>

      <StartBand />
    </>
  );
}
