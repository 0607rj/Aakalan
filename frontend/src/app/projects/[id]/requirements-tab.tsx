"use client";

import * as React from "react";

import { ErrorNotice, Loading, SectionTitle } from "@/components/status";
import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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
import { Textarea } from "@/components/ui/textarea";
import {
  api,
  errorText,
  type Requirement,
  type RequirementCreate,
} from "@/lib/api/client";
import { useLoad } from "@/lib/use-load";

const CATEGORIES: RequirementCreate["category"][] = [
  "functional",
  "NFR",
  "integration",
  "compliance",
  "commercial",
  "O&M",
  "manpower",
];

const STATUS_VARIANT: Record<string, BadgeProps["variant"]> = {
  confirmed: "success",
  edited: "success",
  extracted: "warning",
  rejected: "destructive",
};

function AddRequirementForm({
  projectId,
  onAdded,
}: {
  projectId: string;
  onAdded: () => void;
}) {
  const [text, setText] = React.useState("");
  const [category, setCategory] =
    React.useState<RequirementCreate["category"]>("functional");
  const [clarity, setClarity] = React.useState(3);
  const [clause, setClause] = React.useState("");
  const [page, setPage] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [saving, setSaving] = React.useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await api.createRequirement(projectId, {
        text,
        category,
        clarity_score: clarity,
        source_refs: [{ clause_ref: clause, page: page ? Number(page) : null }],
      });
      setText("");
      setClause("");
      setPage("");
      onAdded();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <CardContent className="pt-6">
        <form onSubmit={submit} className="grid gap-4 md:grid-cols-6">
          <div className="flex flex-col gap-2 md:col-span-6">
            <Label htmlFor="req-text">Requirement</Label>
            <Textarea
              id="req-text"
              required
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Vendors shall register online and submit empanelment applications…"
            />
          </div>
          <div className="flex flex-col gap-2 md:col-span-2">
            <Label htmlFor="req-category">Category</Label>
            <Select
              id="req-category"
              value={category}
              onChange={(e) =>
                setCategory(e.target.value as RequirementCreate["category"])
              }
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </Select>
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="req-clarity">Clarity (1–5)</Label>
            <Select
              id="req-clarity"
              value={clarity}
              onChange={(e) => setClarity(Number(e.target.value))}
            >
              {[1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </Select>
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="req-clause">Document clause</Label>
            <Input
              id="req-clause"
              required
              value={clause}
              onChange={(e) => setClause(e.target.value)}
              placeholder="4.3.2"
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="req-page">Page</Label>
            <Input
              id="req-page"
              type="number"
              min={1}
              value={page}
              onChange={(e) => setPage(e.target.value)}
            />
          </div>
          <div className="flex items-end">
            <Button
              type="submit"
              disabled={saving || !text.trim() || !clause.trim()}
            >
              {saving ? "Adding…" : "Add requirement"}
            </Button>
          </div>
          <ErrorNotice message={error} className="md:col-span-6" />
        </form>
      </CardContent>
    </Card>
  );
}

export function RequirementsTab({
  projectId,
  canEdit,
}: {
  projectId: string;
  canEdit: boolean;
}) {
  const load = React.useCallback(
    () => api.listRequirements(projectId),
    [projectId],
  );
  const { state, reload, setData } = useLoad(load);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  async function act(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      reload();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  if (state.kind === "loading") return <Loading />;
  if (state.kind === "error") return <ErrorNotice message={state.message} />;
  const requirements: Requirement[] = state.data;
  const pending = requirements.filter((r) => r.status === "extracted").length;

  return (
    <div className="flex flex-col gap-4">
      <SectionTitle
        action={
          canEdit && pending > 0 ? (
            <Button
              size="sm"
              disabled={busy}
              onClick={() =>
                act(async () =>
                  setData(await api.confirmRequirements(projectId)),
                )
              }
            >
              Confirm all ({pending})
            </Button>
          ) : null
        }
      >
        Requirements ({requirements.length})
      </SectionTitle>
      <p className="text-sm text-muted-foreground">
        Every requirement must cite its clause in the requirement document.
        Requirements awaiting review block pricing; rejected ones are excluded.
      </p>
      <ErrorNotice message={error} />

      {requirements.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            No requirements yet. Add them below with their clause and page.
          </CardContent>
        </Card>
      ) : (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Code</TableHead>
                <TableHead>Requirement</TableHead>
                <TableHead>Category</TableHead>
                <TableHead>Clarity</TableHead>
                <TableHead>Clause / page</TableHead>
                <TableHead>Status</TableHead>
                {canEdit ? (
                  <TableHead className="text-right">Actions</TableHead>
                ) : null}
              </TableRow>
            </TableHeader>
            <TableBody>
              {requirements.map((r) => {
                const ref = r.source_refs[0];
                return (
                  <TableRow key={r.id}>
                    <TableCell className="font-mono text-xs">
                      {r.code}
                    </TableCell>
                    <TableCell className="max-w-md text-sm whitespace-normal">
                      {r.text}
                    </TableCell>
                    <TableCell>{r.category}</TableCell>
                    <TableCell>{r.clarity_score}</TableCell>
                    <TableCell className="text-xs whitespace-nowrap">
                      {ref ? (
                        <>
                          §{ref.clause_ref}
                          {ref.page ? `, p. ${ref.page}` : ""}
                        </>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={STATUS_VARIANT[r.status] ?? "outline"}
                        className="capitalize"
                      >
                        {r.status}
                      </Badge>
                    </TableCell>
                    {canEdit ? (
                      <TableCell className="text-right whitespace-nowrap">
                        {r.status === "extracted" || r.status === "rejected" ? (
                          <Button
                            size="sm"
                            variant="ghost"
                            disabled={busy}
                            onClick={() =>
                              act(() =>
                                api.updateRequirement(r.id, {
                                  status: "confirmed",
                                }),
                              )
                            }
                          >
                            Confirm
                          </Button>
                        ) : null}
                        {r.status !== "rejected" ? (
                          <Button
                            size="sm"
                            variant="ghost"
                            disabled={busy}
                            onClick={() =>
                              act(() =>
                                api.updateRequirement(r.id, {
                                  status: "rejected",
                                }),
                              )
                            }
                          >
                            Reject
                          </Button>
                        ) : null}
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-destructive"
                          disabled={busy}
                          onClick={() => {
                            if (window.confirm(`Delete ${r.code}?`)) {
                              void act(() => api.deleteRequirement(r.id));
                            }
                          }}
                        >
                          Delete
                        </Button>
                      </TableCell>
                    ) : null}
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </Card>
      )}

      {canEdit ? (
        <AddRequirementForm projectId={projectId} onAdded={reload} />
      ) : null}
    </div>
  );
}
