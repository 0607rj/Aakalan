"use client";

import * as React from "react";

/* One plain requirement line, as tenders write them; the marked words are the features. */
const LINE: (string | { words: string; feature: string })[] = [
  "The portal shall let citizens ",
  { words: "register", feature: "Sign-in" },
  ", ",
  { words: "pay fees online", feature: "Payment" },
  " and ",
  { words: "track their complaint", feature: "Grievance tickets" },
  " by ",
  { words: "SMS", feature: "SMS gateway" },
  ".",
];

const MARKED = LINE.filter((part) => typeof part !== "string").length;

/**
 * What Aakalan does, shown on one line: a tender sentence across the page in large type, on the
 * light page. As it rises up the screen its words light up
 * one by one, each with the feature it becomes under it. With reduced motion (or before the
 * script runs on a phone) every word is lit.
 */
export function TenderLine() {
  const ref = React.useRef<HTMLHeadingElement>(null);
  const [lit, setLit] = React.useState(MARKED);

  React.useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let frame = 0;
    const update = () => {
      frame = 0;
      const r = el.getBoundingClientRect();
      const vh = window.innerHeight;
      // 0 when the line's middle is at 85% of the screen, 1 at 40%
      const mid = r.top + r.height / 2;
      const p = Math.min(1, Math.max(0, (vh * 0.85 - mid) / (vh * 0.45)));
      setLit(Math.round(p * MARKED));
    };
    const onScroll = () => {
      if (!frame) frame = requestAnimationFrame(update);
    };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      cancelAnimationFrame(frame);
    };
  }, []);

  let n = 0;
  return (
    <section className="pt-6 pb-[clamp(72px,10vw,120px)]">
      <div className="page-wrap">
        <p className="font-mono text-xs tracking-[0.08em] text-tape uppercase">
          One line of a tender
        </p>
        <h2
          ref={ref}
          className="font-display mt-8 max-w-6xl text-[clamp(2.2rem,5.2vw,4.4rem)] leading-[1.75] text-faint/70"
        >
          {LINE.map((part, i) => {
            if (typeof part === "string") return part;
            const on = n++ < lit;
            return (
              <span key={i} className="relative inline-block whitespace-nowrap">
                <span
                  className={`transition-colors duration-500 ${on ? "text-foreground" : ""}`}
                >
                  {part.words}
                </span>
                <span
                  aria-hidden="true"
                  className={`absolute inset-x-0 bottom-[0.18em] h-[3px] origin-left rounded-full bg-tape-bright transition-transform duration-500 ${on ? "scale-x-100" : "scale-x-0"}`}
                />
                <span
                  className={`absolute top-[calc(100%-0.35em)] left-0 font-sans text-[clamp(0.9rem,1.35vw,1.1rem)] leading-none font-medium tracking-normal whitespace-nowrap text-tape transition-[opacity,transform] duration-500 ${on ? "translate-y-0 opacity-100" : "-translate-y-2 opacity-0"}`}
                >
                  → {part.feature}
                </span>
              </span>
            );
          })}
        </h2>
        <p className="mt-12 max-w-xl text-lg text-muted-foreground">
          Aakalan reads the document the same way: every feature it finds keeps
          the line it came from, so you can check each one before it is priced.
        </p>
      </div>
    </section>
  );
}
