"use client";

import * as React from "react";

import { ErrorNotice } from "@/components/status";
import { Button } from "@/components/ui/button";
import {
  ApiError,
  api,
  errorText,
  type TenderDocument,
} from "@/lib/api/client";
import { cn } from "@/lib/utils";

import { DOCUMENT_STEPS, StepIndicator } from "./parts";

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
        <div className="mt-8 size-10 animate-spin rounded-full border-4 border-muted border-t-primary" />
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
      <section className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
            Upload the requirement document
          </h1>
          <p className="mt-1 text-muted-foreground">
            A PDF or Word file (up to 25 MB). Scanned documents can be read once
            the AI key is set up.
          </p>
        </div>

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
            "flex cursor-pointer flex-col items-center gap-3 rounded-xl border border-dashed border-input bg-card px-6 py-16 text-center transition-colors duration-200",
            dragging
              ? "border-primary bg-primary/5"
              : "hover:border-foreground/40 hover:bg-panel-2",
          )}
        >
          <svg
            aria-hidden="true"
            viewBox="0 0 24 24"
            className="size-10 text-primary"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinejoin="round"
          >
            <path d="M6 2.75h8.5L19.25 7.5v13.75H6z" />
            <path d="M14.25 2.75V7.75h5M9 12h7M9 15.5h7M9 19h4" />
          </svg>
          <span className="text-lg font-semibold">
            Drop the file here, or click to choose it
          </span>
          <span className="text-sm text-muted-foreground">PDF or .docx</span>
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
          <Button variant="outline" size="lg" className="h-11" onClick={onBack}>
            Back
          </Button>
        </div>
      </section>
    </div>
  );
}
