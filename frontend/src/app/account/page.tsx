import type { Metadata } from "next";

import { ChangePassword } from "./change-password";

export const metadata: Metadata = {
  title: "Your account · Aakalan",
};

export default function AccountPage() {
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
        Your account
      </h1>
      <ChangePassword />
    </div>
  );
}
