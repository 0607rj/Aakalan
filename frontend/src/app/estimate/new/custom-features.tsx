"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import type {
  CustomFeature,
  CustomFeatureType,
  Evidence,
  FoundOtherFeature,
  Researched,
  Size,
} from "@/lib/api/client";
import { cn } from "@/lib/utils";

import { Citation, FeatureCard } from "./parts";

/** A feature outside the ready-made list, as the user is editing it. */
export interface CustomItem {
  id: string;
  name: string;
  category: string;
  size: Size;
  /** Index into the document's other_features (so the backend can cite the page). */
  foundIndex: number | null;
  description: string;
  evidence: Evidence[];
  included: boolean;
  /** A feature researched before: priced by its saved block, not searched again. */
  catalogKey?: string | null;
  /** Found in the user's description (not in our list): the words it came from. */
  fromDescription?: string;
  /** How many modules of this size it is (a large sub-system can be several). */
  units?: number;
}

const SIZES: { value: Size; label: string }[] = [
  { value: "S", label: "Small effort" },
  { value: "M", label: "Medium effort" },
  { value: "L", label: "Large effort" },
];

const MAX_NAME = 200;

function asSize(value: string): Size {
  return value === "S" || value === "L" ? value : "M";
}

/** Editable items from the document's other features, as the backend pre-fills them
 * (`custom`, each pointing at its finding), with the finding's words and pages. */
export function itemsFromDocument(
  custom: CustomFeature[],
  found: FoundOtherFeature[],
): CustomItem[] {
  return custom.map((c, i) => {
    const f = c.found_index != null ? found[c.found_index] : undefined;
    return {
      id: `found-${c.found_index ?? i}`,
      name: c.name,
      category: c.category,
      size: c.size,
      foundIndex: c.found_index ?? null,
      description: f?.description ?? "",
      evidence: f?.evidence ?? [],
      included: true,
      units: c.units,
    };
  });
}

/** Editable items from a saved template's extra features. */
export function itemsFromTemplate(saved: CustomFeature[]): CustomItem[] {
  return saved.map((f, i) => ({
    id: `template-${i}`,
    name: f.name,
    category: f.category,
    size: asSize(f.size),
    foundIndex: null,
    description: "",
    evidence: [],
    included: true,
    catalogKey: f.catalog_key ?? null,
    units: f.units,
  }));
}

/**
 * Features the company had researched before, under their section (web, mobile, ...). Ticking
 * one adds it to "Features you added" with its saved block, so it is not searched again.
 */
export function ResearchedFeatures({
  researched,
  items,
  onChange,
}: {
  researched: Researched[];
  items: CustomItem[];
  onChange: (items: CustomItem[]) => void;
}) {
  if (researched.length === 0) return null;
  const ticked = new Set(items.map((i) => i.catalogKey).filter(Boolean));
  const sections = [...new Set(researched.map((r) => r.section_label))];

  function toggle(r: Researched) {
    if (ticked.has(r.catalog_key)) {
      onChange(items.filter((i) => i.catalogKey !== r.catalog_key));
      return;
    }
    onChange([
      ...items,
      {
        id: `researched-${r.catalog_key}`,
        name: r.name,
        category: r.category,
        size: "M",
        foundIndex: null,
        description: "",
        evidence: [],
        included: true,
        catalogKey: r.catalog_key,
      },
    ]);
  }

  return (
    <section className="flex flex-col gap-3">
      <div>
        <h2 className="text-lg font-semibold">Researched before</h2>
        <p className="text-sm text-muted-foreground">
          Features that were not in the list, researched earlier by you or other
          users. They are priced from the saved research, with no new search.
        </p>
      </div>
      {sections.map((label) => (
        <div key={label} className="flex flex-col gap-2">
          <h3 className="text-sm font-medium text-muted-foreground">{label}</h3>
          <div className="grid gap-3 sm:grid-cols-2">
            {researched
              .filter((r) => r.section_label === label)
              .map((r) => (
                <FeatureCard
                  key={r.catalog_key}
                  label={r.name}
                  hint="Researched before"
                  checked={ticked.has(r.catalog_key)}
                  onToggle={() => toggle(r)}
                />
              ))}
          </div>
        </div>
      ))}
    </section>
  );
}

