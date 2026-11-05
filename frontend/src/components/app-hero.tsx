import { cn } from "@/lib/utils";

/**
 * The top of a signed-in page (`.app-head` in globals.css): no box, the page's label, title,
 * one line and buttons on the site's faint grid of hairlines, a rule below. `overlap` is kept
 * for the pages that pass it and does nothing now.
 */
export function AppHero({
  children,
  className,
}: {
  children: React.ReactNode;
  overlap?: boolean;
  className?: string;
}) {
  return (
    <div className={cn("app-head settle", className)}>
      <div aria-hidden="true" className="app-head-grid" />
      {children}
    </div>
  );
}
