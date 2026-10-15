import type { Metadata } from "next";

import { EstimatesHome } from "./estimates-home";

// Auth is client-side (token in localStorage), so there is no server-rendered shell to
// validate for instant navigation.
export const instant = false;

export const metadata: Metadata = {
  title: "Your estimates · Aakalan",
};

export default function ProjectsPage() {
  return <EstimatesHome />;
}
