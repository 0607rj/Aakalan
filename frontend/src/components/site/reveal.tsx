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
      { threshold: 0.2, rootMargin: "0px 0px -8% 0px" },
    );
    // remembered here, not marked on the element: parts still hydrating must match the server
    const seen = new WeakSet<Element>();
    const scan = () => {
      document.querySelectorAll("[data-reveal]:not(.is-in)").forEach((el) => {
        if (seen.has(el)) return;
        seen.add(el);
        if (still) show(el);
        else io.observe(el);
      });
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
      mo.disconnect();
      io.disconnect();
    };
  }, []);
  return null;
}
