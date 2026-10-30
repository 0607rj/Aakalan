import type { Metadata } from "next";
import Link from "next/link";

import { AiCompare } from "@/components/site/ai-compare";
import { CountUp } from "@/components/site/count-up";
import { TenderLine } from "@/components/site/home-bands";
import { EmberHero } from "@/components/site/ember-hero";
import { FeatureTiles } from "@/components/site/feature-tiles";
import {
  Faq,
  Kicker,
  Section,
  StartBand,
  Title,
} from "@/components/site/sections";

export const metadata: Metadata = {
  title: "Aakalan · What should this software cost?",
};

const FACTS = [
  { value: "1 line", label: "per feature, each with its own price" },
  { value: "10", label: "plain questions, one per screen" },
  { value: "0", label: "prices made up by AI: formulas do the sums" },
  { value: "PDF + Excel", label: "report and bill of quantities to share" },
];

/** The old way and Aakalan's, topic by topic. */
const COMPARE = [
  {
    topic: "The work",
    then: "Hours of typing, line by line",
    now: "Each feature at the level you need",
  },
  {
    topic: "AI tools",
    then: "Left out, or a guessed discount",
    now: "Saving per task, with the checking added back",
  },
  {
    topic: "The total",
    then: "Building only",
    now: "Build, launch, servers, support and tax",
  },
  {
    topic: "The numbers",
    then: "Ask whoever made the sheet",
    now: "Each one traced to its rate and source",
  },
];

/** The example result in the phone and on the first card (illustration only). */
const EXAMPLE = [
  { name: "Bookings", level: "Standard", ai: "₹2.6 L", old: "₹3.3 L" },
  { name: "Online payment", level: "Basic", ai: "₹1.1 L", old: "₹1.4 L" },
  { name: "Mobile app", level: "Basic", ai: "₹3.0 L", old: "₹3.9 L" },
  { name: "SMS reminders", level: "Basic", ai: "₹0.9 L", old: "₹1.1 L" },
];

const TRACE = [
  { mark: "§", what: "Clause 4.2", note: "p. 7" },
  { mark: "BK", what: "Bookings", note: "standard" },
  { mark: "₹/h", what: "₹1,150", note: "an hour" },
  { mark: "₹", what: "₹2.6 L", note: "cost line" },
];

const TEAM = [
  { count: "×2", role: "Developers" },
  { count: "×1", role: "Checks AI code" },
  { count: "×1", role: "Tester" },
  { count: "×1", role: "Designer" },
];

const AUDIENCE = [
  "#SystemIntegrators",
  "#ITVendors",
  "#GovernmentTenders",
  "#Startups",
];

const FAQ = [
  {
    q: "Does AI make up the price?",
    a: "No. AI only reads your document and suggests features. Every number comes from fixed formulas, hours and dated rates, so the same answers always give the same price.",
  },
  {
    q: "What does the total include?",
    a: "Building it, launching it, the servers, the years of support you choose, and tax, as a low, likely and high cost. What the document asks for but the price leaves out is listed on its own.",
  },
  {
    q: "What if I don't know an answer?",
    a: "Choose “Not sure”. The usual answer is used and the range widens, instead of the estimate pretending to know.",
  },
  {
    q: "Can I use my own rates?",
    a: "Yes. Your company's day rates and margin are used for its estimates. An estimate keeps the rates it was made with, so it never changes later.",
  },
  {
    q: "Who sees my requirement document?",
    a: "Only your company. The text goes only to the AI service set up for reading it, and is treated as data, never as instructions.",
  },
  {
    q: "How exact is it?",
    a: "It is a guide before work starts, not a quote. Nobody knows the exact number yet, so you get a range with the reasons for its width.",
  },
];

const delay = (rd: number) => ({ "--rd": rd }) as React.CSSProperties;

/** A section's space below it; the one above comes from the section before. */
const BLOCK = "pt-6 pb-[clamp(72px,10vw,120px)]";
const CARD = "p-[clamp(28px,4vw,44px)]";

