"use client";

import * as React from "react";

import { ErrorNotice, Loading, SectionTitle } from "@/components/status";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  api,
  errorText,
  type Catalog,
  type CatalogComponent,
  type Component,
  type ComponentIn,
  type Requirement,
} from "@/lib/api/client";
import { formatDateTime } from "@/lib/format";
import { useLoad } from "@/lib/use-load";

const SIZES: ComponentIn["size"][] = ["S", "M", "L"];
const COMPLEXITIES: ComponentIn["complexity"][] = [
  "low",
  "medium",
  "high",
  "very_high",
];

type Row = ComponentIn & { rowId: string };

type Loaded = {
  catalog: Catalog;
  components: Component[];
  requirements: Requirement[];
};

let rowCounter = 0;
function nextRowId(): string {
  rowCounter += 1;
  return `row-${rowCounter}`;
}

function toRow(c: Component): Row {
  return {
    rowId: nextRowId(),
    catalog_key: c.catalog_key,
    label: c.label,
    size: c.size as ComponentIn["size"],
    complexity: c.complexity as ComponentIn["complexity"],
    quantity: c.quantity,
    requirement_ids: c.requirement_ids,
  };
}

function groupByCategory(components: CatalogComponent[]) {
  const groups = new Map<string, CatalogComponent[]>();
  for (const c of components) {
    groups.set(c.category, [...(groups.get(c.category) ?? []), c]);
  }
  return [...groups.entries()];
}

function RequirementPicker({
  requirements,
  selected,
  disabled,
  onChange,
}: {
  requirements: Requirement[];
  selected: string[];
  disabled: boolean;
  onChange: (ids: string[]) => void;
}) {
  const [open, setOpen] = React.useState(false);
  const chosen = requirements.filter((r) => selected.includes(r.id));
  return (
    <div className="flex flex-col gap-1">
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((o) => !o)}
        className="flex min-h-9 flex-wrap items-center gap-1 rounded-md border border-input bg-card px-2 py-1 text-left text-xs disabled:opacity-50"
      >
        {chosen.length === 0 ? (
          <span className="text-muted-foreground">Link requirements…</span>
        ) : (
          chosen.map((r) => (
            <Badge key={r.id} variant="outline" className="font-mono">
              {r.code}
            </Badge>
          ))
        )}
      </button>
      {open && !disabled ? (
        <div className="max-h-48 overflow-y-auto rounded-md border bg-card p-2 shadow-sm">
          {requirements.length === 0 ? (
            <p className="text-xs text-muted-foreground">No requirements.</p>
          ) : (
            requirements.map((r) => (
              <label
                key={r.id}
                className="flex cursor-pointer items-start gap-2 py-1 text-xs"
              >
                <input
                  type="checkbox"
                  className="mt-0.5 accent-primary"
                  checked={selected.includes(r.id)}
                  onChange={(e) =>
                    onChange(
                      e.target.checked
                        ? [...selected, r.id]
                        : selected.filter((id) => id !== r.id),
                    )
                  }
                />
                <span>
                  <span className="font-mono">{r.code}</span>{" "}
                  <span className="text-muted-foreground">
                    {r.text.length > 80 ? `${r.text.slice(0, 80)}…` : r.text}
                  </span>
                </span>
              </label>
            ))
          )}
        </div>
      ) : null}
    </div>
  );
}

