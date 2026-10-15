import { AppHeader } from "@/components/app-header";
import { AuthGuard } from "@/components/auth-guard";
import { HealthStatus } from "@/components/health-status";

export default function ProjectsLayout({ children }: LayoutProps<"/projects">) {
  return (
    <AuthGuard>
      <AppHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-8">
        {children}
      </main>
      <HealthStatus />
    </AuthGuard>
  );
}
