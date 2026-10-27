"use client";

import * as React from "react";

import {
  FileArrowUpIcon,
  ListChecksIcon,
  LockKeyIcon,
  MagnifyingGlassIcon,
  ReceiptIcon,
} from "@phosphor-icons/react/dist/ssr";

import {
  IconTile,
  type IconType,
  type Tone,
} from "@/components/site/illustrations";
import { ErrorNotice } from "@/components/status";
import { Button } from "@/components/ui/button";
import {
  ApiError,
  api,
  errorText,
  type TenderDocument,
} from "@/lib/api/client";
import { cn } from "@/lib/utils";

import { DOCUMENT_STEPS, StepHeader, StepIndicator } from "./parts";

const NEXT: { icon: IconType; tone: Tone; text: string }[] = [
  {
    icon: MagnifyingGlassIcon,
    tone: "plain",
    text: "We read the document, usually in a minute or two.",
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

function friendlyError(error: unknown): string {
  if (error instanceof ApiError && error.status === 413) {
    return "This file is too large. Please upload a file smaller than 25 MB — the main requirement document is usually enough.";
  }
  if (error instanceof TypeError) {
    return "We could not reach the server. Please check that Aakalan is running and try again.";
  }
  return errorText(error);
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
  const [uploading, setUploading] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  async function upload(file: File) {
    setError(null);
    setUploading(file.name);
    try {
      onUploaded(await api.uploadDocument(file));
    } catch (e) {
      setError(friendlyError(e));
      setUploading(null);
    }
  }

  function pick(files: FileList | null) {
    const file = files?.[0];
    if (file) void upload(file);
  }

  if (uploading) {
    return (
      <div className="flex flex-col items-center gap-4 py-24 text-center">
        <StepIndicator labels={DOCUMENT_STEPS} current={1} />
        <IconTile icon={MagnifyingGlassIcon} size="lg" className="mt-8" />
        <div className="h-1.5 w-64 overflow-hidden rounded-full bg-tape-soft">
          <div className="h-full w-1/3 animate-[measure_1.4s_cubic-bezier(0.65,0,0.35,1)_infinite] rounded-full bg-primary/80" />
        </div>
        <p className="text-lg font-medium">Reading your document…</p>
        <p className="max-w-md text-sm text-muted-foreground">
          This can take a minute or two for long documents. Please keep this
          page open.
        </p>
        <p className="text-sm text-muted-foreground">{uploading}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8">
      <StepIndicator labels={DOCUMENT_STEPS} current={1} />
      <StepHeader
        eyebrow="New estimate"
        title="Upload the requirement document"
      >
        We read it, list what it asks for with page numbers, and you check the
        list before any price is worked out.
      </StepHeader>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="flex flex-col gap-4">
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
              pick(e.dataTransfer.files);
            }}
            className={cn(
              "slab group flex cursor-pointer flex-col items-center gap-4 border-dashed px-6 py-14 text-center transition-colors duration-200 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
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
              {dragging ? "Drop it here" : "Drop the file here"}
            </span>
            <span className="inline-flex h-10 items-center rounded-lg bg-primary px-5 text-sm font-semibold text-primary-foreground">
              Choose a file
            </span>
            <span className="text-sm text-muted-foreground">
              PDF or Word, up to 25 MB
            </span>
            <input
              ref={inputRef}
              type="file"
              accept={ACCEPT}
              className="hidden"
              onChange={(e) => {
                pick(e.target.files);
                e.target.value = "";
              }}
            />
          </div>

          {error ? (
            <div className="flex flex-col gap-3">
              <ErrorNotice message={error} />
              <span className="text-sm text-muted-foreground">
                Choose another file above to try again.
              </span>
            </div>
          ) : null}

          <div>
            <Button variant="ghost" size="lg" className="h-11" onClick={onBack}>
              ← Back
            </Button>
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
            Scanned documents can be read once the AI key is set up. Your file
            is sent only to the AI provider you configured.
          </p>
        </aside>
      </div>
    </div>
  );
}
