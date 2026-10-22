import type { Metadata } from "next";

import { SignupForm } from "./signup-form";

export const metadata: Metadata = {
  title: "Create an account · Aakalan",
};

export default function SignupPage() {
  return (
    <main className="flex flex-1 items-center justify-center px-4 py-20">
      <SignupForm />
    </main>
  );
}
