import { AppHeader } from "@/components/app-header";
import { AuthGuard } from "@/components/auth-guard";
import { HealthStatus } from "@/components/health-status";
import { Footer } from "@/components/site/footer";

/** Signed-in page frame: auth guard, the bar, centred content, footer, in the app's light
 * theme (`.app-ui` in globals.css). */
export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <div className="app-ui flex min-h-full flex-1 flex-col">
        <AppHeader />
        <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-10 sm:px-6">
          {children}
        </main>
        <HealthStatus />
        <Footer />
      </div>
    </AuthGuard>
  );
}
