"use client";

import { Expand, Plus, Send } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuickTask } from "@/lib/api/hooks";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export function QuickCapture() {
  const [title, setTitle] = useState("");
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const quickTask = useQuickTask();
  const router = useRouter();

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
    setError(null);
    try {
      await quickTask.mutateAsync(value);
    } catch {
      setTitle(value);
      setError("Úkol se nepodařilo uložit. Zkus to prosím znovu.");
    }
  }

  return (
    <div className="panel grid gap-1 p-2">
      <div className="flex items-center gap-1 sm:gap-2">
        <div className="ml-1 text-[var(--muted)] sm:ml-2"><Plus size={17} /></div>
        <Input ref={inputRef} value={title} onChange={(e) => setTitle(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") void submit(); }} placeholder="Rychle zapsat úkol…" className="min-w-0 border-0 bg-transparent text-sm shadow-none focus-visible:outline-none sm:text-base" aria-label="Rychlý zápis úkolu" />
        {quickTask.isPending ? <span className="hidden pr-2 text-xs text-[var(--muted)] sm:inline">Ukládám…</span> : null}
        <Button type="button" size="sm" onClick={() => void submit()} disabled={quickTask.isPending || !title.trim()} aria-label="Uložit rychlý úkol"><Send size={15} /></Button>
        <Button type="button" size="sm" variant="secondary" onClick={() => router.push(`/tasks?view=inbox&q=${encodeURIComponent(title.trim())}`)} aria-label="Otevřít plný pohled úkolů"><Expand size={15} /></Button>
      </div>
      <div className="px-2 text-xs text-[var(--muted)]">
        <span className="hidden sm:inline">Enter uloží, Cmd/Ctrl+N skočí sem.</span>
        {error ? <span className="text-[var(--danger)]">{error}</span> : null}
      </div>
    </div>
  );
}
