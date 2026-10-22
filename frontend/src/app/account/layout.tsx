import { AppShell } from "@/components/app-shell";

export default function AccountLayout({ children }: LayoutProps<"/account">) {
  return <AppShell>{children}</AppShell>;
}
