"use client";

import * as React from "react";

/** What the letters flick through before they settle: a price being worked out. */
const POOL = "₹0123456789";
/** How long every letter scrambles before the first one settles, then the gap to the next. */
const HOLD_MS = 420;
const PER_LETTER_MS = 55;
/** When each letter starts scrambling, after the one before. */
const START_STEP_MS = 18;

/**
 * The home page headline: its letters flick through ₹ signs and digits, left to right, then
 * settle on the real words, like a meter reaching a price. Each letter keeps its own width while
 * it scrambles, so the line never jumps. Played once, after the fonts load; the server sends the
 * real words, screen readers get them as one line, and with reduced motion nothing moves.
 */
export function ScrambleText({
  parts,
}: {
  parts: { text: string; className?: string }[];
}) {
  const ref = React.useRef<HTMLSpanElement>(null);

  React.useEffect(() => {
    const root = ref.current;
    if (!root) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const letters = [...root.querySelectorAll<HTMLElement>("[data-c]")];
    let raf = 0;
    let cancelled = false;

    const reset = () =>
      letters.forEach((s) => {
        s.textContent = s.dataset.c ?? "";
        s.style.width = "";
        s.style.color = "";
      });

    const run = () => {
      if (cancelled) return;
      // fixed widths first, measured on the real letters
      letters.forEach((s) => {
        s.style.width = `${s.getBoundingClientRect().width}px`;
      });
      const t0 = performance.now();
      const tick = (now: number) => {
        if (cancelled) return;
        const t = now - t0;
        let settled = 0;
        letters.forEach((s, k) => {
          if (t >= HOLD_MS + k * PER_LETTER_MS) {
            if (s.textContent !== s.dataset.c) {
              s.textContent = s.dataset.c ?? "";
              s.style.color = "";
            }
            settled += 1;
          } else if (t >= k * START_STEP_MS) {
            s.textContent = POOL[Math.floor(Math.random() * POOL.length)] ?? "";
            s.style.color = "var(--tape-bright)";
          }
        });
        if (settled < letters.length) raf = requestAnimationFrame(tick);
        else reset();
      };
      raf = requestAnimationFrame(tick);
    };

    void document.fonts.ready.then(run);
    return () => {
      cancelled = true;
      cancelAnimationFrame(raf);
      reset();
    };
  }, []);

  const full = parts.map((p) => p.text).join("");
  return (
    <>
      <span className="sr-only">{full}</span>
      <span ref={ref} aria-hidden="true">
        {parts.map((part, pi) => (
          <span key={pi} className={part.className}>
            {part.text.split(/(\s+)/).map((piece, wi) =>
              /^\s+$/.test(piece) ? (
                " "
              ) : piece ? (
                <span key={wi} className="inline-block whitespace-nowrap">
                  {[...piece].map((c, ci) => (
                    <span
                      key={ci}
                      data-c={c}
                      className="inline-block text-center"
                    >
                      {c}
                    </span>
                  ))}
                </span>
              ) : null,
            )}
          </span>
        ))}
      </span>
    </>
  );
}
