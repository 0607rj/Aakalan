/**
 * The hero picture: a night sky made of 30,000 possible costs for one project, spread the way
 * Aakalan's simulation spreads them (skewed: overruns go further than savings), with the low,
 * likely and high marks. Illustration only: no real estimate is drawn.
 *
 * It is a saved image (public/hero/sky-*.webp, drawn once from a fixed seed), not drawn in the
 * browser: 30,000 dots on a canvas made the page slow to show. A wide picture for screens from
 * 640px up and a squarer one for phones.
 */
export function CostSky({ className }: { className?: string }) {
  return (
    <picture>
      <source media="(min-width: 640px)" srcSet="/hero/sky-wide.webp" />
      <img
        src="/hero/sky-tall.webp"
        alt=""
        aria-hidden="true"
        width={1200}
        height={900}
        fetchPriority="high"
        decoding="async"
        className={`cost-sky absolute -inset-[6%] h-[112%] w-[112%] max-w-none object-cover ${className ?? ""}`}
      />
    </picture>
  );
}
