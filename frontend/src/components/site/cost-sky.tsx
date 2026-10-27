/**
 * The hero picture: a night sky made of 30,000 possible costs for one project, spread the way
 * Aakalan's simulation spreads them (skewed: overruns go further than savings), with the low,
 * likely and high marks. Illustration only: no real estimate is drawn.
 *
 * It is a saved image (public/hero/sky-*.webp, drawn once from a fixed seed), not drawn in the
 * browser: 30,000 dots on a canvas made the page slow to show. The image is only a transparency
 * mask, painted in the palette's accent (`--tape`), so it suits every palette. A wide picture
 * for screens from 640px up and a squarer one for phones.
 */
export function CostSky({ className }: { className?: string }) {
  return (
    <>
      {/* a soft glow under the peak, in CSS: drawn into the mask it showed as bands */}
      <div
        aria-hidden="true"
        className="absolute inset-0 bg-[radial-gradient(42%_52%_at_42%_52%,color-mix(in_srgb,var(--tape)_20%,transparent),transparent_72%)]"
      />
      <div
        aria-hidden="true"
        className={`cost-sky absolute -inset-[6%] h-[112%] w-[112%] bg-tape [mask-image:url(/hero/sky-tall.webp)] [mask-size:cover] [mask-position:center] [mask-repeat:no-repeat] sm:[mask-image:url(/hero/sky-wide.webp)] ${className ?? ""}`}
      />
    </>
  );
}
