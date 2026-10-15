import { AppHeader } from "@/components/app-header";
import { AuthGuard } from "@/components/auth-guard";
import { HealthStatus } from "@/components/health-status";

/** Signed-in page frame: auth guard, header, centred content, health footer. */
export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <AppHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">
        {children}
      </main>
      <HealthStatus />
    </AuthGuard>
  );
}
