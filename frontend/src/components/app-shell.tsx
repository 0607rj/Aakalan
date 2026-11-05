import { AppSidebar } from "@/components/app-sidebar";
import { AuthGuard } from "@/components/auth-guard";
import { ViewingBanner } from "@/components/viewing-banner";

/** Signed-in page frame, laid out as a web app: auth guard, the ink sidebar (a top bar and
 * drawer on phones), then the page in one wide column (`.app-ui` in globals.css). A page's top
 * is a rounded ember card (`AppHero`), the soft white cards below it. */
export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <div className="app-ui flex min-h-svh flex-1 flex-col lg:flex-row">
        <ViewingBanner />
        <AppSidebar />
        <main className="w-full max-w-6xl min-w-0 flex-1 px-4 pt-5 pb-16 sm:px-6 lg:px-9 lg:pt-8">
          {children}
        </main>
      </div>
    </AuthGuard>
  );
}
