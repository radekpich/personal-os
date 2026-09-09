"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { Expand, Plus, Send, X } from "lucide-react";
import { useState } from "react";
import { useCreateTask, useQuickTask } from "@/lib/api/hooks";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import type { Category } from "@/lib/api/types";

export function QuickCapture({ categories }: { categories: Category[] }) {
  const quickTask = useQuickTask();
  const createTask = useCreateTask();
  const [value, setValue] = useState("");
  const [open, setOpen] = useState(false);
  const [fullTitle, setFullTitle] = useState("");
  const [fullDescription, setFullDescription] = useState("");
  const [fullCategoryId, setFullCategoryId] = useState("");
  const disabled = quickTask.isPending || !value.trim();

  async function submitQuick() {
    const trimmed = value.trim();
    if (!trimmed) return;
    await quickTask.mutateAsync(trimmed);
    setValue("");
  }

  async function submitFull() {
    const title = fullTitle.trim();
    if (!title) return;
    await createTask.mutateAsync({
      title,
      description: fullDescription.trim() || null,
      category_id: fullCategoryId || null,
      status: "inbox",
      priority: "none",
    });
    setFullTitle("");
    setFullDescription("");
    setFullCategoryId("");
    setOpen(false);
  }

  return (
    <>
      <div className="panel mb-3 flex items-center gap-2 p-2 sm:mb-6 sm:p-3">
        <Plus className="hidden text-[var(--muted)] sm:block" size={18} />
        <Input
          aria-label="Rychle zapsat úkol"
          placeholder="Rychle zapsat úkol…"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") submitQuick();
          }}
        />
        <Button aria-label="Uložit rychlý úkol" className="min-w-10 px-2" disabled={disabled} onClick={submitQuick}><Send size={16} /></Button>
        <Button aria-label="Otevřít plný dialog úkolu" className="min-w-10 px-2" variant="secondary" onClick={() => { setFullTitle(value); setOpen(true); }}><Expand size={16} /></Button>
        <p className="hidden whitespace-nowrap text-xs text-[var(--muted)] md:block">Enter uloží</p>
      </div>

      <Dialog.Root open={open} onOpenChange={setOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/30" />
          <Dialog.Content className="fixed inset-x-3 top-16 z-50 mx-auto grid max-w-lg gap-4 rounded-[var(--radius-xl)] border border-[var(--border)] bg-[var(--surface)] p-4 shadow-soft sm:top-24 sm:p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <Dialog.Title className="text-lg font-semibold">Nový úkol</Dialog.Title>
                <Dialog.Description className="text-sm text-[var(--muted)]">Doplň úkol podrobněji. Uloží se do Inboxu.</Dialog.Description>
              </div>
              <Dialog.Close asChild><button className="focus-ring rounded-full p-1" aria-label="Zavřít dialog"><X size={18} /></button></Dialog.Close>
            </div>
            <label className="grid gap-1 text-sm font-medium">Název<Input value={fullTitle} onChange={(event) => setFullTitle(event.target.value)} autoFocus /></label>
            <label className="grid gap-1 text-sm font-medium">Popis<Textarea value={fullDescription} onChange={(event) => setFullDescription(event.target.value)} rows={4} /></label>
            <label className="grid gap-1 text-sm font-medium">Kategorie<select className="rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-3 py-2" value={fullCategoryId} onChange={(event) => setFullCategoryId(event.target.value)}><option value="">Bez kategorie</option>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label>
            <div className="flex justify-end gap-2">
              <Dialog.Close asChild><Button type="button" variant="ghost">Zrušit</Button></Dialog.Close>
              <Button type="button" onClick={submitFull} disabled={createTask.isPending || !fullTitle.trim()}>Uložit úkol</Button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </>
  );
}
