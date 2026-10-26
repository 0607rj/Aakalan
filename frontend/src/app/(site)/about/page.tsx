import type { Metadata } from "next";
import { ArrowDownIcon, ArrowUpIcon } from "@phosphor-icons/react/dist/ssr";

import { TraceFigure } from "@/components/site/illustrations";
import { MeaningFigure } from "@/components/site/page-art";
import {
  AppWindow,
  Kicker,
  PageIntro,
  Section,
  StartBand,
  Title,
} from "@/components/site/sections";

export const metadata: Metadata = {
  title: "About · Aakalan",
};

const ANSWER = [
  "Each feature at the size it needs",
  "The saving AI tools really bring, task by task",
  "The checking that saving demands",
  "Everything after launch",
];

const TESTS = [
  {
    size: "Small projects",
    up: false,
    text: "Real contracts mostly came in below ours: lowest bids, simpler builds.",
  },
  {
    size: "Medium projects",
    up: false,
    text: "Real contracts mostly came in a little below ours.",
  },
  {
    size: "Large projects",
    up: true,
    text: "Real contracts mostly came in above ours: hardware and licences we can't see yet.",
  },
];

const PRINCIPLES = [
  {
    title: "Price what is built, not who asks",
    body: "A login screen costs the same for everyone.",
  },
  {
    title: "AI reads, formulas count",
    body: "AI suggests features. It never sets, edits or rounds a price.",
  },
  {
    title: "Every number has a source",
    body: "Feature, rate, where the rate came from, and the formula.",
  },
  {
    title: "Honest about how sure we are",
    body: "A range with its reasons, not one number pretending to be exact.",
  },
];

const AUDIENCE = [
  {
    title: "Companies quoting a project",
    body: "Price a quote from the document in minutes, with your own rates.",
  },
  {
    title: "People planning to build",
    body: "Know what an app should cost before asking for quotes.",
  },
  {
    title: "Departments budgeting",
    body: "A realistic budget with security, support and hosting included.",
  },
];

const delay = (rd: number) => ({ "--rd": rd }) as React.CSSProperties;

export default function AboutPage() {
  return (
    <>
      <PageIntro
        title="Aakalan means estimation."
        rest="Because software prices stopped adding up."
        art={<MeaningFigure />}
      >
        AI now does much of the typing. Nobody agrees what that does to the
        price, so quotes drift further apart.
      </PageIntro>

      {/* The question and our answer */}
      <Section className="grid grid-cols-1 items-center gap-12 py-20 sm:py-28 lg:grid-cols-2 lg:gap-16">
        <div className="flex flex-col gap-6">
          <Kicker n="01">The question</Kicker>
          <Title claim="How do you price software when AI writes much of the code?">
            People still design, check and look after it.
          </Title>
          <p data-reveal className="text-lg text-muted-foreground">
            Price the work itself, and show the working:
          </p>
          <ol data-reveal className="flex flex-col border-t">
            {ANSWER.map((a, i) => (
              <li
                key={a}
                className="flex items-baseline gap-4 border-b py-3.5 font-medium"
              >
                <span className="font-mono text-xs text-muted-foreground">
                  0{i + 1}
                </span>
                {a}
              </li>
            ))}
          </ol>
        </div>
        <div data-reveal style={delay(1)}>
          <AppWindow title="where one number comes from" bodyClassName="py-10">
            <TraceFigure />
          </AppWindow>
        </div>
      </Section>

      {/* How we test the prices: a ruled table */}
      <Section className="border-t py-20 sm:py-28">
        <Kicker n="02">How we test the prices</Kicker>
        <Title claim="Checked against real Indian projects." className="mt-5">
          Not tuned to them: our prices come from hours and rates.
        </Title>
        <dl data-reveal className="mt-12 flex flex-col border-t">
          {TESTS.map((t) => {
            const Icon = t.up ? ArrowUpIcon : ArrowDownIcon;
            return (
              <div
                key={t.size}
                className="grid gap-2 border-b py-5 sm:grid-cols-[14rem_1fr] sm:gap-8"
              >
                <dt className="flex items-center gap-2.5 font-semibold">
                  <Icon
                    size={16}
                    weight="bold"
                    aria-hidden="true"
                    className={t.up ? "text-warm" : "text-tape"}
                  />
                  {t.size}
                </dt>
                <dd className="text-muted-foreground">{t.text}</dd>
              </div>
            );
          })}
        </dl>
        <p
          data-reveal
          className="mt-6 max-w-2xl font-mono text-xs leading-relaxed text-muted-foreground"
        >
          Not checked yet: what finished projects really cost. Recorded outcomes
          will do that, so treat every estimate as a guide.
        </p>
      </Section>

      {/* What we hold to: numbered columns */}
      <Section className="border-t py-20 sm:py-28">
        <Kicker n="03">What we hold to</Kicker>
        <Title claim="Four rules." className="mt-5">
          Every estimate follows them.
        </Title>
        <dl className="mt-14 grid gap-x-8 gap-y-10 sm:grid-cols-2 lg:grid-cols-4">
          {PRINCIPLES.map((p, i) => (
            <div
              key={p.title}
              data-reveal
              style={delay(i)}
              className="flex flex-col gap-3 border-t-2 border-foreground/10 pt-6 first:border-tape"
            >
              <span className="font-mono text-sm text-muted-foreground">
                0{i + 1}
              </span>
              <dt className="font-wide text-xl leading-snug">{p.title}</dt>
              <dd className="text-muted-foreground">{p.body}</dd>
            </div>
          ))}
        </dl>
      </Section>

      {/* Who it is for: a ruled list */}
      <Section className="grid grid-cols-1 gap-10 border-t py-20 sm:py-28 lg:grid-cols-[0.8fr_1.2fr] lg:gap-16">
        <div className="flex flex-col gap-5">
          <Kicker n="04">Who it is for</Kicker>
          <Title
            claim="Anyone who needs the number"
            className="text-[2rem] sm:text-[2.6rem]"
          >
            before the work starts.
          </Title>
        </div>
        <ul data-reveal className="flex flex-col border-t">
          {AUDIENCE.map((a) => (
            <li key={a.title} className="flex flex-col gap-1 border-b py-6">
              <span className="font-wide text-xl">{a.title}</span>
              <span className="text-muted-foreground">{a.body}</span>
            </li>
          ))}
        </ul>
      </Section>

      <StartBand />
    </>
  );
}