/** The items to send to the API (only included ones with a name). */
export function toCustomFeatures(items: CustomItem[]): CustomFeature[] {
  return items
    .filter((i) => i.included && i.name.trim() !== "")
    .map((i) => ({
      name: i.name.trim().slice(0, MAX_NAME),
      category: i.category,
      size: i.size,
      found_index: i.foundIndex,
      catalog_key: i.catalogKey ?? null,
      units: i.units ?? 1,
    }));
}

const MAX_UNITS = 100; // as the quick config's sizing.max_units

function TypeAndSize({
  item,
  types,
  onChange,
}: {
  item: CustomItem;
  types: CustomFeatureType[];
  onChange: (patch: Partial<CustomItem>) => void;
}) {
  return (
    <div className="grid gap-2 sm:grid-cols-[1fr_1fr_7rem]">
      <Select
        aria-label="Type"
        value={item.category}
        onChange={(e) => onChange({ category: e.target.value })}
      >
        {types.map((t) => (
          <option key={t.key} value={t.key}>
            {t.label}
          </option>
        ))}
      </Select>
      <Select
        aria-label="Size"
        value={item.size}
        onChange={(e) => onChange({ size: asSize(e.target.value) })}
      >
        {SIZES.map((s) => (
          <option key={s.value} value={s.value}>
            {s.label}
          </option>
        ))}
      </Select>
      <Input
        aria-label="How many modules of this size"
        title="How many modules of this size (a large sub-system can be several)"
        type="number"
        min={1}
        max={MAX_UNITS}
        value={item.units ?? 1}
        onChange={(e) =>
          onChange({
            units: Math.min(
              MAX_UNITS,
              Math.max(1, Math.round(Number(e.target.value) || 1)),
            ),
          })
        }
      />
    </div>
  );
}

function ItemCard({
  item,
  types,
  approximatePages,
  onChange,
  onRemove,
}: {
  item: CustomItem;
  types: CustomFeatureType[];
  approximatePages: boolean;
  onChange: (patch: Partial<CustomItem>) => void;
  onRemove?: () => void;
}) {
  const fromDocument = item.foundIndex !== null;
  return (
    <div
      className={cn(
        "flex flex-col gap-3 rounded-xl border bg-card p-4 transition-colors",
        item.included
          ? "border-primary bg-primary/5 ring-1 ring-primary"
          : "opacity-70",
      )}
    >
      <div className="flex items-start gap-3">
        {fromDocument ? (
          <input
            type="checkbox"
            aria-label={`Include ${item.name}`}
            checked={item.included}
            onChange={() => onChange({ included: !item.included })}
            className="mt-3 size-4 accent-primary"
          />
        ) : null}
        <div className="flex flex-1 flex-col gap-2">
          <Input
            aria-label="Feature name"
            value={item.name}
            maxLength={MAX_NAME}
            onChange={(e) => onChange({ name: e.target.value })}
            className="h-10 font-semibold"
          />
          {item.description ? (
            <span className="text-sm text-muted-foreground">
              {item.description}
            </span>
          ) : null}
          {item.included ? (
            <TypeAndSize item={item} types={types} onChange={onChange} />
          ) : null}
          {fromDocument ? (
            <>
              <span className="text-xs text-muted-foreground">
                Not in our list: priced as its own feature
              </span>
              <Citation
                evidence={item.evidence}
                approximatePages={approximatePages}
              />
            </>
          ) : (
            <span className="text-xs text-muted-foreground">Added by you</span>
          )}
        </div>
        {onRemove ? (
          <Button
            variant="ghost"
            size="sm"
            onClick={onRemove}
            aria-label={`Remove ${item.name}`}
          >
            Remove
          </Button>
        ) : null}
      </div>
    </div>
  );
}

