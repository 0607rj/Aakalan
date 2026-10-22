"use client";

import * as React from "react";

import {
  AuthCard,
  FormError,
  TextField,
  failure,
} from "@/components/auth-forms";
import { useCurrentUser } from "@/components/auth-guard";
import { Button } from "@/components/ui/button";
import { api, setToken } from "@/lib/api/client";

const MIN_PASSWORD = 8;

/** A new password while signed in; other sessions are signed out, this one stays. */
export function ChangePassword() {
  const user = useCurrentUser();
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
    <AuthCard
      title="Change password"
      description={`${user.full_name || user.email} · ${user.org_name}`}
    >
      <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
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
          hint={`At least ${MIN_PASSWORD} characters. Other devices will be signed out.`}
        />
        <FormError message={error} />
        {done ? (
          <p role="status" className="text-sm text-muted-foreground">
            Password changed.
          </p>
        ) : null}
        <Button
          type="submit"
          disabled={busy || !current || next.length < MIN_PASSWORD}
        >
          {busy ? "Saving…" : "Change password"}
        </Button>
      </form>
    </AuthCard>
  );
}
