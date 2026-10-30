import type { Metadata } from "next";
import {
  ArrowsClockwiseIcon,
  CoinsIcon,
  FileXlsIcon,
  UsersThreeIcon,
} from "@phosphor-icons/react/dist/ssr";

import {
  AiSavingFigure,
  DocumentFigure,
  FeatureCostFigure,
  NotPricedFigure,
  QuestionFigure,
} from "@/components/site/illustrations";
import {
  AppWindow,
  FeatureRow,
  Kicker,
  PageIntro,
  Section,
  StartBand,
  Title,
} from "@/components/site/sections";

export const metadata: Metadata = {
  title: "Features · Aakalan",
};

const ALSO = [
  {
    icon: UsersThreeIcon,
    title: "Team and timeline",
    body: "People by role and the months to build.",
  },
  {
    icon: FileXlsIcon,
    title: "Reports to share",
    body: "A PDF report and an Excel bill of quantities.",
  },
  {
    icon: ArrowsClockwiseIcon,
    title: "Templates",
    body: "Start from an earlier estimate's answers.",
  },
  {
    icon: CoinsIcon,
    title: "Your own rates",
    body: "Your day rates and margin; old estimates never change.",
  },
];

/** Two rows of uneven width, so the four read as a pair of pairs. */
const ALSO_SHAPE = [
  "dark-card warm lg:col-span-3",
  "soft-card lg:col-span-2",
  "soft-card lg:col-span-2",
  "dark-card glow-low lg:col-span-3",
];

export default function FeaturesPage() {
  return (
    <>
      <PageIntro
        title="Everything that goes into a fair software price."
        scene="blocks"
        sceneClassName="sm:top-[calc(50svh+83px)] sm:left-[calc(50%-24px)]"
      >
        It reads what you need, asks what it can&apos;t read, and shows where
        every number comes from.
      </PageIntro>

      <Section className="pt-4">
        <FeatureRow
          kicker="Per feature"
          n="01"
          title="Priced by what is built."
          rest="Not by who asks."
          body="The same feature costs the same for a startup or a ministry. Each one is priced at the level the project needs."
          points={[
            "Basic, standard or advanced for every feature",
            "A first simple version, or the full product",
            "Security audits only when the project asks for one",
          ]}
          art={
            <AppWindow title="result · features">
              <FeatureCostFigure />
            </AppWindow>
          }
        />
        <FeatureRow
          flip
          tone="open"
          kicker="AI-era work"
          n="02"
          title="Priced for how software is built now."
          body="The saving AI tools bring is worked out task by task, and the time people spend checking the AI's work is added back."
          points={["Every feature with and without AI tools"]}
          art={
            <AppWindow title="ai tools · where they save">
              <AiSavingFigure />
            </AppWindow>
          }
        />
        <FeatureRow
          tone="warm"
          kicker="Your document"
          n="03"
          title="Reads your requirement document."
          rest="And shows its page."
          body="Each feature it finds keeps the page and the sentence it came from, so you can check every one before any price is worked out."
          points={[
            "PDF or Word",
            "A corrigendum overrides the original",
            "Questions to send the client before you bid",
          ]}
          art={
            <AppWindow title="requirement.pdf · page 4">
              <DocumentFigure />
            </AppWindow>
          }
        />
        <FeatureRow
          flip
          tone="open"
          kicker="Nothing quiet"
          n="04"
          title="Nothing left out quietly."
          body="What the document asks for but the price leaves out is listed, with its page. Costs paid to other providers are kept apart."
          points={["Onsite staff priced from the document's own lines"]}
          art={
            <AppWindow title="requirement.pdf · not in the price">
              <NotPricedFigure />
            </AppWindow>
          }
        />
        <FeatureRow
          kicker="The questions"
          n="05"
          title="Short, plain questions."
          rest="About ten."
          body="One per screen, in everyday words, and only the ones your project needs. The usual answer is already picked."
          points={["“Not sure” is an answer: the range widens"]}
          art={
            <AppWindow title="question 3 of 10">
              <QuestionFigure />
            </AppWindow>
          }
        />
      </Section>

      <Section className="py-[clamp(72px,10vw,120px)]">
        <Kicker n="06">Also included</Kicker>
        <Title claim="The rest of what a quote needs." className="mt-5" />
        <dl className="mt-12 grid gap-5 lg:grid-cols-5">
          {ALSO.map((a, i) => (
            <div
              key={a.title}
              data-reveal
              style={{ "--rd": i } as React.CSSProperties}
              className={`flex items-start gap-5 p-8 ${ALSO_SHAPE[i]}`}
            >
              <span className="flex size-12 shrink-0 items-center justify-center rounded-full bg-tape-bright text-white">
                <a.icon size={22} aria-hidden="true" />
              </span>
              <span className="flex flex-col gap-1.5">
                <dt className="font-wide text-[1.45rem] leading-tight">
                  {a.title}
                </dt>
                <dd
                  className={
                    i % 3 === 0 ? "text-white/72" : "text-muted-foreground"
                  }
                >
                  {a.body}
                </dd>
              </span>
            </div>
          ))}
        </dl>
      </Section>

      <StartBand
        title="See it on your own features."
        rest="We'll do the sums."
      />
    </>
  );
}
