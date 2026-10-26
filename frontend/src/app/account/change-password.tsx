"use client";

import * as React from "react";
import {
  BuildingsIcon,
  EnvelopeSimpleIcon,
  LockKeyIcon,
  UserCircleIcon,
} from "@phosphor-icons/react/dist/ssr";

import { FormError, TextField, failure } from "@/components/auth-forms";
import { useCurrentUser } from "@/components/auth-guard";
import { IconTile } from "@/components/site/illustrations";
import { Button } from "@/components/ui/button";
import { api, setToken } from "@/lib/api/client";

const MIN_PASSWORD = 8;

/** Who is signed in: name, email and company. */
export function AccountSummary() {
  const user = useCurrentUser();
  return (
    <div className="flex items-center gap-5">
      <IconTile icon={UserCircleIcon} size="lg" />
      <div className="flex flex-col gap-1">
        <p className="eyebrow">Account</p>
        <h1 className="font-display text-3xl sm:text-4xl">
          {user.full_name || "Your account"}
        </h1>
        <p className="flex flex-wrap items-center gap-x-4 gap-y-1 text-muted-foreground">
          <span className="inline-flex items-center gap-1.5">
            <EnvelopeSimpleIcon size={16} aria-hidden="true" />
            {user.email}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <BuildingsIcon size={16} aria-hidden="true" />
            {user.org_name}
          </span>
        </p>
      </div>
    </div>
  );
}

/** A new password while signed in; other sessions are signed out, this one stays. */
export function ChangePassword() {
  const [current, setCurrent] = React.useState("");
  const [next, setNext] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [done, setDone] = React.useState(false);
  const [busy, setBusy] = React.useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setDone(false);
    try {
      setToken((await api.changePassword(current, next)).access_token);
      setCurrent("");
      setNext("");
      setDone(true);
    } catch (err) {
      setError(failure(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="slab flex w-full max-w-xl flex-col gap-6 p-6 sm:p-8">
      <div className="flex items-center gap-3">
        <IconTile icon={LockKeyIcon} />
        <div className="flex flex-col gap-0.5">
          <h2 className="text-xl font-semibold">Change password</h2>
          <p className="text-sm text-muted-foreground">
            Other devices are signed out. This one stays signed in.
          </p>
        </div>
      </div>
      <form onSubmit={submit} className="flex flex-col gap-5" noValidate>
        <TextField
          id="current-password"
          label="Current password"
          type="password"
          autoComplete="current-password"
          value={current}
          onChange={setCurrent}
        />
        <TextField
          id="new-password"
          label="New password"
          type="password"
          autoComplete="new-password"
          value={next}
          onChange={setNext}
          hint={`At least ${MIN_PASSWORD} characters.`}
          met={next.length >= MIN_PASSWORD}
        />
        <FormError message={error} />
        {done ? (
          <p
            role="status"
            className="rounded-lg border border-success/25 bg-success/5 px-3.5 py-2.5 text-sm text-success"
          >
            Password changed.
          </p>
        ) : null}
        <Button
          type="submit"
          size="lg"
          className="w-full sm:w-fit"
          disabled={busy || !current || next.length < MIN_PASSWORD}
        >
          {busy ? "Saving…" : "Change password"}
        </Button>
      </form>
    </section>
  );
}
