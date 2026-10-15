"use client";

import * as React from "react";

import { cn } from "@/lib/utils";

/** Right-hand side panel built on the native <dialog> (focus trap + Esc for free). */
function Sheet({
  open,
  onClose,
  title,
  description,
  children,
  className,
}: {
  open: boolean;
  onClose: () => void;
  title: React.ReactNode;
  description?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  const ref = React.useRef<HTMLDialogElement>(null);

  React.useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      onClick={(event) => {
        if (event.target === ref.current) onClose();
      }}
      className={cn(
        "fixed inset-y-0 right-0 left-auto m-0 h-dvh max-h-dvh w-full max-w-2xl border-l bg-card p-0 text-card-foreground shadow-xl backdrop:bg-black/30",
        className,
      )}
    >
      {open ? (
        <div className="flex h-full flex-col">
          <div className="flex items-start justify-between gap-4 border-b px-6 py-4">
            <div className="flex flex-col gap-1">
              <h2 className="text-base font-semibold">{title}</h2>
              {description ? (
                <p className="text-sm text-muted-foreground">{description}</p>
              ) : null}
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded-md px-2 py-1 text-sm text-muted-foreground hover:bg-muted"
              aria-label="Close"
            >
              ✕
            </button>
          </div>
          <div className="flex-1 overflow-y-auto px-6 py-4">{children}</div>
        </div>
      ) : null}
    </dialog>
  );
}

export { Sheet };