function ComponentEditor({
  projectId,
  data,
  canEdit,
  onSaved,
}: {
  projectId: string;
  data: Loaded;
  canEdit: boolean;
  onSaved: (components: Component[]) => void;
}) {
  const [rows, setRows] = React.useState<Row[]>(() =>
    data.components.map(toRow),
  );
  const [dirty, setDirty] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [saving, setSaving] = React.useState(false);
  const catalogByKey = React.useMemo(
    () => new Map(data.catalog.components.map((c) => [c.key, c])),
    [data.catalog],
  );
  const groups = React.useMemo(
    () => groupByCategory(data.catalog.components),
    [data.catalog],
  );
  const priced = data.requirements.filter((r) => r.status !== "rejected");
  const confirmedAt = data.components[0]?.confirmed_at;

  function update(rowId: string, patch: Partial<Row>) {
    setDirty(true);
    setRows((rs) =>
      rs.map((r) => (r.rowId === rowId ? { ...r, ...patch } : r)),
    );
  }

  function addRow() {
    setDirty(true);
    setRows((rs) => [
      ...rs,
      {
        rowId: nextRowId(),
        catalog_key: data.catalog.components[0]?.key ?? "",
        label: null,
        size: "M",
        complexity: "medium",
        quantity: 1,
        requirement_ids: [],
      },
    ]);
  }

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const saved = await api.putComponents(
        projectId,
        rows.map((r) => ({
          catalog_key: r.catalog_key,
          label: r.label,
          size: r.size,
          complexity: r.complexity,
          quantity: r.quantity,
          requirement_ids: r.requirement_ids,
        })),
      );
      setRows(saved.map(toRow));
      setDirty(false);
      onSaved(saved);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <SectionTitle
        action={
          <div className="flex items-center gap-2">
            {!dirty && rows.length > 0 && confirmedAt ? (
              <Badge variant="success">
                Confirmed {formatDateTime(confirmedAt)}
              </Badge>
            ) : null}
            {dirty ? <Badge variant="warning">Unsaved changes</Badge> : null}
          </div>
        }
      >
        Component mapping ({rows.length})
      </SectionTitle>
      <p className="text-sm text-muted-foreground">
        Map requirements to catalog components (catalog {data.catalog.version}
        ). Saving the mapping is your confirmation; estimates can only be
        calculated from a confirmed mapping.
      </p>

      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="min-w-56">Component</TableHead>
              <TableHead>Size</TableHead>
              <TableHead>Complexity</TableHead>
              <TableHead>Qty</TableHead>
              <TableHead className="min-w-48">Requirements</TableHead>
              {canEdit ? <TableHead /> : null}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={6}
                  className="py-8 text-center text-sm text-muted-foreground"
                >
                  No components yet.
                </TableCell>
              </TableRow>
            ) : null}
            {rows.map((row) => {
              const cat = catalogByKey.get(row.catalog_key);
              return (
                <TableRow key={row.rowId} className="align-top">
                  <TableCell className="whitespace-normal">
                    <Select
                      value={row.catalog_key}
                      disabled={!canEdit}
                      onChange={(e) =>
                        update(row.rowId, { catalog_key: e.target.value })
                      }
                    >
                      {groups.map(([category, items]) => (
                        <optgroup key={category} label={category}>
                          {items.map((c) => (
                            <option key={c.key} value={c.key}>
                              {c.name}
                            </option>
                          ))}
                        </optgroup>
                      ))}
                    </Select>
                    {cat ? (
                      <p className="mt-1 text-xs text-muted-foreground">
                        Base effort S/M/L: {cat.base_effort_pd.S}/
                        {cat.base_effort_pd.M}/{cat.base_effort_pd.L} pd
                        {cat.licensable ? " · licensable" : ""}
                        {cat.source === "placeholder" ? " · placeholder" : ""}
                      </p>
                    ) : null}
                  </TableCell>
                  <TableCell>
                    <Select
                      value={row.size}
                      disabled={!canEdit}
                      onChange={(e) =>
                        update(row.rowId, {
                          size: e.target.value as ComponentIn["size"],
                        })
                      }
                    >
                      {SIZES.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </Select>
                  </TableCell>
                  <TableCell>
                    <Select
                      value={row.complexity}
                      disabled={!canEdit}
                      onChange={(e) =>
                        update(row.rowId, {
                          complexity: e.target
                            .value as ComponentIn["complexity"],
                        })
                      }
                    >
                      {COMPLEXITIES.map((c) => (
                        <option key={c} value={c}>
                          {c.replace("_", " ")}
                        </option>
                      ))}
                    </Select>
                  </TableCell>
                  <TableCell>
                    <Input
                      type="number"
                      min={1}
                      className="w-20"
                      value={row.quantity}
                      disabled={!canEdit}
                      onChange={(e) =>
                        update(row.rowId, {
                          quantity: Math.max(1, Number(e.target.value) || 1),
                        })
                      }
                    />
                  </TableCell>
                  <TableCell className="whitespace-normal">
                    <RequirementPicker
                      requirements={priced}
                      selected={row.requirement_ids}
                      disabled={!canEdit}
                      onChange={(ids) =>
                        update(row.rowId, { requirement_ids: ids })
                      }
                    />
                  </TableCell>
                  {canEdit ? (
                    <TableCell>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-destructive"
                        onClick={() => {
                          setDirty(true);
                          setRows((rs) =>
                            rs.filter((r) => r.rowId !== row.rowId),
                          );
                        }}
                      >
                        Remove
                      </Button>
                    </TableCell>
                  ) : null}
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </Card>
      <ErrorNotice message={error} />
      {canEdit ? (
        <div className="flex gap-2">
          <Button variant="outline" onClick={addRow}>
            Add component
          </Button>
          <Button onClick={save} disabled={saving || rows.length === 0}>
            {saving ? "Saving…" : "Save & confirm mapping"}
          </Button>
        </div>
      ) : null}
    </div>
  );
}

export function ComponentsTab({
  projectId,
  canEdit,
}: {
  projectId: string;
  canEdit: boolean;
}) {
  const load = React.useCallback(async (): Promise<Loaded> => {
    const [catalog, components, requirements] = await Promise.all([
      api.getCatalog(),
      api.listComponents(projectId),
      api.listRequirements(projectId),
    ]);
    return { catalog, components, requirements };
  }, [projectId]);
  const { state, setData } = useLoad(load);

  if (state.kind === "loading") return <Loading />;
  if (state.kind === "error") return <ErrorNotice message={state.message} />;
  const data = state.data;

  return (
    <ComponentEditor
      projectId={projectId}
      data={data}
      canEdit={canEdit}
      onSaved={(components) => setData({ ...data, components })}
    />
  );
}
