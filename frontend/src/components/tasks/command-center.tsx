"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { Command } from "cmdk";
import { Search, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { useQuickTask, useTasks, useTaxonomy } from "@/lib/api/hooks";
import { Button } from "@/components/ui/button";

export function CommandCenter() {
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState("");
  const router = useRouter();
  const quick = useQuickTask();
  const tasks = useTasks({ page_size: 20, q: value || undefined });
  const { categories } = useTaxonomy();
  const trimmed = value.trim();

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const key = event.key.toLowerCase();
      if ((event.metaKey || event.ctrlKey) && key === "k") { event.preventDefault(); setOpen((current) => !current); }
      if ((event.metaKey || event.ctrlKey) && key === "1") router.push("/dashboard");
      if ((event.metaKey || event.ctrlKey) && key === "2") router.push("/tasks");
      if ((event.metaKey || event.ctrlKey) && key === "3") router.push("/inbox");
      if ((event.metaKey || event.ctrlKey) && key === "4") router.push("/visions");
      if ((event.metaKey || event.ctrlKey) && key === "5") router.push("/settings");
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [router]);

  const results = useMemo(() => tasks.data?.items ?? [], [tasks.data?.items]);

  async function createTask() {
    if (!trimmed) return;
    const task = await quick.mutateAsync(trimmed);
    setOpen(false); setValue(""); router.push(`/tasks?selected=${task.id}`);
  }

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-[60] bg-black/25" />
        <Dialog.Content className="fixed left-1/2 top-20 z-[61] w-[calc(100vw-2rem)] max-w-2xl -translate-x-1/2 overflow-hidden rounded-[var(--radius-xl)] border border-[var(--border)] bg-[var(--surface)] shadow-2xl">
          <Dialog.Title className="sr-only">Command palette</Dialog.Title>
          <Command shouldFilter={false} className="bg-transparent">
            <div className="flex items-center gap-3 border-b border-[var(--border)] px-4 py-3"><Search size={18}/><Command.Input value={value} onValueChange={setValue} autoFocus placeholder="Hledat úkol, kategorii nebo založit nový…" className="w-full bg-transparent outline-none"/><Dialog.Close asChild><button aria-label="Zavřít"><X size={18}/></button></Dialog.Close></div>
            <Command.List className="max-h-[60vh] overflow-auto p-2">
              <Command.Empty className="p-4 text-sm text-[var(--muted)]">Nic nenalezeno.</Command.Empty>
              {trimmed ? <Command.Item value={`create-${trimmed}`} onSelect={createTask} className="rounded-[var(--radius-sm)] px-3 py-2 aria-selected:bg-[var(--surface-muted)]">Vytvořit úkol „{trimmed}“</Command.Item> : null}
              <Command.Group heading="Pohledy" className="text-xs text-[var(--muted)]">
                {[['/dashboard','Dashboard'],['/tasks?view=today','Dnes'],['/tasks?view=overdue','Po termínu'],['/inbox','Inbox'],['/visions','Vize'],['/settings','Nastavení']].map(([href,label]) => <Command.Item key={href} value={label} onSelect={() => { setOpen(false); router.push(href); }} className="rounded-[var(--radius-sm)] px-3 py-2 text-sm aria-selected:bg-[var(--surface-muted)]">{label}</Command.Item>)}
              </Command.Group>
              <Command.Group heading="Kategorie" className="text-xs text-[var(--muted)]">
                {categories.data?.items.map((category) => <Command.Item key={category.id} value={category.name} onSelect={() => { setOpen(false); router.push(`/tasks?category_id=${category.id}`); }} className="rounded-[var(--radius-sm)] px-3 py-2 text-sm aria-selected:bg-[var(--surface-muted)]"><span className="mr-2 inline-block size-2 rounded-full" style={{ background: category.color }}/>{category.name}</Command.Item>)}
              </Command.Group>
              <Command.Group heading="Úkoly" className="text-xs text-[var(--muted)]">
                {results.map((task) => <Command.Item key={task.id} value={task.title} onSelect={() => { setOpen(false); router.push(`/tasks?selected=${task.id}`); }} className="rounded-[var(--radius-sm)] px-3 py-2 text-sm aria-selected:bg-[var(--surface-muted)]">{task.title}</Command.Item>)}
              </Command.Group>
            </Command.List>
          </Command>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export function CommandHint() { return <Button variant="secondary" size="sm"><Search size={15}/>Cmd/Ctrl+K</Button>; }
