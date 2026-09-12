"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { Download, FileText, Loader2, Unlink, X } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ActionButton } from "@/components/ui/action-buttons";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Input } from "@/components/ui/input";
import { attachmentUrl } from "@/lib/api/client";
import {
  useDeleteNoteAttachment,
  useDeleteTaskAttachment,
  useNoteAttachments,
  useTaskAttachments,
  useUnlinkNoteAttachment,
  useUnlinkTaskAttachment,
  useUpdateAttachment,
} from "@/lib/api/hooks";
import type { Attachment } from "@/lib/api/types";

type AttachmentGridProps =
  | { taskId: string; noteId?: never }
  | { noteId: string; taskId?: never };

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  return `${(kb / 1024).toFixed(1)} MB`;
}

function isImage(attachment: Attachment) {
  return attachment.mime_type.startsWith("image/");
}

export function AttachmentGrid(props: AttachmentGridProps) {
  const taskId = "taskId" in props ? props.taskId ?? null : null;
  const noteId = "noteId" in props ? props.noteId ?? null : null;
  const taskAttachments = useTaskAttachments(taskId);
  const noteAttachments = useNoteAttachments(noteId);
  const attachments = taskId ? taskAttachments : noteAttachments;
  const update = useUpdateAttachment();
  const removeTask = useDeleteTaskAttachment();
  const removeNote = useDeleteNoteAttachment();
  const unlinkTask = useUnlinkTaskAttachment();
  const unlinkNote = useUnlinkNoteAttachment();
  const [active, setActive] = useState<Attachment | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [caption, setCaption] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<Attachment | null>(null);

  const items = attachments.data?.items ?? [];

  async function saveCaption(attachment: Attachment) {
    await update.mutateAsync({ id: attachment.id, payload: { caption: caption.trim() || null } });
    setEditingId(null);
    await attachments.refetch();
  }

  async function deleteAttachment(attachment: Attachment) {
    if (taskId) {
      await removeTask.mutateAsync({ taskId, attachmentId: attachment.id });
    } else if (noteId) {
      await removeNote.mutateAsync({ noteId, attachmentId: attachment.id });
    }
    setDeleteTarget(null);
  }

  async function unlinkAttachment(attachment: Attachment) {
    if (taskId) {
      await unlinkTask.mutateAsync({ taskId, attachmentId: attachment.id });
    } else if (noteId) {
      await unlinkNote.mutateAsync({ noteId, attachmentId: attachment.id });
    }
  }

  if (attachments.isLoading) {
    return <p className="text-sm text-[var(--muted)]">Načítám přílohy…</p>;
  }

  if (items.length === 0) {
    return <p className="text-sm text-[var(--muted)]">Zatím žádné přílohy.</p>;
  }

  return (
    <>
      <div className="grid gap-3 sm:grid-cols-2">
        {items.map((attachment) => (
          <article key={attachment.id} className="overflow-hidden rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)]">
            <button type="button" className="block h-36 w-full bg-[var(--surface-muted)] text-left" onClick={() => setActive(attachment)}>
              {isImage(attachment) && attachment.processing_status === "ready" ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={attachmentUrl(attachment.id, "thumb")} alt={attachment.caption ?? attachment.original_filename} className="h-full w-full object-cover" />
              ) : (
                <span className="flex h-full items-center justify-center gap-2 text-sm text-[var(--muted)]">
                  {attachment.processing_status === "pending" ? <Loader2 className="animate-spin" size={18} /> : <FileText size={18} />}
                  {attachment.processing_status === "pending" ? "Zpracovávám…" : "Otevřít soubor"}
                </span>
              )}
            </button>
            <div className="grid gap-2 p-3">
              <div>
                <p className="truncate text-sm font-medium">{attachment.original_filename}</p>
                <p className="text-xs text-[var(--muted)]">{formatBytes(attachment.size_bytes)}</p>
              </div>
              {editingId === attachment.id ? (
                <div className="flex gap-2">
                  <Input value={caption} onChange={(event) => setCaption(event.target.value)} placeholder="Popisek" />
                  <Button type="button" size="sm" onClick={() => void saveCaption(attachment)}>OK</Button>
                </div>
              ) : (
                <p className="min-h-5 text-sm text-[var(--muted)]">{attachment.caption ?? "Bez popisku"}</p>
              )}
              <div className="flex flex-wrap gap-2">
                <ActionButton icon="edit" label="Popisek" showLabel onClick={() => { setEditingId(attachment.id); setCaption(attachment.caption ?? ""); }} />
                <Button type="button" size="sm" variant="ghost" onClick={() => void unlinkAttachment(attachment)}>
                  <Unlink size={14} />Odpojit
                </Button>
                <ActionButton icon="delete" label="Smazat" showLabel danger onClick={() => setDeleteTarget(attachment)} />
              </div>
            </div>
          </article>
        ))}
      </div>
      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title={`Smazat přílohu „${deleteTarget?.original_filename ?? ""}“?`}
        description="Soubor se odstraní z Personal OS. Tuto akci nejde vrátit zpět."
        confirmLabel="Smazat přílohu"
        destructive
        confirmDisabled={removeTask.isPending || removeNote.isPending}
        onConfirm={() => { if (deleteTarget) void deleteAttachment(deleteTarget); }}
        onCancel={() => setDeleteTarget(null)}
      />

      <Dialog.Root open={Boolean(active)} onOpenChange={(open) => { if (!open) setActive(null); }}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-[60] bg-black/60" />
          <Dialog.Content className="fixed left-1/2 top-1/2 z-[61] max-h-[92dvh] w-[92vw] max-w-5xl -translate-x-1/2 -translate-y-1/2 overflow-hidden rounded-[var(--radius)] bg-[var(--surface)] shadow-2xl">
            <div className="flex items-center justify-between gap-3 border-b border-[var(--border)] p-3">
              <Dialog.Title className="truncate text-sm font-semibold">{active?.original_filename}</Dialog.Title>
              <div className="flex gap-2">
                {active ? <Button asChild size="sm" variant="secondary"><a href={attachmentUrl(active.id)} target="_blank" rel="noreferrer"><Download size={14} />Stáhnout</a></Button> : null}
                <Dialog.Close asChild><Button size="sm" variant="ghost"><X size={16} /></Button></Dialog.Close>
              </div>
            </div>
            <div className="flex max-h-[80dvh] items-center justify-center bg-black/5 p-4">
              {active && isImage(active) ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={attachmentUrl(active.id)} alt={active.caption ?? active.original_filename} className="max-h-[76dvh] max-w-full rounded object-contain" />
              ) : active ? (
                <iframe src={attachmentUrl(active.id)} title={active.original_filename} className="h-[76dvh] w-full rounded border border-[var(--border)] bg-white" />
              ) : null}
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </>
  );
}
