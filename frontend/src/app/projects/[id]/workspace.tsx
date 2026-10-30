"use client";

import { AppHero } from "@/components/app-hero";
import * as React from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";

import { useCurrentUser } from "@/components/auth-guard";
import { ErrorNotice, Loading } from "@/components/status";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api/client";
import { useLoad } from "@/lib/use-load";
import { cn } from "@/lib/utils";

import { ComponentsTab } from "./components-tab";
import { EstimateTab } from "./estimate-tab";
import { QuestionnaireTab } from "./questionnaire-tab";
import { RequirementsTab } from "./requirements-tab";

const TABS = [
  { key: "requirements", label: "Requirements" },
  { key: "questionnaire", label: "Questionnaire" },
  { key: "components", label: "Components" },
  { key: "estimate", label: "Estimate" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

function isTab(value: string | null): value is TabKey {
  return TABS.some((t) => t.key === value);
}

export function ProjectWorkspace() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const projectId = params.id;
  const tabParam = searchParams.get("tab");
  const tab: TabKey = isTab(tabParam) ? tabParam : "requirements";
  const user = useCurrentUser();
  const canEdit = user.role !== "viewer";

  const loadProject = React.useCallback(
    () => api.getProject(projectId),
    [projectId],
  );
  const { state } = useLoad(loadProject);

  if (state.kind === "loading") return <Loading>Loading project…</Loading>;
  if (state.kind === "error") return <ErrorNotice message={state.message} />;
  const project = state.data;

  return (
    <div className="flex flex-col gap-6">
      <AppHero>
        <div className="flex flex-col gap-3">
          <Link
            href="/projects/all"
            className="text-sm text-muted-foreground hover:underline"
          >
            ← Detailed projects
          </Link>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="font-display text-[clamp(2rem,4.5vw,3rem)] leading-[1.05]">
              {project.name}
            </h1>
            <Badge variant="outline" className="uppercase">
              {project.buyer_type}
            </Badge>
            <Badge variant="outline">{project.domain}</Badge>
            <Badge variant="secondary" className="capitalize">
              {project.status}
            </Badge>
          </div>
          {project.description ? (
            <p className="text-sm text-muted-foreground">
              {project.description}
            </p>
          ) : null}
        </div>
      </AppHero>

      <nav className="flex gap-1 border-b" aria-label="Project sections">
        {TABS.map((t) => (
          <Link
            key={t.key}
            href={`/projects/${projectId}?tab=${t.key}`}
            scroll={false}
            aria-current={tab === t.key ? "page" : undefined}
            className={cn(
              "-mb-px border-b-2 px-4 py-2 text-sm font-medium transition-colors",
              tab === t.key
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground",
            )}
          >
            {t.label}
          </Link>
        ))}
      </nav>

      {tab === "requirements" ? (
        <RequirementsTab projectId={projectId} canEdit={canEdit} />
      ) : null}
      {tab === "questionnaire" ? (
        <QuestionnaireTab projectId={projectId} canEdit={canEdit} />
      ) : null}
      {tab === "components" ? (
        <ComponentsTab projectId={projectId} canEdit={canEdit} />
      ) : null}
      {tab === "estimate" ? (
        <EstimateTab projectId={projectId} canEdit={canEdit} />
      ) : null}
    </div>
  );
}
