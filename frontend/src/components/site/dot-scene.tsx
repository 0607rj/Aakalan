import { cn } from "@/lib/utils";

/**
 * Each page's picture, wide for screens from 640px up and squarer for phones. They are saved
 * images (public/hero/, drawn once from fixed seeds, not drawn in the browser: 30,000 dots on a
 * canvas made the page slow to show). `cost` is the home page's 30,000 possible costs, spread the
 * way Aakalan's simulation spreads them; the others draw what their page is about. Illustration
 * only: no real estimate is drawn.
 */
const SCENES = {
  cost: ["/hero/sky-wide.webp", "/hero/sky-tall.webp"],
  blocks: ["/hero/blocks-wide.webp", "/hero/blocks-tall.webp"],
  path: ["/hero/path-wide.webp", "/hero/path-tall.webp"],
  word: ["/hero/word-wide.webp", "/hero/word-tall.webp"],
  talk: ["/hero/talk-wide.webp", "/hero/talk-tall.webp"],
  dial: ["/hero/dial.webp", "/hero/dial.webp"],
  waterfall: ["/hero/waterfall.webp", "/hero/waterfall.webp"],
} as const;

export type DotSceneName = keyof typeof SCENES;

/** The picture on the ember panel: the image is only a mask, painted by `.dot-scene`. */
export function DotScene({
  scene,
  className,
}: {
  scene: DotSceneName;
  className?: string;
}) {
  const [wide, tall] = SCENES[scene];
  return (
    <div
      aria-hidden="true"
      className={cn("dot-scene absolute", className)}
      style={
        {
          "--scene-wide": `url(${wide})`,
          "--scene-tall": `url(${tall})`,
        } as React.CSSProperties
      }
    />
  );
}
