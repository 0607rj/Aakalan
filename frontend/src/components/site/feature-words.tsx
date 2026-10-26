"use client";

import * as React from "react";

import { cn } from "@/lib/utils";

/** The things Aakalan prices, each with one plain line on how it is priced. */
const WORDS: { word: string; line: string }[] = [
  {
    word: "Sign-in",
    line: "Priced once at the level you need, the same for a startup or a ministry.",
  },
  {
    word: "Bookings",
    line: "Booking, moving and cancelling, at the level the project needs: basic, standard or advanced.",
  },
  {
    word: "Payments",
    line: "Set up, connected and tested, priced with and without AI tools.",
  },
  {
    word: "Chatbot",
    line: "The build, and the running cost of the questions it answers every day.",
  },
  {
    word: "Mobile app",
    line: "Added when people use it on their phones as well as on the web.",
  },
  {
    word: "Hosting",
    line: "Servers sized from the people online at once, for every year it runs.",
  },
  {
    word: "Support",
    line: "Years of upkeep, helpdesk hours and onsite staff, year by year.",
  },
];

const STEP_MS = 2600;

/**
 * The features, set large in a row: one is lit at a time with its line underneath, moving on
 * by itself while the row is on screen. Hovering or choosing a word holds it.
 */
export function FeatureWords({ className }: { className?: string }) {
  const [current, setCurrent] = React.useState(0);
  const [held, setHeld] = React.useState(false);
  const [visible, setVisible] = React.useState(false);
  const root = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const el = root.current;
    if (!el) return;
    const io = new IntersectionObserver(([entry]) =>
      setVisible(entry.isIntersecting),
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  React.useEffect(() => {
    if (held || !visible) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const timer = window.setInterval(
      () => setCurrent((i) => (i + 1) % WORDS.length),
      STEP_MS,
    );
    return () => window.clearInterval(timer);
  }, [held, visible]);

  const shown = WORDS[current];
  return (
    <div
      ref={root}
      className={cn("flex flex-col gap-8", className)}
      onMouseEnter={() => setHeld(true)}
      onMouseLeave={() => setHeld(false)}
    >
      <div
        role="group"
        aria-label="What gets priced"
        className="flex flex-wrap items-baseline gap-x-6 gap-y-1 sm:gap-x-9"
      >
        {WORDS.map((w, i) => (
          <button
            key={w.word}
            type="button"
            aria-pressed={i === current}
            onClick={() => {
              setCurrent(i);
              setHeld(true);
            }}
            onFocus={() => {
              setCurrent(i);
              setHeld(true);
            }}
            className={cn(
              "font-display text-[clamp(2.1rem,5.2vw,4rem)] leading-[1.1] transition-colors duration-500 focus-visible:outline-none",
              i === current
                ? "text-foreground"
                : "text-foreground/15 hover:text-foreground/35",
            )}
          >
            {w.word}
            <span
              aria-hidden="true"
              className={cn(
                "text-warm transition-opacity duration-500",
                i === current ? "opacity-100" : "opacity-0",
              )}
            >
              .
            </span>
          </button>
        ))}
      </div>
      <p className="max-w-2xl border-t pt-6 text-lg leading-relaxed text-muted-foreground">
        <span key={shown.word} className="settle inline-block">
          <span className="font-semibold text-foreground">{shown.word}:</span>{" "}
          {shown.line}
        </span>
      </p>
    </div>
  );
}
