import type { Metadata } from "next";
import {
  ChatCircleDotsIcon,
  FileArrowUpIcon,
  FlagIcon,
  ListChecksIcon,
  LockIcon,
  ReceiptIcon,
  SlidersHorizontalIcon,
  TagIcon,
} from "@phosphor-icons/react/dist/ssr";

import {
  DocumentFigure,
  FeatureCostFigure,
  IconTile,
  type IconType,
  NotPricedFigure,
  QuestionFigure,
} from "@/components/site/illustrations";
import { FlowFigure } from "@/components/site/page-art";
import { PageIntro, Section, StartBand } from "@/components/site/sections";

export const metadata: Metadata = {
  title: "How it works · Aakalan",
};

interface Step {
  icon: IconType;
  title: string;
  body: string;
  tip: string;
  art?: React.ReactNode;
}

const STEPS: Step[] = [
  {
    icon: FileArrowUpIcon,
    title: "Choose how to start",
    body: "Upload the requirement document, or pick the kind of software: portal, staff tool, store, booking app, chatbot.",
    tip: "A saved template starts you with earlier answers.",
    art: <DocumentFigure />,
  },
  {
    icon: ListChecksIcon,
    title: "Tick what it should do",
    body: "The usual features come first. Write a few lines and Aakalan ticks the ones you describe.",
    tip: "From a document, each feature shows its page.",
  },
  {
    icon: ChatCircleDotsIcon,
    title: "Answer about ten questions",
    body: "First version or full product, users, hosting, years of support. One per screen.",
    tip: "Not sure? Say so: the range widens.",
    art: <QuestionFigure />,
  },
  {
    icon: SlidersHorizontalIcon,
    title: "Add details if you know them",
    body: "Uptime, security audit, people online at once, help at launch. Skip what you don't know.",
    tip: "Check every answer on one screen.",
  },
  {
    icon: ReceiptIcon,
    title: "Read the result",
    body: "Low, likely and high cost, each feature with and without AI tools, the team and the months.",
    tip: "Download the PDF report or Excel bill of quantities.",
    art: <FeatureCostFigure />,
  },
  {
    icon: FlagIcon,
    title: "Check what is not priced",
    body: "From a document: what it asks for that the price leaves out, and questions for the client.",
    tip: "Ask, update, calculate again.",
    art: <NotPricedFigure />,
  },
];

const delay = (rd: number) => ({ "--rd": rd }) as React.CSSProperties;

export default function HowItWorksPage() {
  return (
    <>
      <PageIntro
        title="From an idea or a document to a price, step by step."
        art={<FlowFigure />}
      >
        AI only reads and suggests. Fixed formulas work out every number, so the
        same answers always give the same price.
      </PageIntro>

      <Section className="py-12 sm:py-16">
        <ol className="relative flex flex-col gap-12 sm:gap-16">
          <span
            aria-hidden="true"
            className="absolute top-4 bottom-4 left-7 w-0.5 bg-[repeating-linear-gradient(180deg,var(--border)_0_8px,transparent_8px_14px)]"
          />
          {STEPS.map((step, i) => (
            <li
              key={step.title}
              className="relative grid gap-6 pl-20 lg:grid-cols-[1fr_0.9fr] lg:gap-12"
            >
              <IconTile
                icon={step.icon}
                size="lg"
                className={`absolute top-0 left-0 ring-8 ring-background ${i === STEPS.length - 2 ? "bg-tape text-primary-foreground" : ""}`}
              />
              <div data-reveal className="flex flex-col gap-3 pt-2">
                <h2 className="font-wide text-2xl font-semibold">
                  {step.title}
                </h2>
                <p className="text-lg text-muted-foreground">{step.body}</p>
                <p className="w-fit rounded-full bg-tape-soft px-3.5 py-1.5 text-sm font-medium text-tape">
                  {step.tip}
                </p>
              </div>
              {step.art ? (
                <div data-reveal style={delay(1)} className="max-w-md">
                  {step.art}
                </div>
              ) : null}
            </li>
          ))}
        </ol>
      </Section>

      <Section className="pb-12 sm:pb-16">
        <div className="grid gap-4 md:grid-cols-2">
          <div
            data-reveal
            className="flex flex-col gap-4 rounded-[26px] border bg-card p-6 sm:p-8"
          >
            <IconTile icon={LockIcon} />
            <h2 className="font-wide text-2xl font-semibold">
              Your document stays yours
            </h2>
            <p className="text-muted-foreground">
              Only your organisation sees it. The text goes only to the AI
              service your company set up, and is read as data, never as
              instructions.
            </p>
          </div>
          <div
            data-reveal
            style={delay(1)}
            className="flex flex-col gap-4 rounded-[26px] bg-tape-soft/70 p-6 sm:p-8"
          >
            <IconTile icon={TagIcon} tone="warm" />
            <h2 className="font-wide text-2xl font-semibold">
              Rates with a source and a date
            </h2>
            <p className="text-muted-foreground">
              Every estimate keeps the rates it used, so it never changes later.
              Re-pricing at today&apos;s rates makes a new version.
            </p>
          </div>
        </div>
      </Section>

      <StartBand />
    </>
  );
}
