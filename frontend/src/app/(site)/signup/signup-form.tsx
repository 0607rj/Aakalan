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
import { api, setToken } from "@/lib/api/client";

const MIN_PASSWORD = 8;

/** A new account and company; then the emailed code confirms the address and signs in. */
export function SignupForm() {
  const router = useRouter();
  const [fullName, setFullName] = React.useState("");
  const [company, setCompany] = React.useState("");
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
        company,
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
    company.trim() !== "" &&
    email.trim() !== "" &&
    password.length >= MIN_PASSWORD;
  return (
    <AuthCard
      title="Create an account"
      description="Your own space for your company's estimates. We'll email you a code to confirm your address."
      footer={
        <span>
          Already have an account?{" "}
          <Link
            href="/login"
            className="font-medium text-primary hover:underline"
          >
            Sign in
          </Link>
        </span>
      }
    >
      <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
        <TextField
          id="full-name"
          label="Your name"
          autoComplete="name"
          value={fullName}
          onChange={setFullName}
        />
        <TextField
          id="company"
          label="Company"
          autoComplete="organization"
          value={company}
          onChange={setCompany}
        />
        <TextField
          id="email"
          label="Work email"
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
        />
        <FormError message={error} />
        <Button
          type="submit"
          disabled={submitting || !ready}
          className="w-full"
        >
          {submitting ? "Creating your account…" : "Create account"}
        </Button>
      </form>
    </AuthCard>
  );
}
