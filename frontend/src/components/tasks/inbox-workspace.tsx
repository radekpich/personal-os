"use client";

import { Bot, CalendarDays, HelpCircle, Inbox, Mail, MessageCircle, NotebookPen, RotateCcw, Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { Category, Context, Task, TaskPriority, TaskSource, TaskStatus, TaskUpdate } from "@/lib/api/types";
import { useDeleteTask, useRestoreTask, useTasks, useTaxonomy, useUpdateTask, useVisions } from "@/lib/api/hooks";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ActionButton } from "@/components/ui/action-buttons";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { TaskDetailPanel } from "./task-detail-panel";

const sourceMeta: Record<TaskSource, { label: string; icon: React.ComponentType<{ size?: number }>; emoji: string }> = {
  web: { label: "Web", icon: Inbox, emoji: "🌐" },
  quick_capture: { label: "Rychlý zápis", icon: Sparkles, emoji: "⚡" },
  telegram: { label: "Telegram", icon: MessageCircle, emoji: "💬" },
  agent: { label: "Agent", icon: Bot, emoji: "🤖" },
  calendar: { label: "Kalendář", icon: CalendarDays, emoji: "📅" },
  email: { label: "E-mail", icon: Mail, emoji: "✉️" },
  journal: { label: "Deník", icon: NotebookPen, emoji: "📓" },
};

const sources: TaskSource[] = ["quick_capture", "telegram", "agent", "calendar", "email", "journal", "web"];
const periods = [["all", "Kdykoliv"], ["today", "Dnes"], ["7", "7 dní"], ["30", "30 dní"]] as const;
const statusOptions: Array<[TaskStatus, string]> = [["inbox", "Inbox"], ["todo", "Čeká"], ["in_progress", "Rozpracováno"], ["blocked", "Blokováno"], ["done", "Hotovo"], ["cancelled", "Zrušeno"]];
const priorityOptions: Array<[TaskPriority, string]> = [["none", "Bez priority"], ["low", "Nízká"], ["medium", "Střední"], ["high", "Vysoká"]];

type BulkDraft = {
  category_id: string;
  context_id: string;
  status: "" | TaskStatus;
  priority: "" | TaskPriority;
  due_date: string;
};

type UndoState = {
  message: string;
  previous: Task[];
  updated: Task[];
  deletedIds: string[];
} | null;

function isoDaysAgo(days: number) {
  const date = new Date();
  date.setDate(date.getDate() - days);
  return date.toISOString().slice(0, 10);
}

function localDate(offsetDays = 0) {
  const date = new Date();
  date.setDate(date.getDate() + offsetDays);
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
  return date.toISOString().slice(0, 10);
}

function nextMonday() {
  const date = new Date();
  const day = date.getDay() || 7;
  date.setDate(date.getDate() + (8 - day));
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
  return date.toISOString().slice(0, 10);
}

function formatWhen(value: string) {
  const date = new Date(value);
  return new Intl.DateTimeFormat("cs-CZ", { dateStyle: "medium", timeStyle: "short" }).format(date);
}

function periodFilter(period: string) {
  if (period === "today") return { created_from: localDate() };
  if (period === "7" || period === "30") return { created_from: isoDaysAgo(Number(period)) };
  return {};
}

const emptyBulkDraft: BulkDraft = { category_id: "", context_id: "", status: "", priority: "", due_date: "" };

