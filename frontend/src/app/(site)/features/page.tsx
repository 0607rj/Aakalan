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
  IconTile,
  NotPricedFigure,
  QuestionFigure,
} from "@/components/site/illustrations";
import { FeatureMosaic } from "@/components/site/page-art";
import { PageIntro, Section, StartBand } from "@/components/site/sections";
import { cn } from "@/lib/utils";

export const metadata: Metadata = {
  title: "Features · Aakalan",
};

interface Feature {
  title: string;
  body: string;
  chips: string[];
  art: React.ReactNode;
  cell: string;
}

const FEATURES: Feature[] = [
  {
    title: "Priced by what is built",
    body: "The same feature costs the same for a startup or a ministry.",
    chips: [
      "Basic, standard or advanced",
      "MVP or full product",
      "Audits only when asked",
    ],
    art: <FeatureCostFigure />,
    cell: "lg:col-span-4 bg-tape-soft/70",
  },
  {
    title: "Priced for AI-era work",
    body: "Saving worked out task by task, with the checking added back.",
    chips: ["With and without AI tools"],
    art: <AiSavingFigure />,
    cell: "lg:col-span-2 bg-ai-soft/80",
  },
  {
    title: "Reads your requirement document",
    body: "Each feature it finds shows the page and the sentence.",
    chips: ["PDF or Word", "Corrigenda override", "Questions for the client"],
    art: <DocumentFigure />,
    cell: "lg:col-span-3 border bg-card",
  },
  {
    title: "Nothing left out quietly",
    body: "What the document asks for but the price leaves out is listed.",
    chips: ["Costs paid to others apart", "Onsite staff priced"],
    art: <NotPricedFigure />,
    cell: "lg:col-span-3 bg-warning-muted/70",
  },
  {
    title: "Short, plain questions",
    body: "About ten, one per screen, in everyday words. Only the ones your project needs.",
    chips: ["Usual answer picked", "Not sure widens the range"],
    art: <QuestionFigure />,
    cell: "lg:col-span-6 border bg-card lg:grid lg:grid-cols-2 lg:items-center lg:gap-10",
  },
];

const ALSO = [
  {
    icon: UsersThreeIcon,
    title: "Team and timeline",
    body: "People by role and months to build.",
  },
  {
    icon: FileXlsIcon,
    title: "Reports to share",
    body: "PDF report and Excel bill of quantities.",
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

      <Section className="py-12 sm:py-16">
        <div className="grid gap-4 lg:grid-cols-6">
          {FEATURES.map((f, i) => (
            <article
              key={f.title}
              data-reveal
              style={{ "--rd": i % 2 } as React.CSSProperties}
              className={cn(
                "flex flex-col gap-6 rounded-[26px] p-6 sm:p-8",
                f.cell,
              )}
            >
              <div className="flex flex-col gap-3">
                <h2 className="font-wide text-2xl font-semibold">{f.title}</h2>
                <p className="text-muted-foreground">{f.body}</p>
                <ul className="flex flex-wrap gap-2">
                  {f.chips.map((c) => (
                    <li
                      key={c}
                      className="rounded-full border border-foreground/10 bg-card/80 px-3 py-1 text-xs font-medium"
                    >
                      {c}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="mt-auto">{f.art}</div>
            </article>
          ))}
        </div>
      </Section>

      <Section className="pb-12 sm:pb-16">
        <h2 data-reveal className="font-wide text-2xl font-semibold">
          Also included
        </h2>
        <dl className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {ALSO.map((a, i) => (
            <div
              key={a.title}
              data-reveal
              style={{ "--rd": i } as React.CSSProperties}
              className="flex flex-col gap-3"
            >
              <IconTile icon={a.icon} />
              <dt className="font-semibold">{a.title}</dt>
              <dd className="-mt-2 text-sm text-muted-foreground">{a.body}</dd>
            </div>
          ))}
        </dl>
      </Section>

      <StartBand />
    </>
  );
}
