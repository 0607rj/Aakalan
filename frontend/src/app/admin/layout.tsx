import { AppShell } from "@/components/app-shell";

export default function AdminLayout({ children }: LayoutProps<"/admin">) {
  return <AppShell>{children}</AppShell>;
}
