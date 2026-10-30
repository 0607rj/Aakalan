import type { Metadata } from "next";
import { ArrowDownIcon, ArrowUpIcon } from "@phosphor-icons/react/dist/ssr";

import {
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
        scene="word"
        center
        className="pb-[24rem] sm:justify-start sm:pt-40 sm:pb-[20rem]"
        sceneClassName="-bottom-[94px] sm:top-auto sm:-bottom-[min(205px,17.5vw)] sm:translate-y-0"
      >
        AI now does much of the typing. Nobody agrees what that does to the
        price, so quotes drift further apart.
      </PageIntro>

      {/* The question and our answer */}
      <Section className="pb-[clamp(72px,10vw,120px)]">
        <div className="flex flex-col gap-6">
          <Kicker n="01">The question</Kicker>
          <h2
            data-reveal
            className="font-display max-w-5xl text-[clamp(2.4rem,5.6vw,4.5rem)] leading-[1.02]"
          >
            How do you price software when AI writes much of the code?{" "}
            <span className="text-faint">
              People still design, check and look after it.
            </span>
          </h2>
          <p data-reveal className="mt-4 text-lg text-muted-foreground">
            Price the work itself, and show the working:
          </p>
          <ol className="grid gap-x-10 sm:grid-cols-2 lg:grid-cols-4">
            {ANSWER.map((a, i) => (
              <li
                key={a}
                data-reveal
                style={delay(i)}
                className="flex flex-col gap-4 border-t-2 border-foreground pt-5 pb-8"
              >
                <span className="font-mono text-sm text-tape">0{i + 1}</span>
                <span className="font-wide text-[clamp(1.4rem,2.2vw,1.75rem)] leading-[1.15]">
                  {a}
                </span>
              </li>
            ))}
          </ol>
        </div>
      </Section>

      {/* How we test the prices: a ruled table */}
      <Section className="pb-[clamp(72px,10vw,120px)]">
        <Kicker n="02">How we test the prices</Kicker>
        <Title claim="Checked against real Indian projects." className="mt-5">
          Not tuned to them: our prices come from hours and rates.
        </Title>
        <dl data-reveal className="soft-card mt-12 flex flex-col px-6 sm:px-8">
          {TESTS.map((t) => {
            const Icon = t.up ? ArrowUpIcon : ArrowDownIcon;
            return (
              <div
                key={t.size}
                className="grid gap-2 border-b py-5 last:border-b-0 sm:grid-cols-[14rem_1fr] sm:gap-8"
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

      {/* What we hold to: the heading stays while the rules go past */}
      <Section className="grid grid-cols-1 gap-10 pb-[clamp(72px,10vw,120px)] lg:grid-cols-[0.8fr_1.2fr] lg:gap-16">
        <div className="flex h-fit flex-col gap-5 lg:sticky lg:top-28">
          <Kicker n="03">What we hold to</Kicker>
          <Title claim="Four rules.">Every estimate follows them.</Title>
        </div>
        <dl className="flex flex-col">
          {PRINCIPLES.map((p, i) => (
            <div
              key={p.title}
              data-reveal
              style={delay(i)}
              className="grid grid-cols-[2.5rem_1fr] gap-x-4 gap-y-2 border-t py-8 last:border-b"
            >
              <span className="row-span-2 pt-2 font-mono text-sm text-tape">
                0{i + 1}
              </span>
              <dt className="font-wide text-[clamp(1.5rem,2.6vw,2rem)] leading-[1.1]">
                {p.title}
              </dt>
              <dd className="text-lg text-muted-foreground">{p.body}</dd>
            </div>
          ))}
        </dl>
      </Section>

      {/* Who it is for: all on one dark card */}
      <Section className="pb-2">
        <div
          data-reveal
          className="dark-card glow-low grid grid-cols-1 gap-10 p-[clamp(28px,4vw,44px)] lg:grid-cols-[0.8fr_1.2fr] lg:gap-16"
        >
          <div className="flex flex-col gap-5">
            <Kicker n="04" tone="dark">
              Who it is for
            </Kicker>
            <h2 className="font-wide text-[clamp(2rem,4vw,2.9rem)] leading-[1.08]">
              Anyone who needs the number{" "}
              <span className="text-white/50">before the work starts.</span>
            </h2>
          </div>
          <ul className="flex flex-col">
            {AUDIENCE.map((a) => (
              <li
                key={a.title}
                className="flex flex-col gap-1 border-b border-white/10 py-5 first:pt-0 last:border-b-0 last:pb-0"
              >
                <span className="font-wide text-xl">{a.title}</span>
                <span className="text-white/70">{a.body}</span>
              </li>
            ))}
          </ul>
        </div>
      </Section>

      <StartBand />
    </>
  );
}
