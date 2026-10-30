import { AppHeader } from "@/components/app-header";
import { AuthGuard } from "@/components/auth-guard";
import { ViewingBanner } from "@/components/viewing-banner";
import { Footer } from "@/components/site/footer";

/** Signed-in page frame: auth guard, the floating bar, centred content, footer, in the app's
 * light theme (`.app-ui` in globals.css). A page's top sits on the ember panel (`AppHero`). */
export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <div className="app-ui flex min-h-full flex-1 flex-col">
        <ViewingBanner />
        <AppHeader />
        <main className="mx-auto w-full max-w-5xl flex-1 px-4 pt-28 pb-16 sm:px-6">
          {children}
        </main>
        <Footer />
      </div>
    </AuthGuard>
  );
}
