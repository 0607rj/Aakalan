"use client";

import * as React from "react";

import { ErrorNotice } from "@/components/status";
import { Button } from "@/components/ui/button";
import { downloadFile, errorText } from "@/lib/api/client";

type Kind = "pdf" | "xlsx";

function slug(name: string): string {
  return (
    name
      .replace(/[^A-Za-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 60) || "estimate"
  );
}

export function Downloads({
  estimateId,
  name,
}: {
  estimateId: string;
  name: string;
}) {
  const [busy, setBusy] = React.useState<Kind | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  async function download(kind: Kind) {
    setBusy(kind);
    setError(null);
    try {
      const path =
        kind === "pdf"
          ? `/estimates/${estimateId}/report.pdf`
          : `/estimates/${estimateId}/boq.xlsx`;
      await downloadFile(path, `${slug(name)}.${kind}`);
    } catch (e) {
      setError(
        `Could not download the ${kind === "pdf" ? "report" : "bill of quantities"}: ${errorText(e)}`,
      );
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap gap-3">
        <Button
          variant="outline"
          disabled={busy !== null}
          onClick={() => download("pdf")}
        >
          {busy === "pdf" ? "Preparing report…" : "Download report (PDF)"}
        </Button>
        <Button
          variant="outline"
          disabled={busy !== null}
          onClick={() => download("xlsx")}
        >
          {busy === "xlsx"
            ? "Preparing spreadsheet…"
            : "Download bill of quantities (Excel)"}
        </Button>
      </div>
      <ErrorNotice message={error} />
    </div>
  );
}
