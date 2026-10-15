import { Suspense } from "react";
import type { Metadata } from "next";

import { Loading } from "@/components/status";

import { EstimateResult } from "./result";

// Auth is client-side (token in localStorage), so there is no server-rendered shell to
// validate for instant navigation.
export const instant = false;

export const metadata: Metadata = {
  title: "Your cost · Aakalan",
};

export default function EstimateResultPage() {
  // The estimate id is request-time data; the result component reads it on the client.
  return (
    <Suspense fallback={<Loading>Loading your estimate…</Loading>}>
      <EstimateResult />
    </Suspense>
  );
}
