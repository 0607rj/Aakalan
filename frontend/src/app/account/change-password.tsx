"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  BuildingsIcon,
  EnvelopeSimpleIcon,
  LockKeyIcon,
  SignOutIcon,
  UserCircleIcon,
} from "@phosphor-icons/react/dist/ssr";

import { FormError, TextField, failure } from "@/components/auth-forms";
import { useCurrentUser } from "@/components/auth-guard";
import { IconTile } from "@/components/site/illustrations";
import { Button } from "@/components/ui/button";
import { api, clearToken, setToken, type CurrentUser } from "@/lib/api/client";

const MIN_PASSWORD = 8;

const ROLES: Record<CurrentUser["role"], { label: string; can: string }> = {
  admin: {
    label: "Admin",
    can: "Makes estimates, sees the margin and changes company settings.",
  },
  finance: {
    label: "Finance",
    can: "Sees the margin and changes company settings.",
  },
  estimator: {
    label: "Estimator",
    can: "Makes estimates. The margin and company settings are hidden.",
  },
  viewer: { label: "Viewer", can: "Looks at the company's estimates." },
};

/** Up to two letters from the name (else the email). */
function initials(user: CurrentUser): string {
  const words = user.full_name.trim().split(/\s+/).filter(Boolean);
  const letters = words.length
    ? words.length > 1
      ? words[0][0] + words[words.length - 1][0]
      : words[0][0]
    : user.email[0];
  return letters.toUpperCase();
}

/** Who is signed in, on the ember card: initials, name, email, company and role. */
export function AccountSummary() {
  const user = useCurrentUser();
  return (
    <div className="flex flex-wrap items-center gap-5">
      <span
        aria-hidden="true"
        className="flex size-16 shrink-0 items-center justify-center rounded-full bg-night font-head text-xl font-semibold text-peach"
      >
        {initials(user)}
      </span>
      <div className="flex min-w-0 flex-1 flex-col gap-1.5">
        <p className="eyebrow">Your account</p>
        <h1 className="font-display">{user.full_name || "Your account"}</h1>
        <p className="flex flex-wrap items-center gap-x-5 gap-y-1 text-muted-foreground">
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
      <span className="rounded-full bg-tape-soft px-4 py-1.5 text-sm font-semibold text-tape">
        {ROLES[user.role].label}
      </span>
    </div>
  );
}

/** The signed-in person's details and what their role allows, with Log out. */
export function AccountDetails() {
  const user = useCurrentUser();
  const router = useRouter();
  const role = ROLES[user.role];
  const rows = [
    { label: "Name", value: user.full_name || "Not given" },
    { label: "Email", value: user.email },
    { label: "Company", value: user.org_name },
  ];

  function logout() {
    clearToken();
    router.replace("/login");
  }

  return (
    <section className="slab flex flex-col gap-6 p-6 sm:p-8">
      <div className="flex items-center gap-3">
        <IconTile icon={UserCircleIcon} />
        <h2 className="text-xl font-semibold">Your details</h2>
      </div>
      <dl className="flex flex-col">
        {rows.map((r) => (
          <div
            key={r.label}
            className="flex flex-col gap-0.5 border-b py-3 first:pt-0"
          >
            <dt className="text-sm text-muted-foreground">{r.label}</dt>
            <dd className="truncate font-medium">{r.value}</dd>
          </div>
        ))}
        <div className="flex flex-col gap-1 py-3">
          <dt className="text-sm text-muted-foreground">Role</dt>
          <dd className="flex flex-col gap-1">
            <span className="w-fit rounded-full bg-tape-soft px-3 py-0.5 text-sm font-semibold text-tape">
              {role.label}
            </span>
            <span className="text-sm text-muted-foreground">{role.can}</span>
          </dd>
        </div>
      </dl>
      <Button
        type="button"
        variant="outline"
        onClick={logout}
        className="mt-auto w-full sm:w-fit"
      >
        <SignOutIcon size={16} aria-hidden="true" />
        Log out
      </Button>
    </section>
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
    <section className="slab flex w-full flex-col gap-6 p-6 sm:p-8">
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
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
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
        </div>
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
