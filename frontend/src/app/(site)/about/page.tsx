import type { Metadata } from "next";
import {
  ArrowDownIcon,
  ArrowUpIcon,
  BankIcon,
  HandshakeIcon,
  HourglassMediumIcon,
  MagnifyingGlassIcon,
  RobotIcon,
  RocketIcon,
  ScalesIcon,
  SealCheckIcon,
} from "@phosphor-icons/react/dist/ssr";

import { IconTile, TraceFigure } from "@/components/site/illustrations";
import { MeaningFigure } from "@/components/site/page-art";
import { PageIntro, Section, StartBand } from "@/components/site/sections";

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
    icon: ArrowDownIcon,
    text: "Real contracts mostly came in below ours: lowest bids, simpler builds.",
  },
  {
    size: "Medium projects",
    icon: ArrowDownIcon,
    text: "Real contracts mostly came in a little below ours.",
  },
  {
    size: "Large projects",
    icon: ArrowUpIcon,
    text: "Real contracts mostly came in above ours: hardware and licences we can't see yet.",
  },
];

const PRINCIPLES = [
  {
    icon: ScalesIcon,
    title: "Price what is built, not who asks",
    body: "A login screen costs the same for everyone.",
  },
  {
    icon: RobotIcon,
    title: "AI reads, formulas count",
    body: "AI suggests features. It never sets, edits or rounds a price.",
  },
  {
    icon: MagnifyingGlassIcon,
    title: "Every number has a source",
    body: "Feature, rate, where the rate came from, and the formula.",
  },
  {
    icon: SealCheckIcon,
    title: "Honest about how sure we are",
    body: "A range with its reasons, not one number pretending to be exact.",
  },
];

const AUDIENCE = [
  {
    icon: HandshakeIcon,
    title: "Companies quoting a project",
    body: "Price a quote from the document in minutes, with your own rates.",
  },
  {
    icon: RocketIcon,
    title: "People planning to build",
    body: "Know what an app should cost before asking for quotes.",
  },
  {
    icon: BankIcon,
    title: "Departments budgeting",
    body: "A realistic budget with security, support and hosting included.",
  },
];

const delay = (rd: number) => ({ "--rd": rd }) as React.CSSProperties;

export default function AboutPage() {
  return (
    <>
      <PageIntro
        title="Aakalan means estimation. We built it because software prices stopped adding up."
        art={<MeaningFigure />}
      >
        AI now does much of the typing. Nobody agrees what that does to the
        price, so quotes drift further apart.
      </PageIntro>

      {/* The question and our answer */}
      <Section className="grid items-center gap-10 py-12 sm:py-16 lg:grid-cols-2">
        <div className="flex flex-col gap-6">
          <h2
            data-reveal
            className="font-wide text-3xl leading-tight font-semibold"
          >
            How do you price software when AI writes much of the code, but
            people still design, check and look after it?
          </h2>
          <p data-reveal className="text-lg text-muted-foreground">
            Price the work itself, and show the working:
          </p>
          <ul className="flex flex-wrap gap-2">
            {ANSWER.map((a, i) => (
              <li
                key={a}
                data-reveal
                style={delay(i)}
                className="rounded-full bg-tape-soft px-3.5 py-1.5 text-sm font-medium text-tape"
              >
                {a}
              </li>
            ))}
          </ul>
        </div>
        <div
          data-reveal
          style={delay(1)}
          className="rounded-[26px] border bg-card p-6 sm:p-8"
        >
          <p className="mb-6 font-semibold">Where one number comes from</p>
          <TraceFigure />
        </div>
      </Section>

      {/* How we test the prices */}
      <Section className="pb-12 sm:pb-16">
        <h2 data-reveal className="font-wide text-3xl font-semibold">
          How we test the prices
        </h2>
        <p data-reveal className="mt-3 max-w-2xl text-muted-foreground">
          We compare with real Indian projects that have published prices. Our
          prices are not tuned to them: they come from hours and rates.
        </p>
        <div className="mt-8 grid gap-4 md:grid-cols-3">
          {TESTS.map((t, i) => (
            <div
              key={t.size}
              data-reveal
              style={delay(i)}
              className="flex flex-col gap-4 rounded-[22px] border bg-card p-6"
            >
              <span className="flex items-center justify-between">
                <span className="font-semibold">{t.size}</span>
                <IconTile
                  icon={t.icon}
                  size="sm"
                  tone={t.icon === ArrowUpIcon ? "warm" : "tape"}
                />
              </span>
              <p className="text-muted-foreground">{t.text}</p>
            </div>
          ))}
        </div>
        <p
          data-reveal
          className="mt-4 flex items-center gap-3 rounded-2xl bg-warning-muted px-4 py-3 text-sm"
        >
          <HourglassMediumIcon
            size={20}
            weight="duotone"
            className="shrink-0 text-warning"
          />
          Not checked yet: what finished projects really cost. Recorded outcomes
          will do that, so treat every estimate as a guide.
        </p>
      </Section>

      {/* What we hold to */}
      <section className="border-y bg-card">
        <Section className="py-12 sm:py-16">
          <h2 data-reveal className="font-wide text-3xl font-semibold">
            What we hold to
          </h2>
          <dl className="mt-10 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
            {PRINCIPLES.map((p, i) => (
              <div
                key={p.title}
                data-reveal
                style={delay(i)}
                className="flex flex-col gap-3"
              >
                <IconTile icon={p.icon} size="lg" />
                <dt className="text-lg font-semibold">{p.title}</dt>
                <dd className="-mt-1 text-muted-foreground">{p.body}</dd>
              </div>
            ))}
          </dl>
        </Section>
      </section>

      {/* Who it is for */}
      <Section className="py-12 sm:py-16">
        <h2 data-reveal className="font-wide text-3xl font-semibold">
          Who it is for
        </h2>
        <ul className="mt-8 flex flex-col divide-y rounded-[22px] border bg-card">
          {AUDIENCE.map((a, i) => (
            <li
              key={a.title}
              data-reveal
              style={delay(i)}
              className="flex items-center gap-5 p-5 sm:p-6"
            >
              <IconTile
                icon={a.icon}
                tone={i === 1 ? "ai" : i === 2 ? "warm" : "tape"}
                size="lg"
              />
              <span className="flex flex-col gap-1">
                <span className="text-lg font-semibold">{a.title}</span>
                <span className="text-muted-foreground">{a.body}</span>
              </span>
            </li>
          ))}
        </ul>
      </Section>

      <StartBand />
    </>
  );
}
