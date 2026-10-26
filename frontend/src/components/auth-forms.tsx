"use client";

import * as React from "react";
import { CheckCircleIcon } from "@phosphor-icons/react/dist/ssr";

import { LogoMark } from "@/components/site/logo";
import {
  CodeFigure,
  FlowFigure,
  SavedEstimatesFigure,
} from "@/components/site/page-art";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, api, type TokenResponse } from "@/lib/api/client";
import { cn } from "@/lib/utils";

/** What the left side of a sign-in screen says (large screens only). */
export type Scene = "login" | "signup" | "forgot" | "verify";

const SCENES: Record<Scene, { title: string; text: string }> = {
  login: {
    title: "Pick up where you left off.",
    text: "Your estimates and saved templates are all here.",
  },
  signup: {
    title: "Price your next project in minutes.",
    text: "Describe it or upload the requirement document, and get a low, likely and high cost.",
  },
  forgot: {
    title: "Locked out? It happens.",
    text: "We email a 6-digit code. Use it to set a new password and you are back in.",
  },
  verify: {
    title: "One quick check.",
    text: "A code in your inbox confirms the address, so only you can open your estimates.",
  },
};

const PROMISES = [
  "AI reads the document. Fixed formulas work out every number.",
  "Every figure traces back to a clause and a rate.",
  "The same answers give the same price, every time.",
];

/** The picture for each screen: saved estimates, the way to a price, or the emailed code. */
const ART: Record<Scene, () => React.ReactNode> = {
  login: () => <SavedEstimatesFigure />,
  signup: () => <FlowFigure />,
  forgot: () => <CodeFigure />,
  verify: () => <CodeFigure />,
};

/**
 * The screen for sign in, sign up, reset and confirm: a sheet in two halves, the screen's
 * picture and what Aakalan promises on the left (large screens), the form on the right.
 */
