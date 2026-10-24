"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, errorText, type ContactIn } from "@/lib/api/client";
import { cn } from "@/lib/utils";

const TOPICS: { value: ContactIn["topic"]; label: string }[] = [
  { value: "demo", label: "A walk-through" },
  { value: "question", label: "A question" },
  { value: "partnership", label: "Working together" },
  { value: "other", label: "Something else" },
];

const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const MIN_MESSAGE = 5; // characters, as the API requires

export function ContactForm() {
  const [form, setForm] = React.useState<ContactIn>({
    name: "",
    email: "",
    organisation: "",
    topic: "question",
    message: "",
  });
  const [state, setState] = React.useState<
    | { kind: "idle" }
    | { kind: "sending" }
    | { kind: "sent" }
    | { kind: "error"; message: string }
  >({ kind: "idle" });
  const [touched, setTouched] = React.useState(false);

  const problems = {
    name: form.name.trim() === "" ? "Enter your name." : null,
    email: EMAIL.test(form.email.trim())
      ? null
      : "Enter an email address we can reply to.",
    message:
      form.message.trim().length < MIN_MESSAGE
        ? "Write a few words about what you need."
        : null,
  };
  const valid = !problems.name && !problems.email && !problems.message;

  function set<K extends keyof ContactIn>(key: K, value: ContactIn[K]) {
    setForm((now) => ({ ...now, [key]: value }));
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setTouched(true);
    if (!valid) return;
    setState({ kind: "sending" });
    try {
      await api.sendContact({
        ...form,
        name: form.name.trim(),
        email: form.email.trim(),
      });
      setState({ kind: "sent" });
    } catch (e) {
      setState({ kind: "error", message: errorText(e) });
    }
  }

  if (state.kind === "sent") {
    return (
      <div
        className="flex flex-col gap-3 rounded-[22px] border bg-card p-8"
        role="status"
      >
        <div
          aria-hidden="true"
          className="tape-ticks h-3 w-32 rounded-sm bg-tape"
        />
        <h2 className="font-wide text-2xl font-semibold">Message sent.</h2>
        <p className="text-muted-foreground">
          We will reply to {form.email.trim()}. You can start an estimate in the
          meantime.
        </p>
      </div>
    );
  }

  const error = (text: string | null) =>
    touched && text ? (
      <span className="text-sm text-destructive">{text}</span>
    ) : null;

  return (
    <form
      onSubmit={submit}
      noValidate
      className="flex flex-col gap-5 rounded-[22px] border bg-card p-6 shadow-[0_24px_60px_-34px_rgb(27_36_51/0.18)] sm:p-8"
    >
      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 text-sm font-semibold">
          What is it about?
        </legend>
        <div role="radiogroup" className="flex flex-wrap gap-2">
          {TOPICS.map((t) => {
            const active = form.topic === t.value;
            return (
              <button
                key={t.value}
                type="button"
                role="radio"
                aria-checked={active}
                onClick={() => set("topic", t.value)}
                className={cn(
                  "rounded-full border px-4 py-2 text-sm font-medium transition-colors",
                  active
                    ? "border-tape/60 bg-tape-soft text-foreground"
                    : "hover:bg-muted",
                )}
              >
                {t.label}
              </button>
            );
          })}
        </div>
      </fieldset>
      <div className="grid gap-5 sm:grid-cols-2">
        <div className="flex flex-col gap-2">
          <Label htmlFor="c-name">Your name</Label>
          <Input
            id="c-name"
            autoComplete="name"
            value={form.name}
            onChange={(e) => set("name", e.target.value)}
            aria-invalid={touched && problems.name ? true : undefined}
            className="h-11"
          />
          {error(problems.name)}
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="c-email">Email</Label>
          <Input
            id="c-email"
            type="email"
            autoComplete="email"
            value={form.email}
            onChange={(e) => set("email", e.target.value)}
            aria-invalid={touched && problems.email ? true : undefined}
            className="h-11"
          />
          {error(problems.email)}
        </div>
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="c-org">Company or department (optional)</Label>
        <Input
          id="c-org"
          autoComplete="organization"
          value={form.organisation}
          onChange={(e) => set("organisation", e.target.value)}
          className="h-11"
        />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="c-message">Message</Label>
        <textarea
          id="c-message"
          rows={5}
          maxLength={4000}
          value={form.message}
          onChange={(e) => set("message", e.target.value)}
          aria-invalid={touched && problems.message ? true : undefined}
          placeholder="e.g. We are quoting a portal with an AI chatbot and want to check our price."
          className="w-full rounded-xl border border-input bg-background px-3 py-2 text-base"
        />
        {error(problems.message)}
      </div>
      {state.kind === "error" ? (
        <p role="alert" className="text-sm text-destructive">
          {state.message}
        </p>
      ) : null}
      <Button
        type="submit"
        size="lg"
        className="w-fit"
        disabled={state.kind === "sending"}
      >
        {state.kind === "sending" ? "Sending…" : "Send message"}
      </Button>
    </form>
  );
}
