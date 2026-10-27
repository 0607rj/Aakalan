import type { Metadata } from "next";

import { AccountSummary, ChangePassword } from "./change-password";
import { AiSavingSetting } from "./pricing";

// Auth is client-side (token in localStorage), so there is no server-rendered shell to
// validate for instant navigation.
export const instant = false;

export const metadata: Metadata = {
  title: "Your account · Aakalan",
};

export default function AccountPage() {
  return (
    <div className="flex flex-col gap-8">
      <AccountSummary />
      <AiSavingSetting />
      <ChangePassword />
    </div>
  );
}
