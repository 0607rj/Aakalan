"use client";

import * as React from "react";

/**
 * Beside a list of steps: the number of the step in the middle of the screen, very large and
 * outlined, with its name under it. It follows the scroll (the steps carry `data-step`); with
 * no script it shows the first step.
 */
export function StepNumber({ titles }: { titles: string[] }) {
  const [active, setActive] = React.useState(0);

  React.useEffect(() => {
    const steps = [...document.querySelectorAll<HTMLElement>("[data-step]")];
    if (steps.length === 0) return;
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting)
            setActive(Number(e.target.getAttribute("data-step")));
        }
      },
      { rootMargin: "-45% 0px -45% 0px" },
    );
    steps.forEach((s) => io.observe(s));
    return () => io.disconnect();
  }, []);

  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    <div
      aria-hidden="true"
      className="sticky top-0 flex h-svh flex-col justify-center"
    >
      <span
        key={active}
        className="step-numeral font-display text-[clamp(9rem,17vw,15rem)] leading-[0.8]"
      >
        {pad(active + 1)}
      </span>
      <span className="mt-6 font-mono text-sm text-faint">
        of {pad(titles.length)}
      </span>
      <span className="font-wide mt-2 text-2xl">{titles[active]}</span>
      <span className="mt-6 flex gap-1.5">
        {titles.map((t, i) => (
          <span
            key={t}
            className={`h-1 rounded-full transition-all duration-500 ${i === active ? "w-8 bg-tape-bright" : "w-3 bg-border"}`}
          />
        ))}
      </span>
    </div>
  );
}
