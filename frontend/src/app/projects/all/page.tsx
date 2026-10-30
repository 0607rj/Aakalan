import { AppHero } from "@/components/app-hero";
import type { Metadata } from "next";
import Link from "next/link";

import { ProjectList } from "../project-list";

// Auth is client-side (token in localStorage), so there is no server-rendered shell to
// validate for instant navigation.
export const instant = false;

export const metadata: Metadata = {
  title: "Detailed projects · Aakalan",
};

export default function AllProjectsPage() {
  return (
    <div className="flex flex-col gap-6">
      <AppHero>
        <Link
          href="/projects"
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          ← Back to your estimates
        </Link>
        <h1 className="font-display mt-4 text-[clamp(2.2rem,5vw,3.25rem)] leading-[1]">
          Detailed projects
        </h1>
        <p className="mt-3 max-w-xl text-muted-foreground">
          The expert workspace: requirements, questionnaire, components and the
          full cost breakdown with traces.
        </p>
      </AppHero>
      <ProjectList />
    </div>
  );
}
