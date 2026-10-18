"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";
import { api, type PrebidQuery, type UnclearPoint } from "@/lib/api/client";
import { useLoad } from "@/lib/use-load";

const COPIED_MS = 2000;

function where(query: PrebidQuery, approximatePages: boolean): string | null {
  const parts = [
    query.clause_ref ? `Clause ${query.clause_ref}` : null,
    query.page !== null
      ? `${approximatePages ? "≈ page" : "Page"} ${query.page}`
      : null,
  ].filter(Boolean);
  return parts.length > 0 ? parts.join(" · ") : null;
}

function asText(queries: PrebidQuery[], approximatePages: boolean): string {
  return queries
    .map((q) => {
      const ref = where(q, approximatePages);
      return `${q.number}. ${q.query}${ref ? ` (${ref})` : ""}`;
    })
    .join("\n\n");
}

/** Older extractions without drafted queries: show the unclear points as a simple list. */
function UnclearList({
  points,
  approximatePages,
}: {
  points: UnclearPoint[];
  approximatePages: boolean;
}) {
  return (
    <ul className="flex list-disc flex-col gap-2 pl-5">
      {points.map((point, i) => (
        <li key={`${point.topic}-${i}`}>
          <span className="font-medium">{point.topic}</span> — {point.why}
          {point.page !== null ? (
            <span className="text-sm text-muted-foreground">
              {" "}
              ({approximatePages ? "≈ page" : "page"} {point.page})
            </span>
          ) : null}
        </li>
      ))}
    </ul>
  );
}

export function PrebidQueries({
  documentId,
  approximatePages,
  fallback,
}: {
  documentId: string;
  approximatePages: boolean;
  fallback: UnclearPoint[];
}) {
  const loader = React.useCallback(
    () => api.prebidQueries(documentId),
    [documentId],
  );
  const { state } = useLoad(loader);
  const [copied, setCopied] = React.useState(false);
  const [copyError, setCopyError] = React.useState(false);

  const queries = state.kind === "ready" ? state.data : [];
  if (queries.length === 0 && (state.kind !== "error" || fallback.length === 0))
    return null;

  async function copyAll() {
    try {
      await navigator.clipboard.writeText(asText(queries, approximatePages));
      setCopyError(false);
      setCopied(true);
      window.setTimeout(() => setCopied(false), COPIED_MS);
    } catch {
      setCopyError(true);
    }
  }

  return (
    <section className="flex flex-col gap-4 rounded-2xl border border-warning/30 bg-warning-muted px-6 py-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">
            Draft questions to ask the client
          </h2>
          <p className="text-sm text-muted-foreground">
            The document is vague or silent on these points. Asking the client
            now means the price is based on the same understanding.
          </p>
        </div>
        {queries.length > 0 ? (
          <div className="flex items-center gap-2">
            {copied ? (
              <span className="text-sm text-muted-foreground">Copied</span>
            ) : null}
            {copyError ? (
              <span className="text-sm text-destructive">
                Could not copy — select the text instead.
              </span>
            ) : null}
            <Button variant="outline" size="sm" onClick={copyAll}>
              Copy all questions
            </Button>
          </div>
        ) : null}
      </div>
      {queries.length > 0 ? (
        <ol className="flex flex-col gap-3">
          {queries.map((query) => {
            const ref = where(query, approximatePages);
            return (
              <li
                key={query.number}
                className="flex gap-3 rounded-xl border bg-card px-4 py-3"
              >
                <span className="font-semibold text-muted-foreground tabular-nums">
                  {query.number}.
                </span>
                <div className="flex flex-col gap-1">
                  <span>{query.query}</span>
                  {ref ? (
                    query.quote ? (
                      <details className="group text-sm">
                        <summary className="cursor-pointer list-none text-primary hover:underline">
                          {ref}
                          <span className="ml-1 text-muted-foreground group-open:hidden">
                            (show text)
                          </span>
                        </summary>
                        <blockquote className="mt-2 border-l-2 border-primary/40 pl-3 text-muted-foreground italic">
                          “{query.quote}”
                        </blockquote>
                      </details>
                    ) : (
                      <span className="text-sm text-muted-foreground">
                        {ref}
                      </span>
                    )
                  ) : null}
                </div>
              </li>
            );
          })}
        </ol>
      ) : (
        <UnclearList points={fallback} approximatePages={approximatePages} />
      )}
    </section>
  );
}
