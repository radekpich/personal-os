"use client";

import { ImagePlus, Loader2, UploadCloud } from "lucide-react";
import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { useUploadTaskAttachment } from "@/lib/api/hooks";

const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp", "image/heic", "image/heif", "application/pdf"];

export function AttachmentUploader({ taskId }: { taskId: string }) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const upload = useUploadTaskAttachment();

  async function uploadFiles(files: FileList | File[]) {
    const selected = Array.from(files);
    if (selected.length === 0) return;
    setMessage(null);
    try {
      for (const file of selected) {
        if (!ACCEPTED_TYPES.includes(file.type)) {
          setMessage(`Soubor ${file.name} nemá podporovaný typ.`);
          continue;
        }
        await upload.mutateAsync({ taskId, file });
      }
      setMessage(selected.length === 1 ? "Příloha nahraná." : "Přílohy nahrané.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Nahrání přílohy selhalo.");
    } finally {
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div
      className="rounded-[var(--radius)] border border-dashed border-[var(--border)] bg-[var(--surface-muted)] p-4"
      onDragOver={(event) => event.preventDefault()}
      onDrop={(event) => {
        event.preventDefault();
        void uploadFiles(event.dataTransfer.files);
      }}
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <div className="rounded-full bg-[var(--surface)] p-2 text-[var(--muted)]">
            <ImagePlus size={18} />
          </div>
          <div>
            <p className="text-sm font-semibold">Přílohy</p>
            <p className="text-xs text-[var(--muted)]">Přetáhni fotky/PDF nebo vyber soubor. Podporuje JPG, PNG, WebP, HEIC a PDF.</p>
          </div>
        </div>
        <Button type="button" variant="secondary" disabled={upload.isPending} onClick={() => inputRef.current?.click()}>
          {upload.isPending ? <Loader2 className="animate-spin" size={16} /> : <UploadCloud size={16} />}
          {upload.isPending ? "Nahrávám…" : "Přidat"}
        </Button>
      </div>
      <input
        ref={inputRef}
        className="sr-only"
        type="file"
        multiple
        accept={ACCEPTED_TYPES.join(",")}
        onChange={(event) => {
          if (event.target.files) void uploadFiles(event.target.files);
        }}
      />
      {message ? <p className="mt-3 text-xs text-[var(--muted)]">{message}</p> : null}
    </div>
  );
}
