"use client";

import * as React from "react";

/**
 * Scroll reveal for every `[data-reveal]` element: it rises in (and its figure plays) once it
 * comes into view. `.rv` on <html> (set by a tiny script in the root layout) is what hides
 * them, so without scripts nothing is hidden; with reduced motion everything shows at once.
 */
export function RevealOnScroll() {
  React.useEffect(() => {
    const root = document.documentElement;
    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const show = (el: Element) => el.classList.add("is-in");
    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            show(entry.target);
            io.unobserve(entry.target);
          }
        }
      },
      { threshold: 0.1, rootMargin: "0px 0px -4% 0px" },
    );
    // remembered here, not marked on the element: parts still hydrating must match the server
    const seen = new WeakSet<Element>();
    // React has taken the element over once it carries its fiber; until then, touching its
    // class would break hydration, so look again a moment later
    const hydrated = (el: Element) =>
      Object.keys(el).some((k) => k.startsWith("__reactFiber$"));
    let retry = 0;
    let tries = 0;
    const scan = () => {
      let waiting = false;
      tries += 1;
      document.querySelectorAll("[data-reveal]:not(.is-in)").forEach((el) => {
        if (seen.has(el)) return;
        // after a few seconds, show it anyway rather than leave it hidden
        if (!hydrated(el) && tries < 100) {
          waiting = true;
          return;
        }
        seen.add(el);
        if (still) show(el);
        else io.observe(el);
      });
      window.clearTimeout(retry);
      if (waiting) retry = window.setTimeout(scan, 50);
    };
    root.classList.add("rv");
    // start once the page has loaded (and React has taken it over), then watch for new parts
    const mo = new MutationObserver(scan);
    let frame = 0;
    const start = () => {
      frame = requestAnimationFrame(() => {
        scan();
        mo.observe(document.body, { childList: true, subtree: true });
      });
    };
    if (document.readyState === "complete") start();
    else window.addEventListener("load", start, { once: true });
    return () => {
      window.removeEventListener("load", start);
      cancelAnimationFrame(frame);
      window.clearTimeout(retry);
      mo.disconnect();
      io.disconnect();
    };
  }, []);
  return null;
}
