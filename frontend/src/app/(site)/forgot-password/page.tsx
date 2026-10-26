import type { Metadata } from "next";

import { ForgotForm } from "./forgot-form";

export const metadata: Metadata = {
  title: "Reset your password · Aakalan",
};

export default function ForgotPasswordPage() {
  return (
    <main className="flex flex-1 flex-col">
      <ForgotForm />
    </main>
  );
}
