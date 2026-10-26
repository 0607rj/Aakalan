import type { Metadata } from "next";

import { AccountSummary, ChangePassword } from "./change-password";

export const metadata: Metadata = {
  title: "Your account · Aakalan",
};

export default function AccountPage() {
  return (
    <div className="flex flex-col gap-8">
      <AccountSummary />
      <ChangePassword />
    </div>
  );
}
