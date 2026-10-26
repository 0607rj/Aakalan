import type { Metadata } from "next";

import { SignupForm } from "./signup-form";

export const metadata: Metadata = {
  title: "Create an account · Aakalan",
};

export default function SignupPage() {
  return (
    <main className="flex flex-1 flex-col">
      <SignupForm />
    </main>
  );
}
