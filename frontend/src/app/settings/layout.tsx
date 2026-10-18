import { AppShell } from "@/components/app-shell";

export default function SettingsLayout({ children }: LayoutProps<"/settings">) {
  return <AppShell>{children}</AppShell>;
}
