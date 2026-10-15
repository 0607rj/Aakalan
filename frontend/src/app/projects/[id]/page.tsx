import { Suspense } from "react";
import type { Metadata } from "next";

import { Loading } from "@/components/status";

import { ProjectWorkspace } from "./workspace";

// Auth is client-side (token in localStorage), so there is no server-rendered shell to
// validate for instant navigation.
export const instant = false;

export const metadata: Metadata = {
  title: "Project · Aakalan",
};

export default function ProjectPage() {
  // The project id and ?tab= are request-time data; the workspace reads them on the client.
  return (
    <Suspense fallback={<Loading>Loading project…</Loading>}>
      <ProjectWorkspace />
    </Suspense>
  );
}
