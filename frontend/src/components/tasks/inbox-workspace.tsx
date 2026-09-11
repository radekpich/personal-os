"use client";

import { Bot, CalendarDays, CheckSquare, HelpCircle, Inbox, Mail, MessageCircle, NotebookPen, Sparkles } from "lucide-react";
import { useMemo, useState } from "react";
import type { Category, Context, Task, TaskSource } from "@/lib/api/types";
import { useTasks, useTaxonomy, useUpdateTask, useVisions } from "@/lib/api/hooks";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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
const periods = [
  ["all", "Kdykoliv"],
  ["today", "Dnes"],
  ["7", "7 dní"],
  ["30", "30 dní"],
] as const;

function isoDaysAgo(days: number) {
  const date = new Date();
  date.setDate(date.getDate() - days);
  return date.toISOString().slice(0, 10);
}

function formatWhen(value: string) {
  const date = new Date(value);
  return new Intl.DateTimeFormat("cs-CZ", { dateStyle: "medium", timeStyle: "short" }).format(date);
}

function periodFilter(period: string) {
  if (period === "today") return { created_from: new Date().toISOString().slice(0, 10) };
  if (period === "7" || period === "30") return { created_from: isoDaysAgo(Number(period)) };
  return {};
}

export function InboxWorkspace() {
  const [source, setSource] = useState<TaskSource | "all">("all");
  const [period, setPeriod] = useState("all");
  const [selected, setSelected] = useState<Task | null>(null);
  const [checked, setChecked] = useState<Set<string>>(() => new Set());
  const [bulkCategoryId, setBulkCategoryId] = useState("all");
  const tasks = useTasks({ view: "inbox", source, page_size: 100, ...periodFilter(period) });
  const { categories, contexts, tags } = useTaxonomy();
  const visions = useVisions();
  const update = useUpdateTask();
  const cat = categories.data?.items ?? [];
  const ctx = contexts.data?.items ?? [];
  const tag = tags.data?.items ?? [];
  const vis = visions.data?.items ?? [];
  const items = useMemo(() => tasks.data?.items ?? [], [tasks.data?.items]);

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

  async function patchTask(task: Task, payload: { category_id?: string | null; context_id?: string | null }) {
    await update.mutateAsync({ task, payload: { ...payload, status: task.status === "inbox" && task.category_id && task.context_id ? "todo" : task.status } });
  }

  async function bulkAssignCategory() {
    if (bulkCategoryId === "all") return;
    const selectedTasks = items.filter((task) => checked.has(task.id));
    await Promise.all(selectedTasks.map((task) => update.mutateAsync({ task, payload: { category_id: bulkCategoryId } })));
    setChecked(new Set());
    setBulkCategoryId("all");
  }

  return (
    <div className="grid gap-4">
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
          </div>
        </div>
      </header>

      {checked.size > 0 ? (
        <div className="panel flex flex-wrap items-center gap-2 border-[var(--accent)] p-3">
          <span className="text-sm font-medium">Vybráno {checked.size}</span>
          <select aria-label="Hromadně přiřadit kategorii" className="focus-ring min-h-10 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-3 text-sm" value={bulkCategoryId} onChange={(event) => setBulkCategoryId(event.target.value)}>
            <option value="all">Vybrat kategorii…</option>
            {cat.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
          </select>
          <Button size="sm" onClick={bulkAssignCategory} disabled={bulkCategoryId === "all" || update.isPending}>Přiřadit kategorii</Button>
          <Button size="sm" variant="ghost" onClick={() => setChecked(new Set())}>Zrušit výběr</Button>
        </div>
      ) : null}

      {tasks.isLoading ? <div className="panel p-6 text-sm text-[var(--muted)]">Načítám inbox…</div> : null}
      {tasks.isError ? <div className="panel p-6 text-sm text-[var(--danger)]">Inbox se nepodařilo načíst.</div> : null}
      {!tasks.isLoading && grouped.length === 0 ? <EmptyInbox /> : null}

      <div className="grid gap-4">
        {grouped.map((group) => <SourceGroup key={group.source} source={group.source} tasks={group.items} categories={cat} contexts={ctx} checked={checked} pending={update.isPending} onToggle={toggle} onPatch={patchTask} onProcess={setSelected} />)}
      </div>

      <TaskDetailPanel task={selected} categories={cat} contexts={ctx} tags={tag} visions={vis} onClose={() => setSelected(null)} />
    </div>
  );
}

function SourceGroup({ source, tasks, categories, contexts, checked, pending, onToggle, onPatch, onProcess }: { source: TaskSource; tasks: Task[]; categories: Category[]; contexts: Context[]; checked: Set<string>; pending: boolean; onToggle: (id: string) => void; onPatch: (task: Task, payload: { category_id?: string | null; context_id?: string | null }) => void; onProcess: (task: Task) => void }) {
  const meta = sourceMeta[source];
  const Icon = meta.icon;
  return (
    <section className="grid gap-2">
      <div className="flex items-center justify-between px-1">
        <h2 className="flex items-center gap-2 text-base font-semibold"><span className="grid size-8 place-items-center rounded-full bg-[var(--surface-muted)]"><Icon size={16}/></span>{meta.label}</h2>
        <span className="text-sm text-[var(--muted)]">{tasks.length} položek</span>
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
      <Button size="sm" variant="secondary" onClick={onProcess}><CheckSquare size={15}/> Zpracovat</Button>
    </article>
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
