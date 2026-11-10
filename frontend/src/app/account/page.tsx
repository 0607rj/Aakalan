import { AppHero } from "@/components/app-hero";
import type { Metadata } from "next";

import {
  AccountDetails,
  AccountSummary,
  ChangePassword,
} from "./change-password";

// Auth is client-side (token in localStorage), so there is no server-rendered shell to
// validate for instant navigation.
export const instant = false;

export const metadata: Metadata = {
  title: "Your account · Aakalan",
};

export default function AccountPage() {
  return (
    <div className="flex flex-col gap-5">
      <AppHero>
        <AccountSummary />
      </AppHero>
      <AccountDetails />
      <ChangePassword />
    </div>
  );
}
