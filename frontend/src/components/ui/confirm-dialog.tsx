"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";

type Props = {
  open: boolean;
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
  confirmDisabled?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  children?: ReactNode;
};

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "Smazat",
  cancelLabel = "Zrušit",
  destructive = true,
  confirmDisabled = false,
  onConfirm,
  onCancel,
  children,
}: Props) {
  return (
    <Dialog.Root open={open} onOpenChange={(next) => { if (!next) onCancel(); }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/30" />
        <Dialog.Content className="fixed inset-x-0 bottom-0 z-[51] flex h-[96dvh] max-h-[96dvh] flex-col overflow-hidden rounded-t-[var(--radius-xl)] border border-[var(--border)] bg-[var(--surface)] shadow-2xl sm:inset-y-0 sm:left-auto sm:right-0 sm:h-dvh sm:w-full sm:max-w-md sm:rounded-none sm:border-l">
          <div className="flex shrink-0 items-start justify-between gap-4 border-b border-[var(--border)] p-4 sm:p-6">
            <div>
              <Dialog.Title className="text-lg font-semibold">{title}</Dialog.Title>
              {description ? <Dialog.Description className="text-sm text-[var(--muted)]">{description}</Dialog.Description> : null}
            </div>
            <Dialog.Close asChild><Button variant="ghost" size="sm" aria-label="Zavřít"><X size={18} /></Button></Dialog.Close>
          </div>
          {children ? <div className="grid min-h-0 flex-1 gap-4 overflow-y-auto p-4 sm:p-6">{children}</div> : null}
          <div className="relative z-10 mt-auto flex shrink-0 justify-end gap-2 border-t border-[var(--border)] bg-[var(--surface)] p-4 pb-[calc(1rem+env(safe-area-inset-bottom))] sm:p-6">
            <Button type="button" variant="ghost" onClick={onCancel}>{cancelLabel}</Button>
            <Button type="button" variant={destructive ? "danger" : "default"} onClick={onConfirm} disabled={confirmDisabled}>{confirmLabel}</Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
