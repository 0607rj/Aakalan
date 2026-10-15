"use client";

import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api, type ProjectSummary } from "@/lib/api/client";

type ListState =
  { kind: "loading" } | { kind: "loaded"; projects: ProjectSummary[] };

const dateFormat = new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" });

export function ProjectList() {
  const [state, setState] = React.useState<ListState>({ kind: "loading" });

  React.useEffect(() => {
    let cancelled = false;
    api
      .listProjects()
      .then((projects) => {
        if (!cancelled) setState({ kind: "loaded", projects });
      })
      .catch(() => {
        // The projects endpoint may not exist yet (M0); treat as empty.
        if (!cancelled) setState({ kind: "loaded", projects: [] });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (state.kind === "loading") {
    return <p className="text-sm text-muted-foreground">Loading projects…</p>;
  }

  if (state.projects.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center gap-1 py-12 text-center">
          <p className="font-medium">No projects yet</p>
          <p className="text-sm text-muted-foreground">
            Projects you create will appear here.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Buyer</TableHead>
            <TableHead>Domain</TableHead>
            <TableHead>Mode</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Created</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {state.projects.map((project) => (
            <TableRow key={project.id}>
              <TableCell className="font-medium">{project.name}</TableCell>
              <TableCell className="uppercase">{project.buyer_type}</TableCell>
              <TableCell>{project.domain}</TableCell>
              <TableCell className="capitalize">{project.mode}</TableCell>
              <TableCell>
                <Badge variant="outline" className="capitalize">
                  {project.status}
                </Badge>
              </TableCell>
              <TableCell className="text-muted-foreground">
                {dateFormat.format(new Date(project.created_at))}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  );
}
