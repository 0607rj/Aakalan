"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import {
  AuthCard,
  FormError,
  TextField,
  VerifyEmailStep,
  failure,
} from "@/components/auth-forms";
import { Button } from "@/components/ui/button";
import { ApiError, api, setToken, type TokenResponse } from "@/lib/api/client";

export function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [submitting, setSubmitting] = React.useState(false);
  const [verifying, setVerifying] = React.useState(false);

  function signedIn(response: TokenResponse) {
    setToken(response.access_token);
    router.replace("/projects");
  }

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      signedIn(await api.login({ email, password }));
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("Incorrect email or password.");
      } else if (err instanceof ApiError && err.status === 403) {
        // the password is right but the address is not confirmed yet: send a code
        await api.resendCode(email).catch(() => undefined);
        setVerifying(true);
      } else {
        setError(failure(err));
      }
      setSubmitting(false);
    }
  }

  if (verifying) {
    return (
      <VerifyEmailStep
        email={email}
        onSignedIn={signedIn}
        onBack={() => setVerifying(false)}
      />
    );
  }

  return (
    <AuthCard
      title="Sign in"
      description="See your estimates and start new ones."
      footer={
        <>
          <span>
            New here?{" "}
            <Link
              href="/signup"
              className="font-medium text-primary hover:underline"
            >
              Create an account
            </Link>
          </span>
        </>
      }
    >
      <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
        <TextField
          id="email"
          label="Email"
          type="email"
          autoComplete="username"
          value={email}
          onChange={setEmail}
        />
        <div className="flex flex-col gap-1">
          <TextField
            id="password"
            label="Password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={setPassword}
          />
          <Link
            href="/forgot-password"
            className="w-fit self-end text-sm text-primary hover:underline"
          >
            Forgot password?
          </Link>
        </div>
        <FormError message={error} />
        <Button
          type="submit"
          disabled={submitting || !email || !password}
          className="w-full"
        >
          {submitting ? "Signing in…" : "Sign in"}
        </Button>
      </form>
    </AuthCard>
  );
}
