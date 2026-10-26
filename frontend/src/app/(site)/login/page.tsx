import type { Metadata } from "next";

import { LoginForm } from "./login-form";

export const metadata: Metadata = {
  title: "Sign in · Aakalan",
};

export default function LoginPage() {
  return (
    <main className="flex flex-1 flex-col">
      <LoginForm />
    </main>
  );
}
