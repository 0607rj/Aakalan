import { Suspense } from "react";
import type { Metadata } from "next";

import { Loading } from "@/components/status";

import { NewEstimateWizard } from "./wizard";

// Auth is client-side (token in localStorage), so there is no server-rendered shell to
// validate for instant navigation.
export const instant = false;

export const metadata: Metadata = {
  title: "New estimate · Aakalan",
};

export default function NewEstimatePage() {
  // The wizard reads its step from the URL (useSearchParams), which needs a Suspense boundary.
  return (
    <Suspense fallback={<Loading />}>
      <NewEstimateWizard />
    </Suspense>
  );
}
