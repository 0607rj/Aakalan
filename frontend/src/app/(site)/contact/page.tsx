import type { Metadata } from "next";

import { Kicker, PageIntro, Section } from "@/components/site/sections";

import { ContactForm } from "./contact-form";

export const metadata: Metadata = {
  title: "Contact · Aakalan",
};

const HELPS = [
  {
    title: "Ask for a walk-through",
    body: "We price one of your real projects with you and explain every line.",
  },
  {
    title: "Ask about a number",
    body: "Send the estimate's name and the line you want explained.",
  },
  {
    title: "Share a real project price",
    body: "Each published price makes estimates for projects like it more accurate.",
  },
];

export default function ContactPage() {
  return (
    <>
      <PageIntro
        title="Talk to us."
        rest="About a project, a price or a partnership."
        scene="talk"
        sceneClassName="sm:top-[calc(50svh+83px)] sm:left-[calc(50%-24px)]"
      >
        Write to us with the form below. A person reads every message and
        replies by email.
      </PageIntro>
      <Section className="grid grid-cols-1 items-start gap-6 pb-[clamp(72px,10vw,120px)] lg:grid-cols-[1.2fr_0.8fr]">
        <div data-reveal className="soft-card p-7 sm:p-10">
          <ContactForm />
        </div>
        <aside
          data-reveal
          className="dark-card glow-low flex flex-col gap-6 p-7 sm:p-10"
        >
          <Kicker tone="dark">What we can help with</Kicker>
          <dl className="flex flex-col">
            {HELPS.map((h, i) => (
              <div
                key={h.title}
                className="flex gap-4 border-b border-white/10 py-5 last:border-b-0"
              >
                <span className="font-mono text-xs leading-6 text-peach">
                  0{i + 1}
                </span>
                <span className="flex flex-col gap-1">
                  <dt className="font-semibold">{h.title}</dt>
                  <dd className="text-white/70">{h.body}</dd>
                </span>
              </div>
            ))}
          </dl>
          <p className="font-mono text-xs leading-relaxed text-white/55">
            Please do not send a confidential requirement document through this
            form. Upload it inside your account instead, where only your
            organisation can see it.
          </p>
        </aside>
      </Section>
    </>
  );
}
