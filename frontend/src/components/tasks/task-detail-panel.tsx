"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { zodResolver } from "@hookform/resolvers/zod";
import { Plus, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import type { Category, Context, RecurrenceMode, Tag, Task, Vision } from "@/lib/api/types";
import { ApiError } from "@/lib/api/client";
import { useCreateTag, useCreateTask, useUpdateTask } from "@/lib/api/hooks";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { AttachmentGrid } from "@/components/attachments/attachment-grid";
import { AttachmentUploader } from "@/components/attachments/attachment-uploader";
import { RecurrenceBuilder } from "@/components/recurrence/recurrence-builder";
import { MarkdownPreview } from "@/components/markdown-preview";

const schema = z.object({
  title: z.string().min(1),
  description: z.string().nullable(),
  status: z.enum(["inbox", "todo", "doing", "done", "cancelled"]),
  priority: z.enum(["none", "low", "medium", "high"]),
  due_date: z.string().nullable(),
  due_time: z.string().nullable(),
  estimate_minutes: z.coerce.number().int().positive().nullable(),
  category_id: z.string().nullable(),
  context_id: z.string().nullable(),
  vision_id: z.string().nullable(),
  recurrence_rule: z.string().nullable(),
  recurrence_mode: z.enum(["fixed", "after_completion"]).nullable(),
  tag_ids: z.array(z.string()),
});

type FormInput = z.input<typeof schema>;
type Values = z.output<typeof schema>;

type Props = {
  mode: "create" | "edit";
  open: boolean;
  task?: Task | null;
  initialTitle?: string;
  categories: Category[];
  contexts: Context[];
  tags: Tag[];
  visions: Vision[];
  onClose: () => void;
  defaultStatus?: Values["status"];
};

export function TaskDialog({ mode, open, task = null, initialTitle = "", categories, contexts, tags, visions, onClose, defaultStatus = "todo" }: Props) {
  const update = useUpdateTask();
  const create = useCreateTask();
  const createTag = useCreateTag();
  const [conflict, setConflict] = useState<string | null>(null);
  const [tagName, setTagName] = useState("");
  const form = useForm<FormInput, unknown, Values>({ resolver: zodResolver(schema), defaultValues: emptyValues });
  const watchedTagIds = form.watch("tag_ids");
  const recurrenceRule = form.watch("recurrence_rule");
  const descriptionValue = form.watch("description");
  const selectedTagIds = useMemo(() => watchedTagIds ?? [], [watchedTagIds]);
  const selectedTags = useMemo(() => selectedTagIds.map((id) => tags.find((tag) => tag.id === id)).filter(Boolean) as Tag[], [selectedTagIds, tags]);
  const availableTags = tags.filter((tag) => !selectedTagIds.includes(tag.id));

  useEffect(() => {
    if (!open) return;
    setConflict(null);
    setTagName("");
    if (mode === "edit" && task) {
      form.reset({
        title: task.title,
        description: task.description ?? "",
        status: task.status,
        priority: task.priority,
        due_date: task.due_date,
        due_time: task.due_time,
        estimate_minutes: task.estimate_minutes,
        category_id: task.category_id,
        context_id: task.context_id,
        vision_id: task.vision_id,
        recurrence_rule: task.recurrence_rule,
        recurrence_mode: task.recurrence_mode,
        tag_ids: task.tags.map((tag) => tag.id),
      });
    } else {
      form.reset({ ...emptyValues, status: defaultStatus, title: initialTitle });
    }
  }, [open, mode, task, initialTitle, defaultStatus, form]);

  function addTagId(id: string) {
    if (!selectedTagIds.includes(id)) form.setValue("tag_ids", [...selectedTagIds, id], { shouldDirty: true, shouldValidate: true });
  }

  function removeTagId(id: string) {
    form.setValue("tag_ids", selectedTagIds.filter((tagId) => tagId !== id), { shouldDirty: true, shouldValidate: true });
  }

  async function createAndAddTag() {
    const name = tagName.trim().replace(/^#/, "");
    if (!name) return;
    const existing = tags.find((tag) => tag.name.toLocaleLowerCase("cs-CZ") === name.toLocaleLowerCase("cs-CZ"));
    const tag = existing ?? await createTag.mutateAsync({ name });
    addTagId(tag.id);
    setTagName("");
  }

  function toPayload(values: Values) {
    return {
      ...values,
      description: values.description || null,
      due_date: values.due_date || null,
      due_time: values.due_time || null,
      estimate_minutes: values.estimate_minutes || null,
      category_id: values.category_id || null,
      context_id: values.context_id || null,
      vision_id: values.vision_id || null,
      recurrence_rule: values.recurrence_rule || null,
      recurrence_mode: values.recurrence_rule ? values.recurrence_mode ?? "fixed" as RecurrenceMode : null,
    };
  }

  async function submit(values: Values) {
    try {
      if (mode === "edit" && task) {
        await update.mutateAsync({ task, payload: toPayload(values) });
      } else {
        await create.mutateAsync(toPayload(values));
      }
      onClose();
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setConflict("Záznam mezitím upravil web nebo agent. Načti aktuální stav a zkus změnu znovu.");
        return;
      }
      throw error;
    }
  }

  const pending = create.isPending || update.isPending;
  const completedText = task?.completed_at ? formatCompletedAt(task.completed_at) : null;
  const title = mode === "create" ? "Nový úkol" : "Detail úkolu";
  const description = mode === "create" ? "Vyplň všechny parametry úkolu na jednom místě." : "Uprav bez odchodu ze seznamu.";

  return (
    <Dialog.Root open={open} onOpenChange={(next) => { if (!next) onClose(); }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/30" />
        <Dialog.Content className="fixed inset-x-0 bottom-0 z-50 flex max-h-[96dvh] flex-col overflow-hidden rounded-t-[var(--radius-xl)] border border-[var(--border)] bg-[var(--surface)] shadow-2xl sm:inset-y-0 sm:left-auto sm:right-0 sm:h-dvh sm:w-full sm:max-w-xl sm:rounded-none sm:border-l">
          <div className="flex items-start justify-between gap-4 border-b border-[var(--border)] p-4 sm:p-6">
            <div><Dialog.Title className="text-lg font-semibold sm:text-xl">{title}</Dialog.Title><Dialog.Description className="text-sm text-[var(--muted)]">{description}</Dialog.Description></div>
            <Dialog.Close asChild><Button variant="ghost" size="sm" aria-label="Zavřít"><X size={18}/></Button></Dialog.Close>
          </div>
          <form className="flex min-h-0 flex-1 flex-col" onSubmit={form.handleSubmit(submit)}>
            <div className="grid flex-1 gap-3 overflow-y-auto p-4 pb-24 sm:gap-4 sm:p-6 sm:pb-24">
              {conflict ? <p className="rounded-[var(--radius-sm)] border border-[var(--warning)] bg-[var(--warning)]/10 p-3 text-sm text-[var(--warning)]">{conflict}</p> : null}
              {completedText ? <p className="rounded-[var(--radius-sm)] bg-[var(--success-soft)] p-3 text-sm font-medium text-[var(--success)]">{completedText}</p> : null}
              <label className="grid gap-1 text-sm font-medium">Název<Input {...form.register("title")} autoFocus /></label>
              <label className="grid gap-1 text-sm font-medium">Popis<Textarea {...form.register("description")} rows={4} /></label>
              {descriptionValue ? <MarkdownPreview className="rounded-[var(--radius-md)] bg-[var(--surface-muted)] p-3 text-sm text-[var(--muted)]">{descriptionValue}</MarkdownPreview> : null}
              <div className="grid gap-3 sm:grid-cols-2">
                <Select label="Stav" {...form.register("status")}><option value="inbox">Inbox</option><option value="todo">Čeká</option><option value="doing">Rozpracováno</option><option value="done">Hotovo</option><option value="cancelled">Zrušeno</option></Select>
                <Select label="Priorita" {...form.register("priority")}><option value="none">Bez priority</option><option value="low">Nízká</option><option value="medium">Střední</option><option value="high">Vysoká</option></Select>
                <label className="grid gap-1 text-sm font-medium">Termín<Input type="date" {...form.register("due_date")} /></label>
                <label className="grid gap-1 text-sm font-medium">Čas (volitelně)<Input type="time" {...form.register("due_time")} /></label>
                <label className="grid gap-1 text-sm font-medium">Odhad v minutách<Input type="number" min={1} inputMode="numeric" {...form.register("estimate_minutes")} /></label>
                <Select label="Kategorie" {...form.register("category_id")}><option value="">Bez kategorie</option>{categories.map((c) => <option value={c.id} key={c.id}>{c.parent_id ? "— " : ""}{c.name}</option>)}</Select>
                <Select label="Kde" {...form.register("context_id")}><option value="">Bez místa</option>{contexts.map((c) => <option value={c.id} key={c.id}>{c.name}</option>)}</Select>
                <Select label="Vize / cíl" {...form.register("vision_id")}><option value="">Bez vazby na vizi</option>{visions.map((v) => <option value={v.id} key={v.id}>{v.title}</option>)}</Select>
              </div>
              <RecurrenceBuilder
                value={recurrenceRule}
                allowNone
                onChange={(next) => {
                  form.setValue("recurrence_rule", next, { shouldDirty: true, shouldValidate: true });
                  if (!next) form.setValue("recurrence_mode", null, { shouldDirty: true, shouldValidate: true });
                  if (next && !form.getValues("recurrence_mode")) form.setValue("recurrence_mode", "fixed", { shouldDirty: true, shouldValidate: true });
                }}
              />
              {recurrenceRule ? (
                <fieldset className="grid gap-2 rounded-[var(--radius-lg)] border border-[var(--border)] p-3 text-sm">
                  <legend className="px-1 font-semibold">Typ opakování</legend>
                  <label className="flex items-start gap-2">
                    <input type="radio" value="fixed" {...form.register("recurrence_mode")} />
                    <span><strong>Podle rozvrhu</strong> — další termín podle pravidla, i když jsem předchozí nesplnil (fakturace každé pondělí).</span>
                  </label>
                  <label className="flex items-start gap-2">
                    <input type="radio" value="after_completion" {...form.register("recurrence_mode")} />
                    <span><strong>Po dokončení</strong> — další termín se počítá od chvíle, kdy úkol zavřu (výměna podestýlky 7 dní po té minulé).</span>
                  </label>
                </fieldset>
              ) : null}
              <div className="grid gap-2">
                <p className="text-sm font-medium">Tagy</p>
                {selectedTags.length ? <div className="flex flex-wrap gap-2">{selectedTags.map((tag) => <button key={tag.id} type="button" onClick={() => removeTagId(tag.id)} className="focus-ring rounded-full border border-[var(--border)] px-2.5 py-1 text-sm">#{tag.name} ×</button>)}</div> : <p className="text-sm text-[var(--muted)]">Žádné tagy.</p>}
                <div className="flex flex-wrap gap-2">{availableTags.map((tag) => <button key={tag.id} type="button" onClick={() => addTagId(tag.id)} className="focus-ring rounded-full border border-[var(--border)] px-2.5 py-1 text-sm text-[var(--muted)]">+ #{tag.name}</button>)}</div>
                <div className="flex gap-2"><Input value={tagName} onChange={(event) => setTagName(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); void createAndAddTag(); } }} placeholder="Nový tag…" /><Button type="button" variant="secondary" onClick={() => void createAndAddTag()} disabled={createTag.isPending || !tagName.trim()}><Plus size={15}/>Přidat</Button></div>
              </div>
              <section className="grid gap-3 rounded-[var(--radius-lg)] border border-dashed border-[var(--border)] p-3 text-sm text-[var(--muted)]">
                <p className="font-medium text-[var(--foreground)]">Přílohy</p>
                {mode === "edit" && task ? <><AttachmentUploader taskId={task.id} /><AttachmentGrid taskId={task.id} /></> : <p>Přílohy půjdou nahrát hned po prvním uložení úkolu.</p>}
              </section>
            </div>
            <div className="sticky bottom-0 flex justify-end gap-2 border-t border-[var(--border)] bg-[var(--surface)] p-4 pb-[calc(1rem+env(safe-area-inset-bottom))] sm:p-6">
              <Button type="button" variant="ghost" onClick={onClose}>Zrušit</Button>
              <Button disabled={pending}>{pending ? "Ukládám…" : "Uložit"}</Button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export function TaskDetailPanel(props: Omit<Props, "mode" | "open"> & { task: Task | null }) {
  return <TaskDialog {...props} mode="edit" open={Boolean(props.task)} />;
}

const emptyValues: Values = { title: "", description: "", status: "todo", priority: "none", due_date: null, due_time: null, estimate_minutes: null, category_id: null, context_id: null, vision_id: null, recurrence_rule: null, recurrence_mode: null, tag_ids: [] };

function formatCompletedAt(value: string) {
  const date = new Date(value);
  const formatted = new Intl.DateTimeFormat("cs-CZ", { dateStyle: "medium", timeStyle: "short" }).format(date);
  return `Splněno ${formatted}`;
}

function Select({ label, children, ...props }: React.SelectHTMLAttributes<HTMLSelectElement> & { label: string }) {
  return <label className="grid gap-1 text-sm font-medium">{label}<select className="focus-ring min-h-10 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-3 text-sm sm:min-h-11 sm:text-base" {...props}>{children}</select></label>;
}
