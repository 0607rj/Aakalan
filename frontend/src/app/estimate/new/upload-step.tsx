"use client";

import * as React from "react";

import {
  FileArrowUpIcon,
  FileTextIcon,
  ListChecksIcon,
  LockKeyIcon,
  MagnifyingGlassIcon,
  ReceiptIcon,
  XIcon,
} from "@phosphor-icons/react/dist/ssr";

import {
  IconTile,
  type IconType,
  type Tone,
} from "@/components/site/illustrations";
import { ErrorNotice } from "@/components/status";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import {
  ApiError,
  api,
  errorText,
  type DocumentKind,
  type TenderDocument,
} from "@/lib/api/client";
import { cn } from "@/lib/utils";

import { DOCUMENT_STEPS, StepHeader, StepIndicator } from "./parts";
import { ReadingDocument } from "./reading-document";

const NEXT: { icon: IconType; tone: Tone; text: string }[] = [
  {
    icon: MagnifyingGlassIcon,
    tone: "plain",
    text: "We read each file, usually in a minute or two.",
  },
  {
    icon: ListChecksIcon,
    tone: "tape",
    text: "You check what we found and answer only what it does not say.",
  },
  {
    icon: ReceiptIcon,
    tone: "ai",
    text: "You get the total cost with a likely range and where the money goes.",
  },
];

const ACCEPT =
  ".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document";

/** The server's `project_max_documents` (OPEN_QUESTIONS 225). */
const MAX_FILES = 5;

/** What each file is, in the user's words. An update or answers replace what the main
 * document says; the order here is the order they are read in. */
const KINDS: { value: DocumentKind; label: string }[] = [
  { value: "rfp", label: "Main document" },
  { value: "annexure", label: "Extra document (annexure)" },
  { value: "corrigendum", label: "Update to the document" },
  { value: "prebid_reply", label: "Answers to questions" },
];
const ORDER: Record<DocumentKind, number> = {
  rfp: 0,
  annexure: 1,
  corrigendum: 2,
  prebid_reply: 3,
};

/** A first guess from the file name; the user can change it. */
function guessKind(name: string): DocumentKind {
  const n = name.toLowerCase();
  if (/corrigend|addend|amend|revis|update/.test(n)) return "corrigendum";
  if (/pre.?bid|clarific|repl|response|quer|faq|answer/.test(n))
    return "prebid_reply";
  return "annexure";
}

type Picked = { file: File; kind: DocumentKind };

function friendlyError(error: unknown): string {
  if (error instanceof ApiError && error.status === 413) {
    return "This file is too large. Please upload a file smaller than 25 MB.";
  }
  if (error instanceof TypeError) {
    return "We could not reach the server. Please check that Aakalan is running and try again.";
  }
  return errorText(error);
}

