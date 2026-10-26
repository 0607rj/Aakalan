"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import {
  AuthScreen,
  CodeField,
  FormError,
  TextField,
  failure,
} from "@/components/auth-forms";
import { Button } from "@/components/ui/button";
import { api, setToken } from "@/lib/api/client";

const MIN_PASSWORD = 8;

/** Email a reset code, then the code and a new password; signs in on success. */
export function ForgotForm() {
  const router = useRouter();
  const [email, setEmail] = React.useState("");
  const [sentTo, setSentTo] = React.useState<string | null>(null);
  const [code, setCode] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  async function sendCode(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setSentTo((await api.forgotPassword(email)).email);
    } catch (err) {
      setError(failure(err));
    } finally {
      setBusy(false);
    }
  }

  async function reset(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!sentTo) return;
    setBusy(true);
    setError(null);
    try {
      const r = await api.resetPassword(sentTo, code, password);
      setToken(r.access_token);
      router.replace("/projects");
    } catch (err) {
      setError(failure(err));
      setBusy(false);
    }
  }

  const footer = (
    <Link
      href="/login"
      className="w-fit rounded font-medium text-primary hover:underline"
    >
      Back to sign in
    </Link>
  );

  if (!sentTo) {
    return (
      <AuthScreen
        scene="forgot"
        eyebrow="Reset password · Step 1 of 2"
        title="Forgot your password?"
        description="Enter your email and we'll send you a code to set a new one."
        footer={footer}
      >
        <form onSubmit={sendCode} className="flex flex-col gap-5" noValidate>
          <TextField
            id="email"
            label="Email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={setEmail}
          />
          <FormError message={error} />
          <Button
            type="submit"
            size="lg"
            disabled={busy || email.trim() === ""}
          >
            {busy ? "Sending…" : "Send code"}
          </Button>
        </form>
      </AuthScreen>
    );
  }

  return (
    <AuthScreen
      scene="forgot"
      eyebrow="Reset password · Step 2 of 2"
      title="Set a new password"
      description="If an account uses this email, we sent it a 6-digit code."
      footer={footer}
    >
      <form onSubmit={reset} className="flex flex-col gap-5" noValidate>
        <CodeField
          email={sentTo}
          code={code}
          onCode={setCode}
          resend={() => api.forgotPassword(sentTo)}
        />
        <TextField
          id="new-password"
          label="New password"
          type="password"
          autoComplete="new-password"
          value={password}
          onChange={setPassword}
          hint={`At least ${MIN_PASSWORD} characters. You'll be signed out everywhere else.`}
          met={password.length >= MIN_PASSWORD}
        />
        <FormError message={error} />
        <Button
          type="submit"
          size="lg"
          disabled={busy || code.length !== 6 || password.length < MIN_PASSWORD}
        >
          {busy ? "Saving…" : "Save and sign in"}
        </Button>
      </form>
    </AuthScreen>
  );
}
