import { cn } from "@/lib/utils";

/**
 * The top of a signed-in page, on the same ember panel as the public pages: full width, the
 * nav floating over it, its words in white (`.app-hero` turns the page's colours light), and a
 * short white mist at the bottom. `overlap` leaves room for the next card to rise into it (that
 * card takes `app-rise`).
 */
export function AppHero({
  children,
  overlap = false,
  className,
}: {
  children: React.ReactNode;
  overlap?: boolean;
  className?: string;
}) {
  return (
    <section className={cn("ember app-hero", className)}>
      <div
        className={cn(
          "relative z-[4] mx-auto w-full max-w-5xl px-4 pt-28 sm:px-6 sm:pt-32",
          overlap
            ? "pb-[clamp(150px,16vw,190px)]"
            : "pb-[clamp(64px,8vw,96px)]",
        )}
      >
        {children}
      </div>
      <div aria-hidden="true" className="mist app" />
    </section>
  );
}
