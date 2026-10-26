"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  BuildingsIcon,
  CalculatorIcon,
  CaretDownIcon,
  EnvelopeSimpleIcon,
  EyeIcon,
  ProhibitIcon,
  SealCheckIcon,
  ShieldStarIcon,
  TrashIcon,
  UsersThreeIcon,
} from "@phosphor-icons/react/dist/ssr";

import { useCurrentUser } from "@/components/auth-guard";
import {
  IconTile,
  type IconType,
  type Tone,
} from "@/components/site/illustrations";
import { ErrorNotice, Loading } from "@/components/status";
import { Input } from "@/components/ui/input";
import {
  api,
  errorText,
  startViewing,
  type OwnerUserChange,
  type OwnerUserRow,
  type QuickSummary,
  type Role,
} from "@/lib/api/client";
import { formatApprox, formatDate } from "@/lib/format";
import { useLoad } from "@/lib/use-load";
import { cn } from "@/lib/utils";

const ROLES: { value: Role; label: string }[] = [
  { value: "admin", label: "Admin" },
  { value: "estimator", label: "Estimator" },
  { value: "finance", label: "Finance" },
  { value: "viewer", label: "Viewer" },
];

type Filter = "all" | "disabled" | "unverified";

const FILTERS: { value: Filter; label: string }[] = [
  { value: "all", label: "Everyone" },
  { value: "disabled", label: "Disabled" },
  { value: "unverified", label: "Not verified" },
];

/** Look at an account read only: swap to its token, then open the page; the app's other
 * sections check who is signed in when they open, so they see the account being viewed. */
function useViewAs() {
  const router = useRouter();
  return React.useCallback(
    async (userId: string, path = "/projects") => {
      const { access_token } = await api.ownerViewAs(userId);
      startViewing(access_token);
      router.push(path);
    },
    [router],
  );
}

function Stat({
  icon,
  tone,
  label,
  value,
  note,
}: {
  icon: IconType;
  tone?: Tone;
  label: string;
  value: number;
  note?: string;
}) {
  return (
    <div className="slab flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:gap-4 sm:p-5">
      <IconTile icon={icon} tone={tone} />
      <span className="flex flex-col">
        <span className="text-2xl font-semibold tabular-nums">{value}</span>
        <span className="text-sm text-muted-foreground">{label}</span>
        {note ? (
          <span className="text-xs text-muted-foreground">{note}</span>
        ) : null}
      </span>
    </div>
  );
}

function Overview() {
  const loader = React.useCallback(() => api.ownerOverview(), []);
  const { state } = useLoad(loader);
  if (state.kind === "error") return <ErrorNotice message={state.message} />;
  if (state.kind !== "ready") return null;
  const o = state.data;
  return (
    <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
      <Stat icon={BuildingsIcon} label="Companies" value={o.companies} />
      <Stat
        icon={UsersThreeIcon}
        label="People"
        value={o.users}
        note={`${o.active_users} active`}
      />
      <Stat
        icon={CalculatorIcon}
        tone="ai"
        label="Estimates"
        value={o.estimates}
        note={`${o.estimates_recent} in the last ${o.recent_days} days`}
      />
      <Stat
        icon={EnvelopeSimpleIcon}
        tone="warning"
        label="Email not verified"
        value={o.unverified_users}
      />
    </div>
  );
}

function initials(row: OwnerUserRow): string {
  const words = row.full_name.trim().split(/\s+/).filter(Boolean);
  const letters = words.length
    ? words.length > 1
      ? words[0][0] + words[words.length - 1][0]
      : words[0][0]
    : row.email[0];
  return letters.toUpperCase();
}

function Tag({
  tone,
  children,
}: {
  tone: "tape" | "warm" | "warning" | "muted";
  children: React.ReactNode;
}) {
  return (
    <span
      className={cn(
        "rounded-full px-2 py-0.5 text-xs font-semibold",
        tone === "tape" && "bg-tape-soft text-tape",
        tone === "warm" && "bg-warm/12 text-warm",
        tone === "warning" && "bg-warning-muted text-warning",
        tone === "muted" && "bg-foreground/[0.06] text-muted-foreground",
      )}
    >
      {children}
    </span>
  );
}

