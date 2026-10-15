/**
 * Display helpers. Money arrives as integer paise and is only ever formatted here — the UI
 * never computes money beyond summing integers for display.
 */

const PAISE_PER_RUPEE = 100;
const LAKH = 100_000;
const CRORE = 10_000_000;

const groupedRupees = new Intl.NumberFormat("en-IN", {
  maximumFractionDigits: 0,
});

/** "₹ 10.77 Cr" (≥ 1 crore), "₹ 12.3 L" (≥ 1 lakh), else "₹ 1,23,456". */
export function formatPaise(paise: number | null | undefined): string {
  if (paise === null || paise === undefined) return "—";
  const rupees = paise / PAISE_PER_RUPEE;
  const sign = rupees < 0 ? "−" : "";
  const abs = Math.abs(rupees);
  if (abs >= CRORE) return `${sign}₹ ${(abs / CRORE).toFixed(2)} Cr`;
  if (abs >= LAKH) return `${sign}₹ ${(abs / LAKH).toFixed(1)} L`;
  return `${sign}₹ ${groupedRupees.format(abs)}`;
}

/** Exact rupees with paise, en-IN grouping — for traces. */
export function formatPaiseExact(paise: number | null | undefined): string {
  if (paise === null || paise === undefined) return "—";
  return `₹ ${(paise / PAISE_PER_RUPEE).toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

/** Decimal strings from the API (e.g. "8.70000") trimmed for display. */
export function formatDecimal(
  value: string | number | null | undefined,
  digits = 2,
): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return String(value);
  return n.toLocaleString("en-IN", { maximumFractionDigits: digits });
}

export function formatPercent(
  value: string | number | null | undefined,
): string {
  if (value === null || value === undefined) return "—";
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return String(value);
  return `${(n * 100).toLocaleString("en-IN", { maximumFractionDigits: 1 })}%`;
}

export function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}

const dateFormat = new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" });
const dateTimeFormat = new Intl.DateTimeFormat("en-IN", {
  dateStyle: "medium",
  timeStyle: "short",
});

export function formatDate(iso: string): string {
  return dateFormat.format(new Date(iso));
}

export function formatDateTime(iso: string): string {
  return dateTimeFormat.format(new Date(iso));
}

/** "uptime_sla" → "Uptime sla"; keeps API keys readable without a lookup table. */
export function humanize(key: string): string {
  const text = key.replace(/[._]/g, " ").trim();
  return text.charAt(0).toUpperCase() + text.slice(1);
}
