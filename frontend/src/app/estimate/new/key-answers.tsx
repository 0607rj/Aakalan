"use client";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { FoundStaff, StaffItem, UnclearPoint } from "@/lib/api/client";

import { Citation } from "./parts";

const MAX_STAFF = 1000; // StaffItem.count
const MAX_MONTHS = 240; // StaffItem.months

/** A staff line on the form: as found, with the user's edits as typed. */
export type StaffRow = FoundStaff & {
  countText: string;
  monthsText: string;
  leftOut: boolean;
};

export function staffRows(staff: FoundStaff[]): StaffRow[] {
  return staff.map((s) => ({
    ...s,
    countText: String(Number(s.count)),
    monthsText: s.months == null ? "" : String(s.months),
    leftOut: false,
  }));
}

export function staffError(row: StaffRow): string | null {
  if (row.leftOut) return null;
  const n = Number(row.countText);
  if (
    row.countText.trim() === "" ||
    !Number.isFinite(n) ||
    n <= 0 ||
    n > MAX_STAFF
  )
    return `Enter a number from 1 to ${MAX_STAFF}.`;
  if (row.monthsText.trim() === "") return null;
  const m = Number(row.monthsText);
  if (!Number.isInteger(m) || m < 1 || m > MAX_MONTHS)
    return `Months: a whole number from 1 to ${MAX_MONTHS}, or empty.`;
  return null;
}

/** The staff list the request sends: unchanged lines exactly as found (so they stay cited). */
export function sentStaff(rows: StaffRow[]): StaffItem[] {
  return rows
    .filter((r) => !r.leftOut && staffError(r) === null)
    .map((r) => {
      const count =
        Number(r.countText) === Number(r.count) ? r.count : r.countText.trim();
      const months = r.monthsText.trim() === "" ? null : Number(r.monthsText);
      return {
        kind: r.kind,
        role: r.role,
        count,
        months,
        seats: r.seats,
        call_off: r.call_off,
        found_index: r.found_index ?? null,
      };
    });
}

/** The pre-bid queries the reading raised about one answer. */
export function Queries({
  queries,
  approximatePages,
}: {
  queries: UnclearPoint[];
  approximatePages: boolean;
}) {
  if (queries.length === 0) return null;
  return (
    <div className="flex flex-col gap-2 rounded-lg bg-warning-muted px-3 py-2 text-sm">
      <span className="font-medium">
        Pre-bid {queries.length === 1 ? "query" : "queries"} to send
      </span>
      <ul className="flex flex-col gap-2">
        {queries.map((q) => (
          <li key={`${q.topic}-${q.quote}`} className="flex flex-col gap-1">
            <span>{q.prebid_query || q.why}</span>
            {q.page != null && q.quote ? (
              <Citation
                evidence={[
                  {
                    page: q.page,
                    clause_ref: q.clause_ref,
                    quote: q.quote,
                    document: q.document,
                    checked: true,
                  },
                ]}
                approximatePages={approximatePages}
              />
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}

/** The staff during support the document asks for: people, months, or left out. */
export function StaffEditor({
  rows,
  onChange,
  approximatePages,
}: {
  rows: StaffRow[];
  onChange: (rows: StaffRow[]) => void;
  approximatePages: boolean;
}) {
  const set = (i: number, change: Partial<StaffRow>) =>
    onChange(rows.map((r, j) => (j === i ? { ...r, ...change } : r)));
  if (rows.length === 0)
    return (
      <span className="text-sm text-muted-foreground">
        The document asks for no staff during support.
      </span>
    );
  return (
    <ul className="flex flex-col gap-3">
      {rows.map((r, i) => {
        const error = staffError(r);
        return (
          <li
            key={`${r.role}-${i}`}
            className="flex flex-col gap-2 rounded-lg border px-3 py-3"
          >
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-medium">{r.role}</span>
              <span className="text-sm text-muted-foreground">
                {r.kind === "onsite" ? "at your office" : "offsite"}
              </span>
              {r.call_off ? (
                <span className="rounded-full bg-warning-muted px-2 py-0.5 text-xs font-medium">
                  Buyer sets the headcount
                </span>
              ) : null}
              {r.seats ? (
                <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium">
                  Round-the-clock seats
                </span>
              ) : null}
            </div>
            {r.leftOut ? null : (
              <div className="flex flex-wrap items-end gap-4">
                <div className="flex flex-col gap-1">
                  <Label htmlFor={`staff-count-${i}`} className="text-sm">
                    {r.seats ? "Seats" : "People"}
                  </Label>
                  <Input
                    id={`staff-count-${i}`}
                    type="number"
                    inputMode="decimal"
                    min={1}
                    max={MAX_STAFF}
                    value={r.countText}
                    onChange={(e) => set(i, { countText: e.target.value })}
                    className="h-9 w-24"
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <Label htmlFor={`staff-months-${i}`} className="text-sm">
                    Months (empty = every support year)
                  </Label>
                  <Input
                    id={`staff-months-${i}`}
                    type="number"
                    inputMode="numeric"
                    min={1}
                    max={MAX_MONTHS}
                    value={r.monthsText}
                    onChange={(e) => set(i, { monthsText: e.target.value })}
                    className="h-9 w-24"
                  />
                </div>
              </div>
            )}
            {error ? (
              <span className="text-sm text-destructive">{error}</span>
            ) : null}
            {r.why ? (
              <span className="text-sm text-muted-foreground">{r.why}</span>
            ) : null}
            <Citation
              evidence={r.evidence}
              approximatePages={approximatePages}
            />
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={r.leftOut}
                onChange={(e) => set(i, { leftOut: e.target.checked })}
                className="size-4 accent-primary"
              />
              Leave out of the price
            </label>
          </li>
        );
      })}
    </ul>
  );
}
