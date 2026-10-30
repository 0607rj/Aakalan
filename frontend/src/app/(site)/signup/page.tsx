import { Suspense } from "react";
import type { Metadata } from "next";

import { SignupForm, SignupFormFromLink } from "./signup-form";

export const metadata: Metadata = {
  title: "Create an account · Aakalan",
};

/** The form prerenders empty; `?email=` from the footer's email box fills it in the browser. */
export default function SignupPage() {
  return (
    <main className="flex flex-1 flex-col">
      <Suspense fallback={<SignupForm />}>
        <SignupFormFromLink />
      </Suspense>
    </main>
  );
}
