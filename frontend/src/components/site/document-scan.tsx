"use client";

import * as React from "react";

import { cn } from "@/lib/utils";

interface Clause {
  n: string;
  text: string;
  /** The feature it becomes; none for a sentence that asks for nothing. */
  item: number | null;
}

/** Illustration only: a made-up page of a tender, not a real document or estimate. */
const CLAUSES: Clause[] = [
  {
    n: "4.1",
    text: "Citizens shall book an appointment at any centre online.",
    item: 0,
  },
  {
    n: "4.1.1",
    text: "The list of centres is kept by the department.",
    item: null,
  },
  {
    n: "4.2",
    text: "The portal must accept payment by UPI and card.",
    item: 1,
  },
  {
    n: "4.3",
    text: "Offices are open 10:00 to 17:30 on working days.",
    item: null,
  },
  {
    n: "4.4",
    text: "An SMS reminder shall be sent one day before.",
    item: 2,
  },
  { n: "4.5", text: "The system shall work on mobile phones.", item: 3 },
];

const ITEMS = [
  {
    name: "Bookings",
    level: "Standard",
    price: "₹2.6 L",
    chip: "§4.1 → Bookings",
  },
  {
    name: "Online payment",
    level: "Basic",
    price: "₹1.1 L",
    chip: "§4.2 → Online payment",
  },
  {
    name: "SMS reminders",
    level: "Basic",
    price: "₹0.9 L",
    chip: "§4.4 → SMS reminders",
  },
  {
    name: "Works on phones",
    level: "In every estimate",
    price: "Included",
    chip: "§4.5 → Phones",
  },
];

const SCAN_MS = 4400;
const FLY_MS = 950;
const PAUSE_MS = 3400;

/**
 * How it works, step 1: a line scans down a tender page; each sentence that asks for something
 * lights up and flies across as a priced feature, and the rest stay grey. It plays while on
 * screen and loops; at rest (and with reduced motion) the page shows everything found.
 */
export function DocumentScan({ className }: { className?: string }) {
  const stage = React.useRef<HTMLDivElement>(null);
  const doc = React.useRef<HTMLDivElement>(null);
  const beam = React.useRef<HTMLDivElement>(null);
  const rows = React.useRef<(HTMLParagraphElement | null)[]>([]);
  const items = React.useRef<(HTMLLIElement | null)[]>([]);
  const chips = React.useRef<(HTMLSpanElement | null)[]>([]);
  const [passed, setPassed] = React.useState(CLAUSES.length);
  const [shown, setShown] = React.useState<boolean[]>(() =>
    ITEMS.map(() => true),
  );

  React.useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const host = stage.current;
    const page = doc.current;
    const line = beam.current;
    if (!host || !page || !line) return;
    let cancelled = false;
    let raf = 0;
    let timer = 0;
    let inView = false;
    let playing = false;

    const fly = (i: number, from: HTMLElement) => {
      const chip = chips.current[i];
      const to = items.current[i];
      if (!chip || !to) return;
      const s = host.getBoundingClientRect();
      const a = from.getBoundingClientRect();
      const b = to.getBoundingClientRect();
      const x0 = a.left - s.left + 10;
      const y0 = a.top - s.top + a.height / 2 - 14;
      const dx = b.left - s.left + 10 - x0;
      const dy = b.top - s.top + b.height / 2 - 14 - y0;
      chip.style.left = `${x0}px`;
      chip.style.top = `${y0}px`;
      const flight = chip.animate(
        [
          { transform: "translate(0,0) scale(.85)", opacity: 0 },
          {
            transform: `translate(${dx * 0.45}px,${dy * 0.45 - 34}px) scale(1.06)`,
            opacity: 1,
            offset: 0.45,
          },
          {
            transform: `translate(${dx}px,${dy}px) scale(.92)`,
            opacity: 0.2,
          },
        ],
        { duration: FLY_MS, easing: "cubic-bezier(.5,0,.3,1)" },
      );
      flight.onfinish = () => {
        if (!cancelled) setShown((now) => now.map((v, j) => v || j === i));
      };
    };

    const run = () => {
      if (cancelled) return;
      if (!inView) {
        playing = false;
        return;
      }
      playing = true;
      setPassed(0);
      setShown(ITEMS.map(() => false));
      const height = page.clientHeight;
      const t0 = performance.now();
      let p = 0;
      line.style.opacity = "1";
      const step = (now: number) => {
        if (cancelled) return;
        const k = Math.min(1, (now - t0) / SCAN_MS);
        const y = k * (height - 3);
        line.style.transform = `translateY(${y}px)`;
        let row = rows.current[p];
        while (row && y >= row.offsetTop + row.offsetHeight / 2) {
          const item = CLAUSES[p]?.item ?? null;
          p += 1;
          setPassed(p);
          if (item !== null) fly(item, row);
          row = rows.current[p];
        }
        if (k < 1) raf = requestAnimationFrame(step);
        else {
          line.style.opacity = "0";
          timer = window.setTimeout(run, PAUSE_MS);
        }
      };
      raf = requestAnimationFrame(step);
    };

    const io = new IntersectionObserver(
      ([entry]) => {
        inView = entry?.isIntersecting ?? false;
        if (inView && !playing) run();
      },
      { threshold: 0.35 },
    );
    io.observe(host);
    return () => {
      cancelled = true;
      cancelAnimationFrame(raf);
      window.clearTimeout(timer);
      io.disconnect();
    };
  }, []);

  return (
    <div
      ref={stage}
      aria-hidden="true"
      className={cn(
        "relative grid items-center gap-5 sm:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]",
        className,
      )}
    >
      <div
        ref={doc}
        className="relative -rotate-[1.2deg] overflow-hidden rounded-2xl border bg-card px-[18px] pt-[18px] pb-3.5 shadow-[0_18px_40px_-26px_rgb(0_0_0/0.35)]"
      >
        <p className="mb-2.5 font-mono text-[11px] tracking-[0.05em] text-faint uppercase">
          RFP · Section 4 · Page 7
        </p>
        {CLAUSES.map((c, i) => (
          <p
            key={c.n}
            ref={(el) => {
              rows.current[i] = el;
            }}
            className={cn(
              "scan-clause",
              i < passed && (c.item === null ? "seen" : "hit"),
            )}
          >
            <b>{c.n}</b>
            {c.text}
          </p>
        ))}
        <div ref={beam} className="scan-beam" />
      </div>
      <ul className="flex flex-col gap-2">
        <li className="font-mono text-[11px] tracking-[0.06em] text-faint uppercase">
          Found and priced
        </li>
        {ITEMS.map((item, i) => (
          <li
            key={item.name}
            ref={(el) => {
              items.current[i] = el;
            }}
            className={cn("scan-item", shown[i] && "in")}
          >
            <span className="min-w-0 leading-tight font-medium">
              {item.name}
              <small className="block text-xs font-normal text-muted-foreground">
                {item.level}
              </small>
            </span>
            <span className="font-mono text-[13.5px] font-medium tabular-nums">
              {item.price}
            </span>
          </li>
        ))}
      </ul>
      {ITEMS.map((item, i) => (
        <span
          key={item.chip}
          ref={(el) => {
            chips.current[i] = el;
          }}
          className="scan-chip"
        >
          {item.chip}
        </span>
      ))}
    </div>
  );
}