export function InboxWorkspace() {
  const [source, setSource] = useState<TaskSource | "all">("all");
  const [period, setPeriod] = useState("all");
  const [selected, setSelected] = useState<Task | null>(null);
  const [checked, setChecked] = useState<Set<string>>(() => new Set());
  const [bulk, setBulk] = useState<BulkDraft>(emptyBulkDraft);
  const [bulkDeleteOpen, setBulkDeleteOpen] = useState(false);
  const [undo, setUndo] = useState<UndoState>(null);
  const tasks = useTasks({ view: "inbox", source, page_size: 100, ...periodFilter(period) });
  const { categories, contexts, tags } = useTaxonomy();
  const visions = useVisions();
  const update = useUpdateTask();
  const remove = useDeleteTask();
  const restore = useRestoreTask();
  const cat = categories.data?.items ?? [];
  const ctx = contexts.data?.items ?? [];
  const tag = tags.data?.items ?? [];
  const vis = visions.data?.items ?? [];
  const items = useMemo(() => tasks.data?.items ?? [], [tasks.data?.items]);
  const selectedTasks = useMemo(() => items.filter((task) => checked.has(task.id)), [checked, items]);

  useEffect(() => {
    setChecked((current) => new Set([...current].filter((id) => items.some((task) => task.id === id))));
  }, [items]);

  useEffect(() => {
    if (!undo) return;
    const timeout = window.setTimeout(() => setUndo(null), 8_000);
    return () => window.clearTimeout(timeout);
  }, [undo]);

  const grouped = useMemo(() => {
    const map = new Map<TaskSource, Task[]>();
    for (const task of items) {
      const group = map.get(task.source) ?? [];
      group.push(task);
      map.set(task.source, group);
    }
    return sources
      .map((key) => ({ source: key, items: (map.get(key) ?? []).sort((a, b) => b.created_at.localeCompare(a.created_at)) }))
      .filter((group) => group.items.length > 0);
  }, [items]);

  function toggle(id: string) {
    setChecked((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  function selectAll() {
    setChecked(new Set(items.map((task) => task.id)));
  }

  function selectGroup(groupItems: Task[]) {
    setChecked((current) => new Set([...current, ...groupItems.map((task) => task.id)]));
  }

  async function patchTask(task: Task, payload: { category_id?: string | null; context_id?: string | null }) {
    await update.mutateAsync({ task, payload: { ...payload, status: task.status === "inbox" && task.category_id && task.context_id ? "todo" : task.status } });
  }

  function buildBulkPayload(): TaskUpdate {
    const payload: TaskUpdate = {};
    if (bulk.category_id === "__clear") payload.category_id = null;
    else if (bulk.category_id) payload.category_id = bulk.category_id;
    if (bulk.context_id === "__clear") payload.context_id = null;
    else if (bulk.context_id) payload.context_id = bulk.context_id;
    if (bulk.status) payload.status = bulk.status;
    if (bulk.priority) payload.priority = bulk.priority;
    if (bulk.due_date === "__clear") payload.due_date = null;
    else if (bulk.due_date) payload.due_date = bulk.due_date;
    return payload;
  }

  async function applyBulk() {
    const payload = buildBulkPayload();
    if (selectedTasks.length === 0 || Object.keys(payload).length === 0) return;
    const previous = selectedTasks;
    const updated = await Promise.all(selectedTasks.map((task) => update.mutateAsync({ task, payload })));
    setUndo({ message: `Zpracováno ${updated.length} položek.`, previous, updated, deletedIds: [] });
    setChecked(new Set());
    setBulk(emptyBulkDraft);
  }

  async function deleteSelected() {
    const previous = selectedTasks;
    if (!previous.length) return;
    await Promise.all(previous.map((task) => remove.mutateAsync(task)));
    setUndo({ message: `Smazáno ${previous.length} položek.`, previous, updated: [], deletedIds: previous.map((task) => task.id) });
    setChecked(new Set());
    setBulkDeleteOpen(false);
  }

  async function undoLast() {
    if (!undo) return;
    if (undo.deletedIds.length > 0) {
      await Promise.all(undo.deletedIds.map((id) => restore.mutateAsync(id)));
    } else {
      await Promise.all(undo.updated.map((task, index) => {
        const before = undo.previous[index];
        return update.mutateAsync({
          task,
          payload: {
            category_id: before.category_id,
            context_id: before.context_id,
            status: before.status,
            priority: before.priority,
            due_date: before.due_date,
          },
        });
      }));
    }
    setUndo({ message: `Vráceno ${undo.previous.length} položek.`, previous: [], updated: [], deletedIds: [] });
  }

  return (
    <div className="grid gap-4 pb-36">
      <header className="panel p-3 sm:p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-semibold tracking-tight">Inbox</h1>
            <Badge className="w-fit px-3 py-1 text-sm">{tasks.data?.total ?? 0} k roztřídění</Badge>
            <div className="group relative">
              <button type="button" aria-label="Nápověda k Inboxu" className="focus-ring grid size-8 place-items-center rounded-full text-[var(--muted)] hover:bg-[var(--surface-muted)]"><HelpCircle size={16} /></button>
              <div className="pointer-events-none absolute left-0 top-9 z-20 hidden w-72 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] p-3 text-sm text-[var(--muted)] shadow-xl group-hover:block group-focus-within:block">
                Všechno nezpracované z webu, Telegramu, mailu, kalendáře, deníku i agenta. Jednou za čas roztřídit a pryč odsud.
              </div>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <select aria-label="Filtrovat kanál" className="focus-ring min-h-10 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-3 text-sm" value={source} onChange={(event) => setSource(event.target.value as TaskSource | "all")}>
              <option value="all">Všechny kanály</option>
              {sources.map((item) => <option key={item} value={item}>{sourceMeta[item].label}</option>)}
            </select>
            <select aria-label="Filtrovat období" className="focus-ring min-h-10 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-3 text-sm" value={period} onChange={(event) => setPeriod(event.target.value)}>
              {periods.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
            <Button size="sm" variant="secondary" onClick={selectAll} disabled={items.length === 0}>Vybrat vše</Button>
          </div>
        </div>
      </header>

      {tasks.isLoading ? <div className="panel p-6 text-sm text-[var(--muted)]">Načítám inbox…</div> : null}
      {tasks.isError ? <div className="panel p-6 text-sm text-[var(--danger)]">Inbox se nepodařilo načíst.</div> : null}
      {!tasks.isLoading && grouped.length === 0 ? <EmptyInbox /> : null}

      <div className="grid gap-4">
        {grouped.map((group) => <SourceGroup key={group.source} source={group.source} tasks={group.items} categories={cat} contexts={ctx} checked={checked} pending={update.isPending || remove.isPending || restore.isPending} onToggle={toggle} onPatch={patchTask} onProcess={setSelected} onSelectGroup={() => selectGroup(group.items)} />)}
      </div>

      {checked.size > 0 ? (
        <BulkPanel
          count={checked.size}
          bulk={bulk}
          categories={cat}
          contexts={ctx}
          pending={update.isPending || remove.isPending || restore.isPending}
          onBulkChange={setBulk}
          onApply={applyBulk}
          onDelete={() => setBulkDeleteOpen(true)}
          onCancel={() => { setChecked(new Set()); setBulkDeleteOpen(false); }}
        />
      ) : null}

      <ConfirmDialog
        open={bulkDeleteOpen}
        title={`Smazat ${checked.size} položek z Inboxu?`}
        description="Tuto akci můžeš krátce vrátit přes lištu Zpět, ale potvrzení je stejné jako u ostatního mazání."
        confirmLabel={`Smazat ${checked.size}`}
        destructive
        confirmDisabled={remove.isPending || checked.size === 0}
        onConfirm={() => void deleteSelected()}
        onCancel={() => setBulkDeleteOpen(false)}
      />

      {undo ? (
        <div className="fixed inset-x-3 bottom-20 z-40 mx-auto flex max-w-3xl items-center justify-between gap-3 rounded-[var(--radius-lg)] border border-[var(--accent)] bg-[var(--surface)] p-3 shadow-2xl sm:bottom-4">
          <span className="text-sm font-medium">{undo.message}</span>
          {undo.previous.length > 0 ? <Button size="sm" variant="secondary" onClick={undoLast} disabled={update.isPending || restore.isPending}><RotateCcw size={15}/> Vrátit</Button> : null}
        </div>
      ) : null}

      <TaskDetailPanel task={selected} categories={cat} contexts={ctx} tags={tag} visions={vis} onClose={() => setSelected(null)} />
    </div>
  );
}

function SourceGroup({ source, tasks, categories, contexts, checked, pending, onToggle, onPatch, onProcess, onSelectGroup }: { source: TaskSource; tasks: Task[]; categories: Category[]; contexts: Context[]; checked: Set<string>; pending: boolean; onToggle: (id: string) => void; onPatch: (task: Task, payload: { category_id?: string | null; context_id?: string | null }) => void; onProcess: (task: Task) => void; onSelectGroup: () => void }) {
  const meta = sourceMeta[source];
  const Icon = meta.icon;
  return (
    <section className="grid gap-2">
      <div className="flex items-center justify-between gap-2 px-1">
        <h2 className="flex items-center gap-2 text-base font-semibold"><span className="grid size-8 place-items-center rounded-full bg-[var(--surface-muted)]"><Icon size={16}/></span>{meta.label}</h2>
        <div className="flex items-center gap-2"><span className="text-sm text-[var(--muted)]">{tasks.length} položek</span><Button size="sm" variant="ghost" onClick={onSelectGroup}>Vybrat vše v této skupině</Button></div>
      </div>
      <div className="grid gap-2">
        {tasks.map((task) => <InboxItem key={task.id} task={task} categories={categories} contexts={contexts} checked={checked.has(task.id)} pending={pending} onToggle={() => onToggle(task.id)} onPatch={(payload) => onPatch(task, payload)} onProcess={() => onProcess(task)} />)}
      </div>
    </section>
  );
}

function InboxItem({ task, categories, contexts, checked, pending, onToggle, onPatch, onProcess }: { task: Task; categories: Category[]; contexts: Context[]; checked: boolean; pending: boolean; onToggle: () => void; onPatch: (payload: { category_id?: string | null; context_id?: string | null }) => void; onProcess: () => void }) {
  const meta = sourceMeta[task.source];
  return (
    <article className="panel grid gap-3 p-3 sm:grid-cols-[auto_1fr_auto] sm:items-center sm:p-4">
      <input aria-label={`Vybrat ${task.title}`} type="checkbox" checked={checked} onChange={onToggle} className="size-5 rounded border-[var(--border)]" />
      <div className="min-w-0">
        <h3 className="truncate text-sm font-semibold sm:text-base">{task.title}</h3>
        <p className="mt-1 text-xs text-[var(--muted)]">Přišlo {formatWhen(task.created_at)} · {meta.emoji} {meta.label}{task.source_detail ? ` · ${task.source_detail}` : ""}</p>
        <div className="mt-2 flex flex-wrap gap-2">
          <select aria-label={`Kategorie pro ${task.title}`} className="focus-ring min-h-9 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-2 text-xs" value={task.category_id ?? "all"} onChange={(event) => onPatch({ category_id: event.target.value === "all" ? null : event.target.value })} disabled={pending}>
            <option value="all">Kategorie…</option>
            {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
          </select>
          <select aria-label={`Kde pro ${task.title}`} className="focus-ring min-h-9 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-2 text-xs" value={task.context_id ?? "all"} onChange={(event) => onPatch({ context_id: event.target.value === "all" ? null : event.target.value })} disabled={pending}>
            <option value="all">Kde…</option>
            {contexts.map((context) => <option key={context.id} value={context.id}>{context.name}</option>)}
          </select>
        </div>
      </div>
      <ActionButton icon="process" label="Zpracovat" showLabel onClick={onProcess} />
    </article>
  );
}

function BulkPanel({ count, bulk, categories, contexts, pending, onBulkChange, onApply, onDelete, onCancel }: { count: number; bulk: BulkDraft; categories: Category[]; contexts: Context[]; pending: boolean; onBulkChange: (bulk: BulkDraft) => void; onApply: () => void; onDelete: () => void; onCancel: () => void }) {
  const hasPatch = Object.keys({ ...bulk }).some((key) => bulk[key as keyof BulkDraft]);
  return (
    <div className="fixed inset-x-2 bottom-20 z-30 mx-auto max-w-5xl rounded-[var(--radius-lg)] border border-[var(--accent)] bg-[var(--surface)] p-3 shadow-2xl sm:bottom-4">
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="text-sm font-semibold">Vybráno {count}</span>
        <Button size="sm" variant="ghost" onClick={onCancel}>Zrušit výběr</Button>
      </div>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
        <select aria-label="Hromadná kategorie" className="focus-ring min-h-10 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-3 text-sm" value={bulk.category_id} onChange={(event) => onBulkChange({ ...bulk, category_id: event.target.value })}>
          <option value="">Kategorie: neměnit</option>
          <option value="__clear">Kategorie: vyčistit</option>
          {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
        </select>
        <select aria-label="Hromadné kde" className="focus-ring min-h-10 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-3 text-sm" value={bulk.context_id} onChange={(event) => onBulkChange({ ...bulk, context_id: event.target.value })}>
          <option value="">Kde: neměnit</option>
          <option value="__clear">Kde: vyčistit</option>
          {contexts.map((context) => <option key={context.id} value={context.id}>{context.name}</option>)}
        </select>
        <select aria-label="Hromadný stav" className="focus-ring min-h-10 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-3 text-sm" value={bulk.status} onChange={(event) => onBulkChange({ ...bulk, status: event.target.value as "" | TaskStatus })}>
          <option value="">Stav: neměnit</option>
          {statusOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
        <select aria-label="Hromadná priorita" className="focus-ring min-h-10 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-3 text-sm" value={bulk.priority} onChange={(event) => onBulkChange({ ...bulk, priority: event.target.value as "" | TaskPriority })}>
          <option value="">Priorita: neměnit</option>
          {priorityOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
        <select aria-label="Hromadný termín" className="focus-ring min-h-10 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-3 text-sm" value={bulk.due_date} onChange={(event) => onBulkChange({ ...bulk, due_date: event.target.value })}>
          <option value="">Termín: neměnit</option>
          <option value={localDate()}>Dnes</option>
          <option value={localDate(1)}>Zítra</option>
          <option value={nextMonday()}>Příští týden</option>
          <option value="__clear">Bez termínu</option>
        </select>
      </div>
      <div className="mt-2 flex flex-wrap gap-2">
        <input aria-label="Vlastní hromadný termín" type="date" className="focus-ring min-h-10 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-3 text-sm" value={bulk.due_date.startsWith("20") ? bulk.due_date : ""} onChange={(event) => onBulkChange({ ...bulk, due_date: event.target.value })} />
        <Button onClick={onApply} disabled={!hasPatch || pending}>Použít na {count}</Button>
        <ActionButton icon="delete" label="Smazat" showLabel danger onClick={onDelete} disabled={pending} />
      </div>
    </div>
  );
}

function EmptyInbox() {
  return (
    <div className="panel grid place-items-center gap-3 p-8 text-center sm:p-12">
      <div className="text-4xl">🎉</div>
      <h2 className="text-xl font-semibold">Inbox je čistý</h2>
      <p className="max-w-md text-sm text-[var(--muted)]">Tohle je cíl, ne prázdná plocha. Všechno příchozí je roztříděné a můžeš dělat skutečnou práci.</p>
    </div>
  );
}