function sizeText(bytes: number): string {
  return bytes >= 1024 * 1024
    ? `${(bytes / 1024 / 1024).toFixed(1)} MB`
    : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

export function UploadStep({
  onUploaded,
  onBack,
}: {
  onUploaded: (doc: TenderDocument) => void;
  onBack: () => void;
}) {
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = React.useState(false);
  const [picked, setPicked] = React.useState<Picked[]>([]);
  const [reading, setReading] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  // the main document is read but a later file failed: go on without it, or try again
  const [partial, setPartial] = React.useState<TenderDocument | null>(null);

  function add(list: FileList | null) {
    if (!list) return;
    setError(null);
    setPicked((current) => {
      const next = [...current];
      for (const file of Array.from(list)) {
        if (
          next.some(
            (p) => p.file.name === file.name && p.file.size === file.size,
          )
        )
          continue;
        if (next.length >= MAX_FILES) {
          setError(`At most ${MAX_FILES} files for one project.`);
          break;
        }
        next.push({
          file,
          kind: next.some((p) => p.kind === "rfp")
            ? guessKind(file.name)
            : "rfp",
        });
      }
      return next;
    });
  }

  function setKind(index: number, kind: DocumentKind) {
    setPicked((current) =>
      current.map((p, i) => {
        if (i === index) return { ...p, kind };
        // one main document: the one chosen now; the old one becomes an extra document
        if (kind === "rfp" && p.kind === "rfp")
          return { ...p, kind: "annexure" };
        return p;
      }),
    );
  }

  function remove(index: number) {
    setPicked((current) => {
      const next = current.filter((_, i) => i !== index);
      if (next.length > 0 && !next.some((p) => p.kind === "rfp"))
        next[0] = { ...next[0], kind: "rfp" };
      return next;
    });
  }

  async function read() {
    setError(null);
    const files = [...picked].sort((a, b) => ORDER[a.kind] - ORDER[b.kind]);
    const count = files.length;
    const label = (i: number) =>
      count === 1
        ? files[i].file.name
        : `${files[i].file.name} · file ${i + 1} of ${count}`;
    let main = partial;
    try {
      if (main === null) {
        setReading(label(0));
        main = await api.uploadDocument(files[0].file);
      }
      for (let i = 1; i < count; i++) {
        setReading(label(i));
        try {
          await api.uploadDocument(files[i].file, {
            projectId: main.project_id,
            kind: files[i].kind,
          });
        } catch (e) {
          setPartial(main);
          setPicked(files.slice(i));
          setError(`${files[i].file.name}: ${friendlyError(e)}`);
          setReading(null);
          return;
        }
      }
      onUploaded(main);
    } catch (e) {
      setError(friendlyError(e));
      setReading(null);
    }
  }

  if (reading) return <ReadingDocument fileName={reading} />;

  const many = picked.length > 1 || partial !== null;

  return (
    <div className="flex flex-col gap-8">
      <StepIndicator labels={DOCUMENT_STEPS} current={1} />
      <StepHeader
        eyebrow="New estimate"
        title="Upload the requirement document"
      >
        We read it, list what it asks for with page numbers, and you check the
        list before any price is worked out. Have annexures, an update or
        answers to questions too? Add them here, up to {MAX_FILES} files.
      </StepHeader>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="flex flex-col gap-4">
          {partial === null ? (
            <div
              role="button"
              tabIndex={0}
              onClick={() => inputRef.current?.click()}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  inputRef.current?.click();
                }
              }}
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragging(false);
                add(e.dataTransfer.files);
              }}
              className={cn(
                "slab group flex cursor-pointer flex-col items-center gap-4 border-dashed px-6 text-center transition-colors duration-200 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
                picked.length > 0 ? "py-8" : "py-14",
                dragging
                  ? "border-primary bg-tape-soft/60"
                  : "hover:border-primary/50",
              )}
            >
              <IconTile
                icon={FileArrowUpIcon}
                size="lg"
                className="transition-transform group-hover:-translate-y-0.5"
              />
              <span className="text-lg font-semibold">
                {dragging
                  ? "Drop them here"
                  : picked.length > 0
                    ? "Add another file"
                    : "Drop the files here"}
              </span>
              <span className="inline-flex h-10 items-center rounded-lg bg-primary px-5 text-sm font-semibold text-primary-foreground">
                {picked.length > 0 ? "Choose more" : "Choose files"}
              </span>
              <span className="text-sm text-muted-foreground">
                PDF or Word, up to 25 MB each
              </span>
              <input
                ref={inputRef}
                type="file"
                multiple
                accept={ACCEPT}
                className="hidden"
                onChange={(e) => {
                  add(e.target.files);
                  e.target.value = "";
                }}
              />
            </div>
          ) : null}

          {picked.length > 0 ? (
            <ul className="flex flex-col gap-2">
              {picked.map((p, i) => (
                <li
                  key={`${p.file.name}-${p.file.size}`}
                  className="flex flex-wrap items-center gap-3 rounded-xl border bg-card px-4 py-3"
                >
                  <FileTextIcon
                    size={20}
                    weight="duotone"
                    aria-hidden="true"
                    className="shrink-0 text-primary"
                  />
                  <span className="flex min-w-0 flex-1 flex-col">
                    <span className="truncate font-medium">{p.file.name}</span>
                    <span className="text-xs text-muted-foreground">
                      {sizeText(p.file.size)}
                    </span>
                  </span>
                  {many ? (
                    <Select
                      aria-label={`What ${p.file.name} is`}
                      className="w-auto"
                      value={p.kind}
                      disabled={partial !== null}
                      onChange={(e) =>
                        setKind(i, e.target.value as DocumentKind)
                      }
                    >
                      {KINDS.filter(
                        (k) => partial === null || k.value !== "rfp",
                      ).map((k) => (
                        <option key={k.value} value={k.value}>
                          {k.label}
                        </option>
                      ))}
                    </Select>
                  ) : null}
                  {partial === null ? (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="px-2"
                      aria-label={`Remove ${p.file.name}`}
                      onClick={() => remove(i)}
                    >
                      <XIcon size={16} aria-hidden="true" />
                    </Button>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : null}

          {many && partial === null ? (
            <p className="text-sm text-muted-foreground">
              Every file is read, and each finding keeps its file and page. An
              update or answers to questions replace what the main document
              says. The same item in two files is counted once.
            </p>
          ) : null}

          {error ? <ErrorNotice message={error} /> : null}

          <div className="flex flex-wrap gap-3">
            <Button variant="ghost" size="lg" className="h-11" onClick={onBack}>
              ← Back
            </Button>
            {picked.length > 0 ? (
              <Button size="lg" className="h-11" onClick={() => void read()}>
                {partial !== null
                  ? "Try again"
                  : picked.length === 1
                    ? "Read the document"
                    : `Read ${picked.length} files`}
              </Button>
            ) : null}
            {partial !== null ? (
              <Button
                variant="outline"
                size="lg"
                className="h-11"
                onClick={() => onUploaded(partial)}
              >
                Continue without{" "}
                {picked.length === 1 ? "this file" : "these files"}
              </Button>
            ) : null}
          </div>
        </div>

        <aside className="flex flex-col gap-4 rounded-2xl border bg-panel-2 p-5">
          <h2 className="font-semibold">What happens next</h2>
          <ol className="flex flex-col gap-4 text-sm">
            {NEXT.map((step) => (
              <li key={step.text} className="flex items-center gap-3">
                <IconTile icon={step.icon} tone={step.tone} size="sm" />
                <span className="text-muted-foreground">{step.text}</span>
              </li>
            ))}
          </ol>
          <p className="flex gap-2 border-t pt-4 text-xs text-muted-foreground">
            <LockKeyIcon
              size={16}
              weight="duotone"
              aria-hidden="true"
              className="shrink-0 text-ai"
            />
            Scanned documents can be read once the AI key is set up. Your files
            are sent only to the AI provider you configured.
          </p>
        </aside>
      </div>
    </div>
  );
}
