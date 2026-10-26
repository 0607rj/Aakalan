import type { Metadata } from "next";

import { LoginForm } from "./login-form";

export const metadata: Metadata = {
  title: "Sign in · Aakalan",
};

export default function LoginPage() {
  return (
    <main className="glow flex flex-1 items-center justify-center px-4 py-10 sm:py-16">
      <LoginForm />
    </main>
  );
}
