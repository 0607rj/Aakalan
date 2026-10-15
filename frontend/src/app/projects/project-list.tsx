"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { useCurrentUser } from "@/components/auth-guard";
import { ErrorNotice, Loading } from "@/components/status";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api, errorText, type ProjectCreate } from "@/lib/api/client";
import { formatDate } from "@/lib/format";
import { useLoad } from "@/lib/use-load";

const BUYER_TYPES: ProjectCreate["buyer_type"][] = ["psu", "govt", "private"];

function NewProjectForm({ onCancel }: { onCancel: () => void }) {
  const router = useRouter();
  const [name, setName] = React.useState("");
  const [buyerType, setBuyerType] =
    React.useState<ProjectCreate["buyer_type"]>("psu");
  const [domain, setDomain] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [saving, setSaving] = React.useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const project = await api.createProject({
        name,
        buyer_type: buyerType,
        domain: domain || "general",
        description: "",
      });
      router.push(`/projects/${project.id}?tab=requirements`);
    } catch (err) {
      setError(errorText(err));
      setSaving(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">New project</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={submit} className="grid gap-4 sm:grid-cols-4">
          <div className="flex flex-col gap-2 sm:col-span-2">
            <Label htmlFor="project-name">Name</Label>
            <Input
              id="project-name"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="AI chatbot + empanelment portal for …"
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="project-buyer">Buyer type</Label>
            <Select
              id="project-buyer"
              value={buyerType}
              onChange={(e) =>
                setBuyerType(e.target.value as ProjectCreate["buyer_type"])
              }
            >
              {BUYER_TYPES.map((b) => (
                <option key={b} value={b}>
                  {b.toUpperCase()}
                </option>
              ))}
            </Select>
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="project-domain">Domain</Label>
            <Input
              id="project-domain"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              placeholder="empanelment"
            />
          </div>
          <div className="flex items-center gap-2 sm:col-span-4">
            <Button type="submit" disabled={saving || !name.trim()}>
              {saving ? "Creating…" : "Create project"}
            </Button>
            <Button type="button" variant="ghost" onClick={onCancel}>
              Cancel
            </Button>
          </div>
          <ErrorNotice message={error} className="sm:col-span-4" />
        </form>
      </CardContent>
    </Card>
  );
}

export function ProjectList() {
  const user = useCurrentUser();
  const canEdit = user.role !== "viewer";
  const [creating, setCreating] = React.useState(false);
  const { state } = useLoad(api.listProjects);

  return (
    <div className="flex flex-col gap-4">
      {canEdit ? (
        creating ? (
          <NewProjectForm onCancel={() => setCreating(false)} />
        ) : (
          <div>
            <Button onClick={() => setCreating(true)}>New project</Button>
          </div>
        )
      ) : null}

      {state.kind === "loading" ? <Loading>Loading projects…</Loading> : null}
      {state.kind === "error" ? <ErrorNotice message={state.message} /> : null}
      {state.kind === "ready" && state.data.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-1 py-12 text-center">
            <p className="font-medium">No projects yet</p>
            <p className="text-sm text-muted-foreground">
              Projects you create will appear here.
            </p>
          </CardContent>
        </Card>
      ) : null}
      {state.kind === "ready" && state.data.length > 0 ? (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Buyer</TableHead>
                <TableHead>Domain</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {state.data.map((project) => (
                <TableRow key={project.id}>
                  <TableCell className="font-medium">
                    <Link
                      href={`/projects/${project.id}`}
                      className="text-primary hover:underline"
                    >
                      {project.name}
                    </Link>
                  </TableCell>
                  <TableCell className="uppercase">
                    {project.buyer_type}
                  </TableCell>
                  <TableCell>{project.domain}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className="capitalize">
                      {project.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatDate(project.created_at)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      ) : null}
    </div>
  );
}