/** The user's company estimates, opened read only as them. */
function TheirEstimates({ row }: { row: OwnerUserRow }) {
  const viewAs = useViewAs();
  const loader = React.useCallback(
    () => api.ownerUserEstimates(row.id),
    [row.id],
  );
  const { state } = useLoad(loader);
  const [error, setError] = React.useState<string | null>(null);
  if (state.kind === "loading") return <Loading />;
  if (state.kind === "error") return <ErrorNotice message={state.message} />;
  if (state.data.length === 0)
    return (
      <p className="py-2 text-sm text-muted-foreground">No estimates yet.</p>
    );
  const open = (s: QuickSummary) => {
    viewAs(row.id, `/estimate/${s.estimate_id}`).catch((e: unknown) =>
      setError(errorText(e)),
    );
  };
  return (
    <div className="flex flex-col gap-2">
      <ErrorNotice message={error} />
      <ul className="flex flex-col divide-y rounded-xl border bg-panel-2">
        {state.data.map((s) => (
          <li
            key={s.estimate_id}
            className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3"
          >
            <span className="flex min-w-0 flex-1 flex-col">
              <span className="truncate font-medium">{s.name}</span>
              <span className="text-xs text-muted-foreground">
                {formatDate(s.created_at)}
              </span>
            </span>
            <span className="text-sm font-semibold text-primary tabular-nums">
              {s.feasible
                ? formatApprox(s.likely_paise, s.currency).replace("about ", "")
                : "No price"}
            </span>
            {row.is_active && !row.is_owner ? (
              <button
                type="button"
                onClick={() => open(s)}
                disabled={!row.is_active}
                className="text-sm font-semibold text-primary hover:underline"
              >
                Open
              </button>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}

const ACTION =
  "inline-flex h-9 items-center gap-1.5 rounded-lg border bg-card px-3 text-sm font-medium transition-colors hover:bg-panel-2 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none disabled:opacity-50";

function UserCard({
  row,
  onChanged,
  onDeleted,
}: {
  row: OwnerUserRow;
  onChanged: (row: OwnerUserRow) => void;
  onDeleted: () => void;
}) {
  const viewAs = useViewAs();
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [showEstimates, setShowEstimates] = React.useState(false);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }

  const change = (body: OwnerUserChange) =>
    run(async () => onChanged(await api.ownerChangeUser(row.id, body)));

  function remove() {
    const alone = row.org_members === 1;
    const what = alone
      ? `This also deletes the company "${row.org_name}" with its ${row.projects} project(s), estimates and uploaded documents.`
      : `The company "${row.org_name}" and its estimates stay for its other ${row.org_members - 1} member(s).`;
    if (!window.confirm(`Delete ${row.email}? ${what} This cannot be undone.`))
      return;
    void run(async () => {
      await api.ownerDeleteUser(row.id);
      onDeleted();
    });
  }

  const locked = row.is_owner;
  return (
    <li
      className={cn(
        "flex flex-col gap-4 rounded-xl border bg-card p-4 shadow-[0_1px_2px_rgb(27_36_51/0.04)] sm:p-5",
        !row.is_active && "border-dashed bg-transparent",
      )}
    >
      <div className="flex flex-wrap items-start gap-4">
        <span
          aria-hidden="true"
          className={cn(
            "flex size-11 shrink-0 items-center justify-center rounded-full text-sm font-semibold",
            row.is_active
              ? "bg-tape-soft text-tape"
              : "bg-foreground/[0.06] text-muted-foreground",
          )}
        >
          {initials(row)}
        </span>
        <span className="flex min-w-0 flex-1 flex-col gap-1">
          <span className="flex flex-wrap items-center gap-2">
            <span className="font-semibold">{row.full_name || row.email}</span>
            {row.is_owner ? <Tag tone="tape">Site owner</Tag> : null}
            {!row.is_active ? <Tag tone="muted">Disabled</Tag> : null}
            {!row.email_verified ? (
              <Tag tone="warning">Email not verified</Tag>
            ) : null}
          </span>
          <span className="truncate text-sm text-muted-foreground">
            {row.email}
          </span>
          <span className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
            <span className="inline-flex items-center gap-1.5">
              <BuildingsIcon size={15} aria-hidden="true" />
              {row.org_name}
              {row.org_members > 1 ? ` · ${row.org_members} people` : ""}
            </span>
            <span className="tabular-nums">
              {row.estimates} estimate{row.estimates === 1 ? "" : "s"}
              {row.last_estimate_at
                ? `, last on ${formatDate(row.last_estimate_at)}`
                : ""}
            </span>
            <span>Joined {formatDate(row.created_at)}</span>
          </span>
        </span>
        <label className="flex flex-col gap-1 text-xs text-muted-foreground">
          Role
          <select
            value={row.role}
            disabled={busy || locked}
            onChange={(e) => void change({ role: e.target.value as Role })}
            className="h-9 rounded-lg border bg-card px-2 text-sm text-foreground disabled:opacity-60"
          >
            {ROLES.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className={ACTION}
          aria-expanded={showEstimates}
          onClick={() => setShowEstimates((v) => !v)}
        >
          <CaretDownIcon
            size={14}
            weight="bold"
            aria-hidden="true"
            className={cn(
              "transition-transform",
              showEstimates && "rotate-180",
            )}
          />
          Estimates
        </button>
        {!locked ? (
          <>
            <button
              type="button"
              className={ACTION}
              disabled={busy || !row.is_active}
              title={row.is_active ? undefined : "Enable the account first"}
              onClick={() => void run(() => viewAs(row.id))}
            >
              <EyeIcon size={16} aria-hidden="true" />
              View as them
            </button>
            {!row.email_verified ? (
              <button
                type="button"
                className={ACTION}
                disabled={busy}
                onClick={() => void change({ email_verified: true })}
              >
                <SealCheckIcon size={16} aria-hidden="true" />
                Mark email verified
              </button>
            ) : null}
            <button
              type="button"
              className={ACTION}
              disabled={busy}
              onClick={() => void change({ is_active: !row.is_active })}
            >
              <ProhibitIcon size={16} aria-hidden="true" />
              {row.is_active ? "Disable" : "Enable"}
            </button>
            <button
              type="button"
              className={cn(ACTION, "text-destructive hover:bg-destructive/10")}
              disabled={busy}
              onClick={remove}
            >
              <TrashIcon size={16} aria-hidden="true" />
              Delete
            </button>
          </>
        ) : null}
      </div>

      <ErrorNotice message={error} />
      {showEstimates ? <TheirEstimates row={row} /> : null}
    </li>
  );
}

function People() {
  const loader = React.useCallback(() => api.ownerUsers(), []);
  const { state, reload, setData } = useLoad(loader);
  const [query, setQuery] = React.useState("");
  const [filter, setFilter] = React.useState<Filter>("all");

  if (state.kind === "loading") return <Loading />;
  if (state.kind === "error") return <ErrorNotice message={state.message} />;
  const rows = state.data;

  const q = query.trim().toLowerCase();
  const shown = rows.filter(
    (r) =>
      (filter === "all" ||
        (filter === "disabled" && !r.is_active) ||
        (filter === "unverified" && !r.email_verified)) &&
      (!q ||
        r.email.toLowerCase().includes(q) ||
        r.full_name.toLowerCase().includes(q) ||
        r.org_name.toLowerCase().includes(q)),
  );

  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold">People</h2>
          <p className="text-sm text-muted-foreground">
            {rows.length} account{rows.length === 1 ? "" : "s"}, newest first.
          </p>
        </div>
        <div className="flex w-full flex-wrap gap-2 sm:w-auto">
          <div
            className="flex rounded-lg border bg-card p-0.5"
            role="group"
            aria-label="Show"
          >
            {FILTERS.map((f) => (
              <button
                key={f.value}
                type="button"
                aria-pressed={filter === f.value}
                onClick={() => setFilter(f.value)}
                className={cn(
                  "rounded-md px-3 py-1.5 text-sm transition-colors",
                  filter === f.value
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {f.label}
              </button>
            ))}
          </div>
          <Input
            type="search"
            aria-label="Search people"
            placeholder="Search name, email or company"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="h-10 w-full rounded-lg sm:w-72"
          />
        </div>
      </div>
      {shown.length === 0 ? (
        <p className="rounded-xl border border-dashed px-5 py-8 text-center text-sm text-muted-foreground">
          Nobody matches.
        </p>
      ) : (
        <ul className="flex flex-col gap-3">
          {shown.map((row) => (
            <UserCard
              key={row.id}
              row={row}
              onChanged={(next) =>
                setData(rows.map((r) => (r.id === next.id ? next : r)))
              }
              onDeleted={reload}
            />
          ))}
        </ul>
      )}
    </section>
  );
}

/** The site owner's console: everyone on Aakalan, what they have made, and account actions. */
export function AdminConsole() {
  const user = useCurrentUser();
  if (!user.is_owner) {
    return <ErrorNotice message="This page is only for the site owner." />;
  }
  return (
    <div className="flex flex-col gap-10">
      <div className="settle flex items-center gap-5">
        <IconTile icon={ShieldStarIcon} size="lg" />
        <div className="flex flex-col gap-1">
          <p className="eyebrow">Admin</p>
          <h1 className="font-display text-3xl sm:text-4xl">
            Everyone on Aakalan
          </h1>
          <p className="text-muted-foreground">
            Every company and person, their estimates, and their accounts.
            Viewing an account is read only.
          </p>
        </div>
      </div>
      <Overview />
      <People />
    </div>
  );
}