/** The example's feature lines, in the phone and in the first card's window. */
function CostLines() {
  return EXAMPLE.map((f) => (
    <div
      key={f.name}
      className="grid grid-cols-[1fr_auto] gap-2.5 border-b py-2.5 text-[14px] leading-[1.55]"
    >
      <span>
        {f.name}
        <small className="block text-[12px] text-muted-foreground">
          {f.level}
        </small>
      </span>
      <span className="text-right font-mono font-medium tabular-nums">
        {f.ai}
        <s className="block text-[11.5px] font-normal text-faint">{f.old}</s>
      </span>
    </div>
  ));
}

/** A card's small line above its heading: "03 · Per feature". */
function CardLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="font-mono text-xs tracking-[0.06em] uppercase opacity-55">
      {children}
    </p>
  );
}

const CARD_TITLE =
  "font-wide mt-3.5 text-[clamp(1.7rem,3vw,2.3rem)] leading-[1.08]";
const CARD_BODY = "mt-3.5 max-w-[30rem] text-[1.05rem]";

export default function HomePage() {
  return (
    <>
      {/* The first screen: the claim on the ember panel, the range of costs behind it */}
      <EmberHero scene="cost" full>
        <div className="relative page-wrap pt-[clamp(132px,17vh,180px)] pb-[clamp(190px,24vh,240px)] text-center">
          <p className="rise-in glass-pill mx-auto inline-flex items-center gap-2 rounded-full py-[7px] pr-4 pl-2 text-sm font-medium">
            <span className="rounded-full bg-night px-[9px] py-[5px] font-mono text-[11px] leading-none tracking-[0.06em] uppercase">
              New
            </span>
            Software cost, feature by feature
          </p>
          <h1
            className="rise-in font-display mt-[26px] text-[clamp(3.1rem,9vw,6.8rem)] leading-none"
            style={delay(1)}
          >
            Price what gets <span className="text-peach">built.</span>
          </h1>
          <p
            className="rise-in mx-auto mt-[26px] max-w-[34rem] text-[clamp(1.1rem,1.8vw,1.3rem)] leading-[1.55] text-white/72"
            style={delay(2)}
          >
            Every feature gets its own price.{" "}
            <span className="text-white">
              Worked out the way teams build today, with AI tools.
            </span>
          </p>
          <div
            className="rise-in mt-9 flex flex-wrap items-center justify-center gap-3"
            style={delay(3)}
          >
            <Link
              href="/estimate/new"
              className="inline-flex h-[52px] items-center rounded-full bg-white px-[26px] font-medium text-foreground transition-transform hover:-translate-y-px"
            >
              Start an estimate
            </Link>
            <Link
              href="/how-it-works"
              className="glass-pill inline-flex h-[52px] items-center gap-2 rounded-full px-[26px] font-medium text-white transition-transform hover:-translate-y-px"
            >
              See how it works <span aria-hidden="true">→</span>
            </Link>
          </div>
          <p
            className="rise-in mt-[22px] text-sm text-white/72"
            style={delay(4)}
          >
            Don&apos;t know an answer? Press{" "}
            <span className="glass-pill inline-flex rounded-md border-b-2 px-2 py-px font-mono text-xs text-white">
              Not sure
            </span>{" "}
            and the range widens.
          </p>
        </div>
      </EmberHero>

      {/* What gets priced: the result in a phone, with features sliding past behind it */}
      <section
        id="features"
        className="relative z-[4] pb-[clamp(72px,10vw,120px)]"
      >
        <Section className="flex flex-col items-center text-center">
          <Kicker n="02">What gets priced</Kicker>
          <Title
            claim="You say what the software should do."
            center
            className="mt-5"
          />
          <p
            data-reveal
            className="mt-[18px] max-w-[40rem] text-[clamp(1.05rem,1.6vw,1.2rem)] text-muted-foreground"
          >
            Aakalan splits it into features, prices each one from hours and
            dated rates, and shows the working.
          </p>
          <p data-reveal className="mt-6 flex flex-wrap justify-center gap-2.5">
            {AUDIENCE.map((a) => (
              <span
                key={a}
                className="rounded-xl bg-muted px-4 py-2 text-[15px] font-medium text-foreground/80"
              >
                {a}
              </span>
            ))}
          </p>
        </Section>
        <FeatureTiles>
          <div className="rounded-[34px] bg-night p-2.5 shadow-[0_40px_80px_-30px_rgb(0_0_0/0.45)]">
            <div className="overflow-hidden rounded-[26px] bg-card">
              <div className="bg-[#1b1a18] px-5 pt-[22px] pb-5 text-white">
                <p className="font-mono text-[11px] text-white/50">
                  result · example
                </p>
                <p className="font-wide mt-2.5 text-[2.4rem] leading-none tracking-[-0.03em]">
                  ₹7.6 L
                  <span className="ml-1.5 font-sans text-sm font-normal tracking-normal text-white/72">
                    for 4 features
                  </span>
                </p>
                <svg
                  viewBox="0 0 320 70"
                  preserveAspectRatio="none"
                  aria-hidden="true"
                  className="mt-3.5 block h-[70px] w-full"
                >
                  <defs>
                    <linearGradient id="spark-fill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0" stopColor="#ff4c00" stopOpacity=".55" />
                      <stop offset="1" stopColor="#ff4c00" stopOpacity="0" />
                    </linearGradient>
                  </defs>
                  <path
                    d="M0 68 C40 68 60 60 85 40 S125 6 140 6 S185 24 210 42 S280 64 320 66 L320 70 L0 70 Z"
                    fill="url(#spark-fill)"
                  />
                  <path
                    d="M0 68 C40 68 60 60 85 40 S125 6 140 6 S185 24 210 42 S280 64 320 66"
                    fill="none"
                    stroke="#ff4c00"
                    strokeWidth="2"
                  />
                  <circle
                    cx="140"
                    cy="6"
                    r="4.5"
                    fill="#fff"
                    stroke="#111"
                    strokeWidth="2"
                  />
                </svg>
              </div>
              <div className="px-[18px] pt-3.5 pb-5 text-left">
                <CostLines />
              </div>
            </div>
          </div>
        </FeatureTiles>
      </section>

      {/* One large number, then the four facts on a card */}
      <Section className="flex flex-col items-center pt-10 pb-[clamp(72px,10vw,120px)] text-center">
        <Kicker>Real numbers, worked out</Kicker>
        <Title
          claim="Every estimate is a range, not a guess"
          center
          className="mt-5"
        />
        <p
          data-reveal
          className="font-wide relative mt-[18px] inline-block text-[clamp(5rem,17vw,12rem)] leading-[0.95] tracking-[-0.04em] text-tape-bright tabular-nums"
        >
          <CountUp to={30000} />
          <span className="absolute right-0 -bottom-[28%] rotate-[7deg] rounded-full bg-card px-[18px] py-2.5 font-sans text-[13px] leading-[1.2] font-medium tracking-normal whitespace-nowrap text-foreground shadow-[0_12px_30px_-12px_rgb(0_0_0/0.35)] sm:-right-[8%] sm:-bottom-[6%] sm:text-[15px]">
            possible costs for every estimate
          </span>
        </p>
        <dl
          data-reveal
          className="soft-card mt-14 grid w-full grid-cols-2 text-left min-[900px]:grid-cols-4"
        >
          {FACTS.map((f, i) => (
            <div
              key={f.label}
              style={delay(i)}
              className="border-b px-6 py-[26px] odd:border-r min-[900px]:border-r min-[900px]:border-b-0 min-[900px]:last:border-r-0"
            >
              <dt className="font-wide text-[clamp(1.7rem,3vw,2.2rem)] leading-[1.1] tracking-[-0.03em]">
                {f.value}
              </dt>
              <dd className="mt-1.5 text-sm text-muted-foreground">
                {f.label}
              </dd>
            </div>
          ))}
        </dl>
      </Section>

      {/* The problem, as a plain comparison on one card */}
      <Section className={BLOCK}>
        <Kicker n="01">Why prices stopped adding up</Kicker>
        <Title
          claim="Hourly rates were made for people typing every line."
          className="mt-5 max-w-[22ch]"
        >
          AI drafts much of it now. Someone still checks it.
        </Title>
        <div data-reveal className="soft-card mt-12 px-7 py-2">
          <div className="hidden gap-6 border-b py-4 font-mono text-xs tracking-[0.06em] text-muted-foreground uppercase sm:grid sm:grid-cols-[1fr_2fr_2fr]">
            <span />
            <span>A spreadsheet estimate</span>
            <span className="text-tape">Aakalan</span>
          </div>
          {COMPARE.map((row) => (
            <div
              key={row.topic}
              className="grid grid-cols-1 gap-1.5 border-b py-5 last:border-b-0 sm:grid-cols-[1fr_2fr_2fr] sm:gap-6"
            >
              <span className="font-semibold">{row.topic}</span>
              <span className="flex gap-2.5 text-muted-foreground">
                <span aria-hidden="true" className="text-faint">
                  –
                </span>
                <span>
                  <span className="sr-only">A spreadsheet estimate: </span>
                  {row.then}
                </span>
              </span>
              <span className="flex gap-2.5 font-medium">
                <span aria-hidden="true" className="font-bold text-tape-bright">
                  ✓
                </span>
                <span>
                  <span className="sr-only">Aakalan: </span>
                  {row.now}
                </span>
              </span>
            </div>
          ))}
        </div>
      </Section>

      {/* The main point: the same software, priced the old way and with AI tools */}
      <Section className={BLOCK}>
        <AiCompare />
      </Section>

      {/* What Aakalan does, on one line of a tender, edge to edge */}
      <TenderLine />

      {/* What the result shows: a warm and a white card */}
      <Section className={BLOCK}>
        <div className="grid gap-6 min-[900px]:grid-cols-2">
          <article
            data-reveal
            className={`dark-card warm grid items-center gap-8 min-[900px]:col-span-2 min-[900px]:grid-cols-2 ${CARD}`}
          >
            <div>
              <CardLabel>03 · Traceable</CardLabel>
              <h3 className={CARD_TITLE}>Every number has an address.</h3>
              <p className={`${CARD_BODY} text-white/72`}>
                Each cost line keeps the clause it came from, the feature, the
                dated rate and the formula. Nothing is a black box.
              </p>
            </div>
            <div className="rounded-[20px] border border-white/12 bg-black/42 p-[22px]">
              <h4 className="font-wide mb-[18px] text-center text-[1.05rem]">
                Where ₹2.6 L comes from
              </h4>
              <ol className="flex items-start justify-between gap-1">
                {TRACE.map((t, i) => (
                  <li
                    key={t.what}
                    className="flex min-w-0 flex-1 flex-col items-center gap-2 text-center text-[12.5px]"
                  >
                    <span
                      className={`grid size-12 place-items-center rounded-full font-mono text-[13px] font-medium ${i === TRACE.length - 1 ? "bg-tape-bright" : "bg-white/10"}`}
                    >
                      {t.mark}
                    </span>
                    {t.what}
                    <small className="font-mono text-[11px] text-white/50">
                      {t.note}
                    </small>
                  </li>
                ))}
              </ol>
            </div>
          </article>

          <article
            data-reveal
            className={`soft-card grid items-center gap-6 rounded-[28px] min-[900px]:col-span-2 min-[900px]:grid-cols-2 ${CARD}`}
          >
            <div>
              <p className="font-mono text-xs tracking-[0.06em] text-muted-foreground uppercase">
                04 · People and time
              </p>
              <h3 className={CARD_TITLE}>The team and the time it takes.</h3>
              <p className={`${CARD_BODY} text-muted-foreground`}>
                Developers, the people who check AI-written code, testers and
                designers, by role, with the months to build.
              </p>
            </div>
            <div>
              <ul className="flex flex-wrap gap-[22px]">
                {TEAM.map((t) => (
                  <li
                    key={t.role}
                    className="flex flex-col items-center gap-2 text-[13px] text-muted-foreground"
                  >
                    <span className="grid size-14 place-items-center rounded-full bg-tape-soft font-mono text-sm font-medium text-tape">
                      {t.count}
                    </span>
                    {t.role}
                  </li>
                ))}
              </ul>
              <p className="mt-6 inline-flex rounded-full bg-foreground px-4 py-2.5 text-sm font-medium text-white">
                3 months to build
              </p>
            </div>
          </article>
        </div>
      </Section>

      {/* Questions people ask first */}
      <Section className={BLOCK}>
        <Faq
          title="Questions people ask first."
          rest="Straight answers."
          items={FAQ}
        />
      </Section>

      <StartBand
        title="Put the spreadsheet down."
        rest="Let Aakalan do the sums."
      />
    </>
  );
}
