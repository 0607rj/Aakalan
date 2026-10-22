"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, api, type TokenResponse } from "@/lib/api/client";

/** The card every sign-in screen sits in. */
export function AuthCard({
  title,
  description,
  children,
  footer,
}: {
  title: string;
  description: React.ReactNode;
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
  return (
    <Card className="w-full max-w-sm rounded-[22px] shadow-[0_24px_60px_-28px_rgb(23_32_58/0.35)]">
      <CardHeader>
        <CardTitle className="text-2xl">{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {children}
        {footer ? (
          <div className="flex flex-col gap-1 border-t pt-4 text-sm text-muted-foreground">
            {footer}
          </div>
        ) : null}
      </CardContent>
    </Card>
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
}: {
  id: string;
  label: string;
  type?: string;
  autoComplete?: string;
  value: string;
  onChange: (value: string) => void;
  hint?: string;
}) {
  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        type={type}
        autoComplete={autoComplete}
        required
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      {hint ? (
        <span className="text-xs text-muted-foreground">{hint}</span>
      ) : null}
    </div>
  );
}

export function FormError({ message }: { message: string | null }) {
  return message ? (
    <p role="alert" className="text-sm text-destructive">
      {message}
    </p>
  ) : null;
}

/** A readable message for a failed call. */
export function failure(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  return "Could not reach the server. Is the backend running?";
}

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
      <Input
        id="code"
        inputMode="numeric"
        autoComplete="one-time-code"
        maxLength={6}
        required
        value={code}
        onChange={(e) => onCode(e.target.value.replace(/\D/g, ""))}
        className="text-center text-lg tracking-[0.5em] tabular-nums"
      />
      <span className="text-xs text-muted-foreground">
        Sent to {email}. Not there? Check spam, or{" "}
        <button
          type="button"
          onClick={again}
          disabled={busy}
          className="font-medium text-primary hover:underline disabled:opacity-60"
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
    <AuthCard
      title="Check your email"
      description="Enter the code we emailed you to confirm your address."
      footer={
        onBack ? (
          <button
            type="button"
            onClick={onBack}
            className="w-fit font-medium text-primary hover:underline"
          >
            Use a different email
          </button>
        ) : undefined
      }
    >
      <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
        <CodeField
          email={email}
          code={code}
          onCode={setCode}
          resend={() => api.resendCode(email)}
        />
        <FormError message={error} />
        <Button type="submit" disabled={busy || code.length !== 6}>
          {busy ? "Checking…" : "Confirm and sign in"}
        </Button>
      </form>
    </AuthCard>
  );
}
