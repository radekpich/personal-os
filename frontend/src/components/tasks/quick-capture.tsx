"use client";

import { Plus } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useQuickTask } from "@/lib/api/hooks";
import { Input } from "@/components/ui/input";

export function QuickCapture() {
  const [title, setTitle] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const quickTask = useQuickTask();

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "n") {
        event.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  async function submit() {
    const value = title.trim();
    if (!value) return;
    setTitle("");
    try { await quickTask.mutateAsync(value); } catch { setTitle(value); }
  }

  return (
    <div className="panel flex items-center gap-2 p-2">
      <div className="ml-2 text-[var(--muted)]"><Plus size={18} /></div>
      <Input ref={inputRef} value={title} onChange={(e) => setTitle(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") submit(); }} placeholder="Rychle zapsat úkol… Enter uloží, Cmd/Ctrl+N skočí sem" className="border-0 bg-transparent shadow-none focus-visible:outline-none" aria-label="Rychlý zápis úkolu" />
      {quickTask.isPending ? <span className="pr-3 text-xs text-[var(--muted)]">Ukládám…</span> : null}
    </div>
  );
}
