import type { Metadata } from "next";

import { RangeTape } from "@/components/site/mockups";
import { PageIntro, Section, StartBand } from "@/components/site/sections";

export const metadata: Metadata = {
  title: "About · Aakalan",
};

const PRINCIPLES = [
  {
    title: "Price what is built, not who asks",
    body: "A login screen costs the same for everyone. Bigger or stricter work costs more because there is more of it, and it shows up as its own line.",
  },
  {
    title: "AI reads, formulas count",
    body: "AI helps read documents and descriptions and suggests features. It never sets, edits or rounds a price; a fixed set of formulas does, the same way every time.",
  },
  {
    title: "Every number has a source",
    body: "Each line links to the feature that asked for it, the rate and where that rate came from, and the formula used. Nothing is a black box.",
  },
  {
    title: "Honest about how sure we are",
    body: "We publish how the prices did against real projects and show a range, not a single number pretending to be exact.",
  },
];

export default function AboutPage() {
  return (
    <>
      <PageIntro title="Aakalan means estimation. We built it because software prices stopped adding up.">
        For years software was priced by the hour. AI tools now do much of the
        typing, and nobody agrees what that should do to the price. Vendors
        guess, buyers guess, and the gap between bids grows.
      </PageIntro>

      <Section className="grid gap-12 py-16 sm:py-24 lg:grid-cols-[1fr_1fr]">
        <div className="flex flex-col gap-5 text-lg">
          <h2 className="font-wide text-3xl leading-tight font-extrabold">
            The question we set out to answer
          </h2>
          <p className="text-muted-foreground">
            How do you work out the cost of building software when AI writes
            much of the code, but people still design it, check it, test it,
            launch it and look after it for years?
          </p>
          <p className="text-muted-foreground">
            Our answer is to price the work itself: each feature at the size it
            needs to be, each kind of task with the saving AI tools really
            bring, plus the review that saving demands, plus everything after
            launch. Then to show the working.
          </p>
        </div>
        <div className="flex flex-col gap-4 rounded-[22px] border bg-card p-6">
          <h3 className="text-lg font-bold">How we test the prices</h3>
          <p className="text-muted-foreground">
            We collected 56 Indian projects with published prices: government
            contracts and private and startup projects. Each was priced with
            settings tuned only on the others.
          </p>
          <ul className="flex flex-col gap-2">
            <li>
              <strong>Small projects:</strong> typically within about 21% of the
              price paid
            </li>
            <li>
              <strong>All sizes together:</strong> typically within about 43%
            </li>
            <li>
              <strong>Large projects:</strong> vary most, so their range is
              widest
            </li>
          </ul>
          <RangeTape
            low={1_400_000}
            likely={1_900_000}
            high={2_600_000}
            scaleMax={3_000_000}
          />
          <p className="text-sm text-muted-foreground">
            That is why every estimate is a range. Treat it as a guide before
            work starts, and use your own judgement.
          </p>
        </div>
      </Section>

      <div className="border-y bg-card">
        <Section className="py-16 sm:py-20">
          <h2 className="font-wide text-3xl font-extrabold">What we hold to</h2>
          <dl className="mt-10 grid gap-x-12 gap-y-10 md:grid-cols-2">
            {PRINCIPLES.map((p) => (
              <div key={p.title} className="flex flex-col gap-2">
                <dt className="flex items-center gap-3 text-lg font-bold">
                  <span
                    aria-hidden="true"
                    className="h-6 w-1.5 rounded-full bg-tape"
                  />
                  {p.title}
                </dt>
                <dd className="text-muted-foreground">{p.body}</dd>
              </div>
            ))}
          </dl>
        </Section>
      </div>

      <Section className="py-16 sm:py-20">
        <h2 className="font-wide text-3xl font-extrabold">Who it is for</h2>
        <div className="mt-8 grid gap-8 md:grid-cols-3">
          <div>
            <h3 className="font-bold">Companies quoting a project</h3>
            <p className="mt-2 text-muted-foreground">
              Price a bid from the requirement document in minutes, with your
              own rates and margin, and see what the document leaves unclear.
            </p>
          </div>
          <div>
            <h3 className="font-bold">People planning to build</h3>
            <p className="mt-2 text-muted-foreground">
              Founders, shops, schools and clinics: know what an app should cost
              before asking for quotes, and which features drive it.
            </p>
          </div>
          <div>
            <h3 className="font-bold">Departments budgeting</h3>
            <p className="mt-2 text-muted-foreground">
              Set a realistic budget for a portal or system, with security,
              support and hosting included for the years you need.
            </p>
          </div>
        </div>
      </Section>

      <StartBand />
    </>
  );
}
