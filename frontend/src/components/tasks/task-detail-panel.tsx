"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { zodResolver } from "@hookform/resolvers/zod";
import { X } from "lucide-react";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import type { Category, Context, Tag, Task, Vision } from "@/lib/api/types";
import { useUpdateTask } from "@/lib/api/hooks";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";

const schema = z.object({
  title: z.string().min(1),
  description: z.string().nullable(),
  status: z.enum(["inbox", "todo", "doing", "done", "cancelled"]),
  priority: z.enum(["none", "low", "medium", "high"]),
  due_date: z.string().nullable(),
  due_time: z.string().nullable(),
  category_id: z.string().nullable(),
  context_id: z.string().nullable(),
  vision_id: z.string().nullable(),
  recurrence_rule: z.string().nullable(),
  recurrence_mode: z.enum(["fixed", "after_completion"]).nullable(),
  tag_ids: z.array(z.string()),
});
type Values = z.infer<typeof schema>;

export function TaskDetailPanel({ task, categories, contexts, tags, visions, onClose }: { task: Task | null; categories: Category[]; contexts: Context[]; tags: Tag[]; visions: Vision[]; onClose: () => void }) {
  const update = useUpdateTask();
  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: emptyValues });
  useEffect(() => { if (task) form.reset({ title: task.title, description: task.description ?? "", status: task.status, priority: task.priority, due_date: task.due_date, due_time: task.due_time, category_id: task.category_id, context_id: task.context_id, vision_id: task.vision_id, recurrence_rule: task.recurrence_rule, recurrence_mode: task.recurrence_mode, tag_ids: task.tags.map((tag) => tag.id) }); }, [task, form]);
  const open = Boolean(task);
  async function submit(values: Values) {
    if (!task) return;
    await update.mutateAsync({ id: task.id, payload: { ...values, description: values.description || null, due_date: values.due_date || null, due_time: values.due_time || null, category_id: values.category_id || null, context_id: values.context_id || null, vision_id: values.vision_id || null, recurrence_rule: values.recurrence_rule || null, recurrence_mode: values.recurrence_rule ? values.recurrence_mode ?? "fixed" : null } });
    onClose();
  }
  return (
    <Dialog.Root open={open} onOpenChange={(next) => { if (!next) onClose(); }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/25" />
        <Dialog.Content className="fixed right-0 top-0 z-50 h-dvh w-full max-w-xl overflow-y-auto border-l border-[var(--border)] bg-[var(--surface)] p-5 shadow-2xl sm:p-7">
          <div className="mb-6 flex items-start justify-between gap-4">
            <div><Dialog.Title className="text-xl font-semibold">Detail úkolu</Dialog.Title><Dialog.Description className="text-sm text-[var(--muted)]">Uprav bez odchodu ze seznamu.</Dialog.Description></div>
            <Dialog.Close asChild><Button variant="ghost" size="sm"><X size={18}/></Button></Dialog.Close>
          </div>
          <form className="grid gap-4" onSubmit={form.handleSubmit(submit)}>
            <label className="grid gap-1 text-sm font-medium">Název<Input {...form.register("title")} /></label>
            <label className="grid gap-1 text-sm font-medium">Poznámka<Textarea {...form.register("description")} /></label>
            <div className="grid gap-3 sm:grid-cols-2">
              <Select label="Stav" {...form.register("status")}><option value="inbox">Inbox</option><option value="todo">Čeká</option><option value="doing">Rozpracováno</option><option value="done">Hotovo</option><option value="cancelled">Zrušeno</option></Select>
              <Select label="Priorita" {...form.register("priority")}><option value="none">Bez priority</option><option value="low">Nízká</option><option value="medium">Střední</option><option value="high">Vysoká</option></Select>
              <label className="grid gap-1 text-sm font-medium">Termín<Input type="date" {...form.register("due_date")} /></label>
              <label className="grid gap-1 text-sm font-medium">Čas<Input type="time" {...form.register("due_time")} /></label>
              <Select label="Kategorie" {...form.register("category_id")}><option value="">Inbox / bez kategorie</option>{categories.map((c) => <option value={c.id} key={c.id}>{c.name}</option>)}</Select>
              <Select label="Kontext" {...form.register("context_id")}><option value="">Bez kontextu</option>{contexts.map((c) => <option value={c.id} key={c.id}>{c.name}</option>)}</Select>
              <Select label="Vize / cíl" {...form.register("vision_id")}><option value="">Bez vazby na vizi</option>{visions.map((v) => <option value={v.id} key={v.id}>{v.title}</option>)}</Select>
            </div>
            <label className="grid gap-1 text-sm font-medium">RRULE opakování<Input placeholder="FREQ=WEEKLY;BYDAY=MO" {...form.register("recurrence_rule")} /></label>
            <Select label="Typ opakování" {...form.register("recurrence_mode")}><option value="">Bez opakování</option><option value="fixed">Pevný rytmus</option><option value="after_completion">Po dokončení</option></Select>
            <div className="grid gap-2"><p className="text-sm font-medium">Tagy</p><div className="flex flex-wrap gap-2">{tags.map((tag) => <label key={tag.id} className="flex items-center gap-2 rounded-full border border-[var(--border)] px-3 py-1 text-sm"><input type="checkbox" value={tag.id} {...form.register("tag_ids")} />#{tag.name}</label>)}</div></div>
            <Button disabled={update.isPending}>{update.isPending ? "Ukládám…" : "Uložit změny"}</Button>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

const emptyValues: Values = { title: "", description: "", status: "inbox", priority: "none", due_date: null, due_time: null, category_id: null, context_id: null, vision_id: null, recurrence_rule: null, recurrence_mode: null, tag_ids: [] };

function Select({ label, children, ...props }: React.SelectHTMLAttributes<HTMLSelectElement> & { label: string }) {
  return <label className="grid gap-1 text-sm font-medium">{label}<select className="focus-ring min-h-11 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-3 text-base" {...props}>{children}</select></label>;
}
