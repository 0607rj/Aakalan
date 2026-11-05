import { AppHero } from "@/components/app-hero";
import type { Metadata } from "next";

import {
  AccountDetails,
  AccountSummary,
  ChangePassword,
} from "./change-password";
import { AiSavingSetting } from "./pricing";

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
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)] lg:items-start">
        <AiSavingSetting />
        <AccountDetails />
      </div>
      <ChangePassword />
    </div>
  );
}
