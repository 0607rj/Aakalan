import type { Metadata } from "next";

import { NewEstimateWizard } from "./wizard";

// Auth is client-side (token in localStorage), so there is no server-rendered shell to
// validate for instant navigation.
export const instant = false;

export const metadata: Metadata = {
  title: "New estimate · Aakalan",
};

export default function NewEstimatePage() {
  return <NewEstimateWizard />;
}
