import type { Metadata } from "next";

import { ProjectList } from "./project-list";

// Auth is client-side (token in localStorage), so there is no server-rendered shell to
// validate for instant navigation.
export const instant = false;

export const metadata: Metadata = {
  title: "Projects · Aakalan",
};

export default function ProjectsPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Projects</h1>
        <p className="text-sm text-muted-foreground">
          Tenders you are estimating for your organisation.
        </p>
      </div>
      <ProjectList />
    </div>
  );
}