export function AuthScreen({
  scene,
  eyebrow,
  title,
  description,
  children,
  footer,
}: {
  scene: Scene;
  eyebrow: string;
  title: string;
  description: React.ReactNode;
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
  const side = SCENES[scene];
  return (
    <div className="panel grid w-full max-w-5xl overflow-hidden rounded-[28px] lg:grid-cols-2">
      <aside className="relative hidden flex-col justify-between gap-10 overflow-hidden border-r bg-panel-2 p-10 lg:flex">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(70%_55%_at_0%_0%,rgb(11_120_184/0.14),transparent_70%)]"
        />
        <div className="relative flex flex-col gap-4">
          <LogoMark className="size-11" />
          <h2 className="font-display text-4xl leading-[1.05]">{side.title}</h2>
          <p className="max-w-sm text-muted-foreground">{side.text}</p>
        </div>
        <div className="relative flex flex-col gap-8">
          {ART[scene]()}
          <ul className="flex flex-col gap-2.5 text-sm text-muted-foreground">
            {PROMISES.map((line) => (
              <li key={line} className="flex gap-2.5">
                <CheckCircleIcon
                  size={18}
                  weight="fill"
                  aria-hidden="true"
                  className="shrink-0 text-ai"
                />
                {line}
              </li>
            ))}
          </ul>
        </div>
      </aside>
      <div className="flex flex-col">
        <div className="flex flex-1 flex-col justify-center p-6 sm:p-10">
          <div className="mx-auto flex w-full max-w-sm flex-col gap-7">
            <div className="settle flex flex-col gap-2">
              <p className="eyebrow">{eyebrow}</p>
              <h1 className="font-display text-3xl">{title}</h1>
              <p className="text-muted-foreground">{description}</p>
            </div>
            <div
              className="settle flex flex-col gap-5"
              style={{ "--d": 1 } as React.CSSProperties}
            >
              {children}
            </div>
            {footer ? (
              <div className="flex flex-col gap-1 border-t pt-5 text-sm text-muted-foreground">
                {footer}
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}

export function TextField({
  id,
  label,
  type = "text",
  autoComplete,
  value,
  onChange,
  hint,
  met,
}: {
  id: string;
  label: string;
  type?: string;
  autoComplete?: string;
  value: string;
  onChange: (value: string) => void;
  hint?: string;
  /** The hint's rule is met (shown in green). */
  met?: boolean;
}) {
  const [shown, setShown] = React.useState(false);
  const secret = type === "password";
  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor={id}>{label}</Label>
      <div className="relative">
        <Input
          id={id}
          type={secret && shown ? "text" : type}
          autoComplete={autoComplete}
          required
          value={value}
          onChange={(e) => onChange(e.target.value)}
          aria-describedby={hint ? `${id}-hint` : undefined}
          className={cn("h-11 rounded-lg px-3.5 text-base", secret && "pr-16")}
        />
        {secret ? (
          <button
            type="button"
            onClick={() => setShown((now) => !now)}
            aria-label={shown ? "Hide password" : "Show password"}
            className="absolute inset-y-0 right-0 rounded-r-lg px-3.5 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
          >
            {shown ? "Hide" : "Show"}
          </button>
        ) : null}
      </div>
      {hint ? (
        <span
          id={`${id}-hint`}
          className={cn(
            "text-xs transition-colors",
            met ? "text-success" : "text-muted-foreground",
          )}
        >
          {hint}
        </span>
      ) : null}
    </div>
  );
}

export function FormError({ message }: { message: string | null }) {
  return message ? (
    <p
      role="alert"
      className="rounded-lg border border-destructive/25 bg-destructive/5 px-3.5 py-2.5 text-sm text-destructive"
    >
      {message}
    </p>
  ) : null;
}

/** A readable message for a failed call. */
export function failure(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  return "Could not reach the server. Is the backend running?";
}

const CODE_LENGTH = 6;

/** The 6-digit code emailed to `email`, with a "send a new code" link (`resend`). */
export function CodeField({
  email,
  code,
  onCode,
  resend,
}: {
  email: string;
  code: string;
  onCode: (code: string) => void;
  resend: () => Promise<unknown>;
}) {
  const [note, setNote] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [focused, setFocused] = React.useState(false);

  async function again() {
    setBusy(true);
    setNote(null);
    try {
      await resend();
      setNote(`We sent a new code to ${email}.`);
    } catch (err) {
      setNote(failure(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor="code">6-digit code</Label>
      {/* one real input (paste and autofill work) over six boxes that show its digits */}
      <div className="relative">
        <div aria-hidden="true" className="flex gap-2">
          {Array.from({ length: CODE_LENGTH }, (_, i) => (
            <span
              key={i}
              className={cn(
                "flex h-14 flex-1 items-center justify-center rounded-lg border border-input bg-card text-2xl font-semibold tabular-nums transition-colors",
                focused &&
                  i === Math.min(code.length, CODE_LENGTH - 1) &&
                  "border-primary ring-2 ring-ring",
              )}
            >
              {code[i] ?? ""}
            </span>
          ))}
        </div>
        <input
          id="code"
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={CODE_LENGTH}
          required
          value={code}
          onChange={(e) => onCode(e.target.value.replace(/\D/g, ""))}
          onFocus={(e) => {
            setFocused(true);
            const end = e.currentTarget.value.length;
            e.currentTarget.setSelectionRange(end, end);
          }}
          onBlur={() => setFocused(false)}
          className="absolute inset-0 size-full cursor-text bg-transparent text-transparent caret-transparent opacity-0 outline-none"
        />
      </div>
      <span className="text-xs text-muted-foreground">
        Sent to {email}. Not there? Check spam, or{" "}
        <button
          type="button"
          onClick={again}
          disabled={busy}
          className="rounded font-medium text-primary hover:underline disabled:opacity-60"
        >
          send a new code
        </button>
        .
      </span>
      {note ? (
        <span role="status" className="text-xs text-muted-foreground">
          {note}
        </span>
      ) : null}
    </div>
  );
}

/** Confirm the email address with its code; signs in on success. */
export function VerifyEmailStep({
  email,
  onSignedIn,
  onBack,
}: {
  email: string;
  onSignedIn: (response: TokenResponse) => void;
  onBack?: () => void;
}) {
  const [code, setCode] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      onSignedIn(await api.verifyEmail(email, code));
    } catch (err) {
      setError(failure(err));
      setBusy(false);
    }
  }

  return (
    <AuthScreen
      scene="verify"
      eyebrow="One more step"
      title="Check your email"
      description="Enter the code we emailed you to confirm your address."
      footer={
        onBack ? (
          <button
            type="button"
            onClick={onBack}
            className="w-fit rounded font-medium text-primary hover:underline"
          >
            Use a different email
          </button>
        ) : undefined
      }
    >
      <form onSubmit={submit} className="flex flex-col gap-5" noValidate>
        <CodeField
          email={email}
          code={code}
          onCode={setCode}
          resend={() => api.resendCode(email)}
        />
        <FormError message={error} />
        <Button
          type="submit"
          size="lg"
          disabled={busy || code.length !== CODE_LENGTH}
        >
          {busy ? "Checking…" : "Confirm and sign in"}
        </Button>
      </form>
    </AuthScreen>
  );
}
