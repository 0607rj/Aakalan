import type { Metadata } from "next";

import { ChatFigure } from "@/components/site/page-art";
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
        art={<ChatFigure />}
      >
        Write to us with the form below. A person reads every message and
        replies by email.
      </PageIntro>
      <Section className="grid grid-cols-1 gap-12 py-16 sm:py-20 lg:grid-cols-[1.2fr_0.8fr] lg:gap-16">
        <ContactForm />
        <aside className="flex flex-col gap-6">
          <Kicker>What we can help with</Kicker>
          <dl className="flex flex-col border-t">
            {HELPS.map((h, i) => (
              <div key={h.title} className="flex gap-4 border-b py-5">
                <span className="font-mono text-xs leading-6 text-muted-foreground">
                  0{i + 1}
                </span>
                <span className="flex flex-col gap-1">
                  <dt className="font-semibold">{h.title}</dt>
                  <dd className="text-muted-foreground">{h.body}</dd>
                </span>
              </div>
            ))}
          </dl>
          <p className="font-mono text-xs leading-relaxed text-muted-foreground">
            Please do not send a confidential requirement document through this
            form. Upload it inside your account instead, where only your
            organisation can see it.
          </p>
        </aside>
      </Section>
    </>
  );
}
