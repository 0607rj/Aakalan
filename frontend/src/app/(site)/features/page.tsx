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
import { FeatureMosaic } from "@/components/site/page-art";
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

export default function FeaturesPage() {
  return (
    <>
      <PageIntro
        title="Everything that goes into a fair software price."
        art={<FeatureMosaic />}
      >
        It reads what you need, asks what it can&apos;t read, and shows where
        every number comes from.
      </PageIntro>

      <Section>
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

      <Section className="border-t py-20 sm:py-28">
        <Kicker n="06">Also included</Kicker>
        <Title claim="The rest of what a quote needs." className="mt-5" />
        <dl className="mt-14 grid gap-x-8 gap-y-10 sm:grid-cols-2 lg:grid-cols-4">
          {ALSO.map((a, i) => (
            <div
              key={a.title}
              data-reveal
              style={{ "--rd": i } as React.CSSProperties}
              className="flex flex-col gap-2 border-t pt-6"
            >
              <a.icon
                size={24}
                weight="duotone"
                aria-hidden="true"
                className="mb-2 text-tape"
              />
              <dt className="text-lg font-semibold">{a.title}</dt>
              <dd className="text-muted-foreground">{a.body}</dd>
            </div>
          ))}
        </dl>
      </Section>

      <StartBand />
    </>
  );
}
