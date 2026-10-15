import { AppShell } from "@/components/app-shell";

export default function ProjectsLayout({ children }: LayoutProps<"/projects">) {
  return <AppShell>{children}</AppShell>;
}
