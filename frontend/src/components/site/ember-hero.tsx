import { cn } from "@/lib/utils";

import { DotScene, type DotSceneName } from "./dot-scene";

/**
 * The top of every public page: the ember panel (orange falling to near black) with the page's
 * dot picture behind the words. It fills the first screen and a little more, so its white mist,
 * rising in uneven swells, starts at the bottom of the screen and curves past on scroll.
 * `full` is the home page: a glow behind the words and the picture across the whole screen. The
 * fixed nav floats over it, so the content starts below the nav.
 */
export function EmberHero({
  children,
  scene,
  full = false,
  className,
  sceneClassName,
}: {
  children: React.ReactNode;
  scene: DotSceneName;
  full?: boolean;
  className?: string;
  /** Where the picture sits: a page's words decide what space it has. */
  sceneClassName?: string;
}) {
  return (
    <section className={cn("ember min-h-[calc(100svh+90px)]", className)}>
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-full"
      >
        {full ? (
          <div className="absolute top-[22%] left-[37%] h-1/2 w-[46vw] -translate-x-1/2 bg-[radial-gradient(closest-side,rgb(255_150_80/0.3),transparent)]" />
        ) : null}
        <DotScene
          scene={scene}
          className={cn(
            "left-1/2 aspect-[1/1.05] -translate-x-1/2 sm:aspect-[1680/822] sm:w-[min(1500px,128vw)]",
            full
              ? "top-[190px] w-[140vw] sm:top-10"
              : "bottom-10 w-[130vw] sm:top-[50svh] sm:bottom-auto sm:-translate-y-1/2",
            sceneClassName,
          )}
        />
      </div>
      {children}
      <div aria-hidden="true" className="mist" />
      <div aria-hidden="true" className="mist-swells">
        <i />
        <i />
        <i />
        <i />
        <i />
      </div>
    </section>
  );
}
