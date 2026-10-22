import type { Metadata } from "next";

import {
  DocumentMockup,
  EstimateMockup,
  NotPricedMockup,
  QuestionMockup,
  TeamMockup,
} from "@/components/site/mockups";
import { PageIntro, Section, StartBand } from "@/components/site/sections";

export const metadata: Metadata = {
  title: "Features · Aakalan",
};

interface Feature {
  title: string;
  body: string;
  points: string[];
  art: React.ReactNode;
}

const FEATURES: Feature[] = [
  {
    title: "Priced by what is built",
    body: "The same feature costs the same for a startup or a ministry. A smaller project costs less because it builds less, never because of who orders it.",
    points: [
      "Every feature at the level you need: basic, standard or advanced",
      "A first simple version (MVP) or the full product, in one answer",
      "Security audits, formal reports and accessibility only when you ask for them",
    ],
    art: <EstimateMockup />,
  },
  {
    title: "Priced for how software is built today",
    body: "AI tools save more on some work than others. Aakalan works the saving out task by task, then adds back the time people spend reviewing and fixing what the AI wrote.",
    points: [
      "Every cost line shown with AI tools and without them",
      "Saving by task: most on documents and forms, least on design decisions, connecting systems and checking",
      "Saving shown per cost line, with the review time added back",
    ],
    art: <TeamMockup />,
  },
  {
    title: "Reads your requirement document",
    body: "Upload the RFP, SRS or scope of work as PDF or Word. Each feature it finds comes with the page and the exact sentence, so you can check it in seconds.",
    points: [
      "Features, numbers (users, years of support, deadline) and answers filled in for you",
      "Corrigenda and later documents override earlier ones, and say what changed",
      "Vague or missing points turned into questions to send the client",
    ],
    art: <DocumentMockup />,
  },
  {
    title: "Nothing left out quietly",
    body: "If the document asks for something the estimate does not price, such as penalties, warranty or a source-code handover, it is listed with its page.",
    points: [
      "Costs paid to others listed apart: SMS, maps, app stores, your own servers",
      "Staff at your office and payment terms priced when the document states them",
      "“Not sure” answers widen the range instead of guessing",
    ],
    art: <NotPricedMockup />,
  },
  {
    title: "Short, plain questions",
    body: "About ten questions, one per screen, in everyday words. Write a few lines about the software and Aakalan ticks the features for you to check.",
    points: [
      "Only the questions that matter for your project are asked",
      "Optional details on one screen, with the usual answer already picked",
      "Each option shows how much it changes the price",
    ],
    art: <QuestionMockup />,
  },
];

const ALSO = [
  {
    title: "The team and the timeline",
    body: "People needed by role, months to build, and the support team after launch.",
  },
  {
    title: "Reports to share",
    body: "A PDF report and an Excel bill of quantities, with the same numbers as the screen.",
  },
  {
    title: "Templates and comparisons",
    body: "Save an estimate as a template, compare hosting options, re-price at today's rates.",
  },
  {
    title: "Your own rates",
    body: "Put in your company's day rates, margin and buffer; past estimates never change.",
  },
];

export default function FeaturesPage() {
  return (
    <>
      <PageIntro title="Everything that goes into a fair software price.">
        Aakalan reads what you need, asks what it cannot read, and prices each
        piece of work with the rates and sources shown. Here is what it does.
      </PageIntro>

      <Section className="flex flex-col gap-20 py-16 sm:gap-28 sm:py-24">
        {FEATURES.map((f, i) => (
          <article
            key={f.title}
            className="grid items-center gap-10 lg:grid-cols-2"
          >
            <div className={i % 2 === 1 ? "lg:order-2" : undefined}>
              <h2 className="font-wide text-3xl leading-tight font-extrabold">
                {f.title}
              </h2>
              <p className="mt-3 text-lg text-muted-foreground">{f.body}</p>
              <ul className="mt-6 flex flex-col gap-3">
                {f.points.map((p) => (
                  <li key={p} className="flex gap-3">
                    <span
                      aria-hidden="true"
                      className="mt-2 h-1.5 w-4 shrink-0 rounded-full bg-tape"
                    />
                    <span>{p}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className={i % 2 === 1 ? "lg:order-1" : undefined}>
              {f.art}
            </div>
          </article>
        ))}
      </Section>

      <div className="border-y bg-card">
        <Section className="py-16">
          <h2 className="font-wide text-2xl font-extrabold">Also included</h2>
          <dl className="mt-8 grid gap-x-10 gap-y-8 sm:grid-cols-2">
            {ALSO.map((a) => (
              <div key={a.title} className="border-l-4 border-tape pl-4">
                <dt className="font-bold">{a.title}</dt>
                <dd className="mt-1 text-muted-foreground">{a.body}</dd>
              </div>
            ))}
          </dl>
        </Section>
      </div>

      <StartBand />
    </>
  );
}
