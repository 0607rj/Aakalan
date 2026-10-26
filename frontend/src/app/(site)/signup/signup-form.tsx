"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import {
  AuthScreen,
  FormError,
  TextField,
  VerifyEmailStep,
  failure,
} from "@/components/auth-forms";
import { Button } from "@/components/ui/button";
import { api, setToken } from "@/lib/api/client";

const MIN_PASSWORD = 8;

/** A new account (name, email, password); then the emailed code confirms the address and signs in. */
export function SignupForm() {
  const router = useRouter();
  const [fullName, setFullName] = React.useState("");
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [submitting, setSubmitting] = React.useState(false);
  const [sentTo, setSentTo] = React.useState<string | null>(null);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const sent = await api.signup({
        full_name: fullName,
        email,
        password,
      });
      setSentTo(sent.email);
    } catch (err) {
      setError(failure(err));
    } finally {
      setSubmitting(false);
    }
  }

  if (sentTo) {
    return (
      <VerifyEmailStep
        email={sentTo}
        onSignedIn={(r) => {
          setToken(r.access_token);
          router.replace("/projects");
        }}
        onBack={() => setSentTo(null)}
      />
    );
  }

  const ready =
    fullName.trim() !== "" &&
    email.trim() !== "" &&
    password.length >= MIN_PASSWORD;
  return (
    <AuthScreen
      scene="signup"
      eyebrow="Step 1 of 2"
      title="Create an account"
      description="We'll email you a code to confirm your address."
      footer={
        <span>
          Already have an account?{" "}
          <Link
            href="/login"
            className="rounded font-medium text-primary hover:underline"
          >
            Sign in
          </Link>
        </span>
      }
    >
      <form onSubmit={onSubmit} className="flex flex-col gap-5" noValidate>
        <TextField
          id="full-name"
          label="Your name"
          autoComplete="name"
          value={fullName}
          onChange={setFullName}
        />
        <TextField
          id="email"
          label="Email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={setEmail}
        />
        <TextField
          id="password"
          label="Password"
          type="password"
          autoComplete="new-password"
          value={password}
          onChange={setPassword}
          hint={`At least ${MIN_PASSWORD} characters.`}
          met={password.length >= MIN_PASSWORD}
        />
        <FormError message={error} />
        <Button
          type="submit"
          size="lg"
          disabled={submitting || !ready}
          className="w-full"
        >
          {submitting ? "Creating your account…" : "Create account"}
        </Button>
      </form>
    </AuthScreen>
  );
}
