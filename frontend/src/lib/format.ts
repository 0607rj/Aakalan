/**
 * Display helpers. Money arrives as integer minor units (paise for INR, cents for USD — the
 * API names these fields `*_paise`) and is only ever formatted here — the UI never computes
 * money beyond summing or subtracting integers for display.
 */

/** ISO currency code of an estimate ("INR" | "USD"). */
export type Currency = string;

const MINOR_PER_MAJOR = 100;
const LAKH = 100_000;
const CRORE = 10_000_000;
const THOUSAND = 1_000;
const HUNDRED_THOUSAND = 100_000;
const MILLION = 1_000_000;

const groupedRupees = new Intl.NumberFormat("en-IN", {
  maximumFractionDigits: 0,
});
const groupedDollars = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 0,
});

/** "₹" for INR, "$" for USD, else the code itself. */
export function currencySymbol(currency: Currency = "INR"): string {
  if (currency === "INR") return "₹";
  if (currency === "USD") return "$";
  return currency;
}

/**
 * INR: "₹ 10.77 Cr" (≥ 1 crore), "₹ 12.3 L" (≥ 1 lakh), else "₹ 1,23,456".
 * USD: "$1.23 M" (≥ 1 million), "$450 K" (≥ 100 thousand), else "$12,345".
 */
export function formatPaise(
  paise: number | null | undefined,
  currency: Currency = "INR",
): string {
  if (paise === null || paise === undefined) return "—";
  const major = paise / MINOR_PER_MAJOR;
  const sign = major < 0 ? "−" : "";
  const abs = Math.abs(major);
  if (currency === "INR") {
    if (abs >= CRORE) return `${sign}₹ ${(abs / CRORE).toFixed(2)} Cr`;
    if (abs >= LAKH) return `${sign}₹ ${(abs / LAKH).toFixed(1)} L`;
    return `${sign}₹ ${groupedRupees.format(abs)}`;
  }
  const symbol = currencySymbol(currency);
  if (abs >= MILLION) return `${sign}${symbol}${(abs / MILLION).toFixed(2)} M`;
  if (abs >= HUNDRED_THOUSAND)
    return `${sign}${symbol}${Math.round(abs / THOUSAND)} K`;
  return `${sign}${symbol}${groupedDollars.format(abs)}`;
}

/** Round to two significant figures: an estimate, not a bill (67,883 -> 68,000). */
export function roundEstimate(paise: number): number {
  if (paise === 0) return 0;
  const magnitude = 10 ** (Math.floor(Math.log10(Math.abs(paise))) - 1);
  return Math.round(paise / magnitude) * magnitude;
}

/** A rounded figure without trailing zeros: "₹ 33 L", "₹ 2.9 Cr", "₹ 68,000". */
function formatEstimate(paise: number, currency: Currency): string {
  return formatPaise(roundEstimate(paise), currency)
    .replace(/\.0+ (L|Cr|M|K)$/, " $1")
    .replace(/(\.\d*?[1-9])0+ (L|Cr|M|K)$/, "$1 $2");
}

/** "about ₹68,000" — a rounded single estimate. */
export function formatApprox(
  paise: number | null | undefined,
  currency: Currency = "INR",
): string {
  if (paise === null || paise === undefined) return "—";
  return `about ${formatEstimate(paise, currency)}`;
}

/**
 * "₹58,000 – ₹92,000": an estimate shown as a rounded range. Falls back to "about …" when
 * the two ends round to the same figure.
 */
export function formatRange(
  low: number | null | undefined,
  high: number | null | undefined,
  currency: Currency = "INR",
): string {
  if (low === null || low === undefined || high === null || high === undefined)
    return "—";
  const a = formatEstimate(low, currency);
  const b = formatEstimate(high, currency);
  return a === b ? `about ${a}` : `${a} – ${b}`;
}

/** Exact amount with two decimals (en-IN grouping for INR, en-US otherwise) — for traces. */
export function formatPaiseExact(
  paise: number | null | undefined,
  currency: Currency = "INR",
): string {
  if (paise === null || paise === undefined) return "—";
  const locale = currency === "INR" ? "en-IN" : "en-US";
  const space = currency === "INR" ? " " : "";
  return `${currencySymbol(currency)}${space}${(
    paise / MINOR_PER_MAJOR
  ).toLocaleString(locale, {
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
