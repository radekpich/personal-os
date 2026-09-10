"use client";

import { Expand, Plus, Send } from "lucide-react";
import { useState } from "react";
import { useQuickTask } from "@/lib/api/hooks";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Category, Context, Tag, Vision } from "@/lib/api/types";
import { TaskDialog } from "@/components/tasks/task-detail-panel";

export function QuickCapture({ categories, contexts, tags, visions }: { categories: Category[]; contexts: Context[]; tags: Tag[]; visions: Vision[] }) {
  const quickTask = useQuickTask();
  const [value, setValue] = useState("");
  const [open, setOpen] = useState(false);
  const disabled = quickTask.isPending || !value.trim();

  async function submitQuick() {
    const trimmed = value.trim();
    if (!trimmed) return;
    await quickTask.mutateAsync(trimmed);
    setValue("");
  }

  function openFullDialog() {
    setOpen(true);
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
            if (event.key === "Enter") void submitQuick();
          }}
        />
        <Button aria-label="Uložit rychlý úkol" className="min-w-10 px-2" disabled={disabled} onClick={submitQuick}><Send size={16} /></Button>
        <Button aria-label="Otevřít plný dialog úkolu" className="min-w-10 px-2" variant="secondary" onClick={openFullDialog}><Expand size={16} /></Button>
        <p className="hidden whitespace-nowrap text-xs text-[var(--muted)] md:block">Enter uloží</p>
      </div>
      <TaskDialog mode="create" open={open} initialTitle={value} categories={categories} contexts={contexts} tags={tags} visions={visions} onClose={() => setOpen(false)} />
    </>
  );
}