function AddFeatureForm({
  types,
  onAdd,
}: {
  types: CustomFeatureType[];
  onAdd: (item: CustomItem) => void;
}) {
  const [open, setOpen] = React.useState(false);
  const [name, setName] = React.useState("");
  const [category, setCategory] = React.useState(types[0]?.key ?? "module");
  const [size, setSize] = React.useState<Size>("M");
  const counter = React.useRef(0);

  function add() {
    if (name.trim() === "") return;
    counter.current += 1;
    onAdd({
      id: `user-${Date.now()}-${counter.current}`,
      name: name.trim(),
      category,
      size,
      foundIndex: null,
      description: "",
      evidence: [],
      included: true,
    });
    setName("");
    setSize("M");
  }

  if (!open) {
    return (
      <div className="flex flex-col gap-1">
        <Button
          variant="outline"
          className="self-start"
          onClick={() => setOpen(true)}
        >
          + Add a feature
        </Button>
        <span className="text-sm text-muted-foreground">
          Something it needs that isn&apos;t listed above? Add it here so it is
          priced too.
        </span>
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-dashed bg-card p-4">
      <span className="text-sm text-muted-foreground">
        Something it needs that isn&apos;t listed above? Add it here so it is
        priced too.
      </span>
      <div className="grid gap-3 md:grid-cols-[2fr_1fr_1fr_auto] md:items-end">
        <div className="flex flex-col gap-1">
          <Label htmlFor="new-feature-name">Feature name</Label>
          <Input
            id="new-feature-name"
            value={name}
            maxLength={MAX_NAME}
            placeholder="e.g. Vehicle tracking on a map"
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") add();
            }}
          />
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="new-feature-type">Type</Label>
          <Select
            id="new-feature-type"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            {types.map((t) => (
              <option key={t.key} value={t.key}>
                {t.label}
              </option>
            ))}
          </Select>
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="new-feature-size">Size</Label>
          <Select
            id="new-feature-size"
            value={size}
            onChange={(e) => setSize(asSize(e.target.value))}
          >
            {SIZES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </Select>
        </div>
        <div className="flex gap-2">
          <Button onClick={add} disabled={name.trim() === ""}>
            Add
          </Button>
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Close
          </Button>
        </div>
      </div>
    </div>
  );
}

/**
 * Features outside the ready-made list that the user adds (the document's own are shown with
 * what was found, `FoundOtherFeatures`). All of them are priced by type and size.
 */
export function CustomFeaturesSection({
  items,
  onChange,
  types,
  approximatePages = false,
}: {
  items: CustomItem[];
  onChange: (items: CustomItem[]) => void;
  types: CustomFeatureType[];
  approximatePages?: boolean;
}) {
  const found = items.filter((i) => i.foundIndex !== null);
  const added = items.filter((i) => i.foundIndex === null);

  function patch(id: string, change: Partial<CustomItem>) {
    onChange(items.map((i) => (i.id === id ? { ...i, ...change } : i)));
  }
  function remove(id: string) {
    onChange(items.filter((i) => i.id !== id));
  }

  return (
    <section className="flex flex-col gap-4">
      {found.length + added.length > 0 ? (
        <div className="grid gap-3 lg:grid-cols-2">
          {[...found, ...added].map((item) => (
            <ItemCard
              key={item.id}
              item={item}
              types={types}
              approximatePages={approximatePages}
              onChange={(change) => patch(item.id, change)}
              onRemove={
                item.foundIndex === null ? () => remove(item.id) : undefined
              }
            />
          ))}
        </div>
      ) : null}
      <AddFeatureForm
        types={types}
        onAdd={(item) => onChange([...items, item])}
      />
    </section>
  );
}

/** Features the document asks for that are not in our list: priced as their own, editable. */
export function FoundOtherFeatures({
  items,
  onChange,
  types,
  approximatePages,
}: {
  items: CustomItem[];
  onChange: React.Dispatch<React.SetStateAction<CustomItem[]>>;
  types: CustomFeatureType[];
  approximatePages: boolean;
}) {
  return items
    .filter((i) => i.foundIndex !== null)
    .map((item) => (
      <ItemCard
        key={item.id}
        item={item}
        types={types}
        approximatePages={approximatePages}
        onChange={(change) =>
          onChange((now) =>
            now.map((i) => (i.id === item.id ? { ...i, ...change } : i)),
          )
        }
      />
    ));
}
