import type { Metadata } from "next";

import { ForgotForm } from "./forgot-form";

export const metadata: Metadata = {
  title: "Reset your password · Aakalan",
};

export default function ForgotPasswordPage() {
  return (
    <main className="glow flex flex-1 items-center justify-center px-4 py-10 sm:py-16">
      <ForgotForm />
    </main>
  );
}
