import type { Metadata } from "next";

import { PageIntro, Section } from "@/components/site/sections";

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
    body: "Each published price we add makes estimates for projects like it more accurate.",
  },
];

export default function ContactPage() {
  return (
    <>
      <PageIntro title="Talk to us about a project, a price or a partnership.">
        Write to us with the form below. A person reads every message and
        replies by email.
      </PageIntro>
      <Section className="grid gap-12 py-12 sm:py-16 lg:grid-cols-[1.2fr_0.8fr]">
        <ContactForm />
        <aside className="flex flex-col gap-8">
          <h2 data-reveal className="font-wide text-2xl font-semibold">
            What we can help with
          </h2>
          <dl className="flex flex-col gap-6">
            {HELPS.map((h) => (
              <div key={h.title} className="border-l-4 border-tape pl-4">
                <dt className="font-bold">{h.title}</dt>
                <dd className="mt-1 text-muted-foreground">{h.body}</dd>
              </div>
            ))}
          </dl>
          <p className="text-sm text-muted-foreground">
            Please do not send a confidential requirement document through this
            form. Upload it inside your account instead, where only your
            organisation can see it.
          </p>
        </aside>
      </Section>
    </>
  );
}
