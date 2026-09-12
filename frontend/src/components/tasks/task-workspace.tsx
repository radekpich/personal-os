"use client";

import { SlidersHorizontal, X } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import type { Category, Context, Tag, Task, TaskFilters, TaskPriority, TaskStatus, TaskView } from "@/lib/api/types";
import { useTasks, useTaxonomy, useVisions } from "@/lib/api/hooks";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TaskDetailPanel } from "@/components/tasks/task-detail-panel";
import { TaskList } from "@/components/tasks/task-list";

const timeViews: Array<{ value: "all" | TaskView; label: string }> = [
  { value: "all", label: "Vše" },
  { value: "today", label: "Dnes" },
  { value: "tomorrow", label: "Zítra" },
  { value: "this_week", label: "Do týdne" },
  { value: "overdue", label: "Po termínu" },
  { value: "unscheduled", label: "Bez termínu" },
];

const statuses: Array<[TaskStatus | "all", string]> = [["all", "Vše"], ["inbox", "Inbox"], ["todo", "Čeká"], ["in_progress", "Rozpracováno"], ["blocked", "Blokováno"], ["done", "Hotovo"], ["cancelled", "Zrušeno"]];
const priorities: Array<[TaskPriority | "all", string]> = [["all", "Vše"], ["none", "Bez priority"], ["low", "Nízká"], ["medium", "Střední"], ["high", "Vysoká"]];

type AdvancedFilters = {
  status: TaskStatus | "all";
  priority: TaskPriority | "all";
  category_id: string;
  context_id: string;
  tag_ids: string[];
};

export function TaskWorkspace({ initialView }: { initialView?: TaskView }) {
  const params = useSearchParams();
  const router = useRouter();
  const [selected, setSelected] = useState<Task | null>(null);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const currentView = (params.get("view") as TaskView | null) ?? initialView ?? "all";
  const advanced = useMemo<AdvancedFilters>(() => ({
    status: (params.get("status") as TaskStatus | null) ?? "all",
    priority: (params.get("priority") as TaskPriority | null) ?? "all",
    category_id: params.get("category_id") ?? "all",
    context_id: params.get("context_id") ?? "all",
    tag_ids: params.getAll("tag_ids"),
  }), [params]);
  const filters = useMemo<TaskFilters>(() => ({
    view: currentView === "all" ? undefined : currentView,
    status: advanced.status === "all" ? undefined : advanced.status,
    priority: advanced.priority === "all" ? undefined : advanced.priority,
    category_id: advanced.category_id,
    context_id: advanced.context_id,
    tag_ids: advanced.tag_ids,
    q: params.get("q") ?? undefined,
    page_size: 50,
  }), [advanced, currentView, params]);
  const countBase = useMemo<TaskFilters>(() => ({
    status: advanced.status === "all" ? undefined : advanced.status,
    priority: advanced.priority === "all" ? undefined : advanced.priority,
    category_id: advanced.category_id,
    context_id: advanced.context_id,
    tag_ids: advanced.tag_ids,
    q: params.get("q") ?? undefined,
    page_size: 1,
  }), [advanced, params]);
  const counts = {
    all: useTasks(countBase),
    today: useTasks({ ...countBase, view: "today" }),
    tomorrow: useTasks({ ...countBase, view: "tomorrow" }),
    this_week: useTasks({ ...countBase, view: "this_week" }),
    overdue: useTasks({ ...countBase, view: "overdue" }),
    unscheduled: useTasks({ ...countBase, view: "unscheduled" }),
  };
  const tasks = useTasks(filters);
  const [highlightedIds, setHighlightedIds] = useState<Set<string>>(() => new Set());
  const seenIds = useRef<Set<string> | null>(null);
  useEffect(() => {
    const current = tasks.data?.items.map((task) => task.id) ?? null;
    if (!current) return;
    if (seenIds.current === null) {
      seenIds.current = new Set(current);
      return;
    }
    const added = current.filter((id) => !seenIds.current?.has(id));
    seenIds.current = new Set(current);
    if (added.length === 0) return;
    setHighlightedIds(new Set(added));
    const timeout = window.setTimeout(() => setHighlightedIds(new Set()), 10_000);
    return () => window.clearTimeout(timeout);
  }, [tasks.data?.items]);
  const { categories, contexts, tags } = useTaxonomy();
  const visions = useVisions();

  function pushParams(mutator: (next: URLSearchParams) => void) {
    const next = new URLSearchParams(params.toString());
    mutator(next);
    const query = next.toString();
    router.push(query ? `/tasks?${query}` : "/tasks");
  }

  function setView(view: "all" | TaskView) {
    pushParams((next) => {
      if (view === "all") next.delete("view"); else next.set("view", view);
      next.delete("selected");
    });
  }

  function applyAdvanced(nextFilters: AdvancedFilters) {
    pushParams((next) => {
      setOrDelete(next, "status", nextFilters.status);
      setOrDelete(next, "priority", nextFilters.priority);
      setOrDelete(next, "category_id", nextFilters.category_id);
      setOrDelete(next, "context_id", nextFilters.context_id);
      next.delete("tag_ids");
      for (const tagId of nextFilters.tag_ids) next.append("tag_ids", tagId);
      next.delete("selected");
    });
    setFiltersOpen(false);
  }

  const selectedFromUrl = params.get("selected");
  const activeSelected = selected ?? tasks.data?.items.find((task) => task.id === selectedFromUrl) ?? null;
  const activeAdvancedCount = countAdvancedFilters(advanced);

  return (
    <div className="grid min-w-0 max-w-full gap-5 xl:grid-cols-[minmax(0,1fr)_20rem]">
      <section className="grid min-w-0 gap-4">
        <div className="panel flex min-w-0 max-w-full items-center gap-2 overflow-hidden p-2 sm:p-3">
          <div className="-mx-1 flex min-w-0 flex-1 gap-2 overflow-x-auto px-1 pb-1" role="tablist" aria-label="Časové filtry úkolů">
            {timeViews.map((view) => {
              const active = currentView === view.value || (view.value === "all" && currentView === "all");
              const total = counts[view.value as keyof typeof counts].data?.total;
              return (
                <button
                  key={view.value}
                  type="button"
                  onClick={() => setView(view.value)}
                  className={cn(
                    "focus-ring inline-flex min-h-10 shrink-0 items-center gap-2 rounded-full border px-3 text-sm font-medium transition",
                    active ? "border-[var(--accent)] bg-[var(--accent)] text-white" : "border-[var(--border)] bg-[var(--surface)] text-[var(--muted)] hover:text-[var(--foreground)]",
                  )}
                  aria-pressed={active}
                >
                  <span>{view.label}</span>
                  <span className={cn("rounded-full px-2 py-0.5 text-xs", active ? "bg-white/20 text-white" : "bg-[var(--surface-muted)] text-[var(--muted)]")}>{total ?? "…"}</span>
                </button>
              );
            })}
          </div>
          <Button variant={activeAdvancedCount > 0 ? "default" : "secondary"} onClick={() => setFiltersOpen(true)} className="shrink-0">
            <SlidersHorizontal size={16} /> Filtry {activeAdvancedCount > 0 ? <Badge className="bg-white/20 px-2 py-0.5 text-xs text-current">{activeAdvancedCount}</Badge> : null}
          </Button>
        </div>
        {tasks.isLoading ? <div className="panel p-8 text-[var(--muted)]">Načítám úkoly…</div> : tasks.isError ? <div className="panel p-8 text-[var(--danger)]">Úkoly se nepodařilo načíst.</div> : <TaskList tasks={tasks.data?.items ?? []} categories={categories.data?.items ?? []} contexts={contexts.data?.items ?? []} tags={tags.data?.items ?? []} visions={visions.data?.items ?? []} selectedId={activeSelected?.id} highlightedIds={highlightedIds} onSelect={setSelected} />}
      </section>
      <aside className="panel hidden h-fit p-5 xl:block">
        <h2 className="font-semibold">Tipy</h2>
        <ul className="mt-3 grid gap-2 text-sm text-[var(--muted)]">
          <li><kbd>Cmd/Ctrl+N</kbd> rychlý zápis</li>
          <li><kbd>Cmd/Ctrl+K</kbd> command palette</li>
          <li>Klik na kolečko úkol optimisticky dokončí.</li>
        </ul>
      </aside>
      <TaskDetailPanel task={activeSelected} categories={categories.data?.items ?? []} contexts={contexts.data?.items ?? []} tags={tags.data?.items ?? []} visions={visions.data?.items ?? []} onClose={() => { setSelected(null); if (selectedFromUrl) { pushParams((next) => next.delete("selected")); } }} />
      {filtersOpen ? <AdvancedFilterPanel initial={advanced} categories={categories.data?.items ?? []} contexts={contexts.data?.items ?? []} tags={tags.data?.items ?? []} onApply={applyAdvanced} onClose={() => setFiltersOpen(false)} /> : null}
    </div>
  );
}

function setOrDelete(params: URLSearchParams, key: string, value: string) {
  if (!value || value === "all") params.delete(key); else params.set(key, value);
}

function countAdvancedFilters(filters: AdvancedFilters) {
  return [filters.status !== "all", filters.priority !== "all", filters.category_id !== "all", filters.context_id !== "all", filters.tag_ids.length > 0].filter(Boolean).length;
}

function AdvancedFilterPanel({ initial, categories, contexts, tags, onApply, onClose }: { initial: AdvancedFilters; categories: Category[]; contexts: Context[]; tags: Tag[]; onApply: (filters: AdvancedFilters) => void; onClose: () => void }) {
  const [draft, setDraft] = useState<AdvancedFilters>(initial);
  function toggleTag(tagId: string) {
    setDraft((current) => ({
      ...current,
      tag_ids: current.tag_ids.includes(tagId) ? current.tag_ids.filter((id) => id !== tagId) : [...current.tag_ids, tagId],
    }));
  }
  return (
    <div className="fixed inset-0 z-40 bg-black/30" role="dialog" aria-modal="true" aria-label="Filtry úkolů">
      <div className="absolute inset-x-0 bottom-0 max-h-[88vh] overflow-y-auto rounded-t-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-4 shadow-2xl sm:left-auto sm:right-4 sm:top-4 sm:w-[26rem] sm:rounded-[var(--radius-lg)]">
        <div className="flex items-center justify-between gap-3">
          <div><h2 className="text-lg font-semibold">Filtry</h2><p className="text-sm text-[var(--muted)]">Nastav všechno najednou a potvrď.</p></div>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="Zavřít filtry"><X size={16}/></Button>
        </div>
        <div className="mt-4 grid gap-3">
          <Select label="Kategorie" value={draft.category_id} onChange={(value) => setDraft((current) => ({ ...current, category_id: value }))} options={[{ value: "all", label: "Všechny kategorie" }, ...categories.map((c) => ({ value: c.id, label: c.name }))]} />
          <div className="grid gap-1">
            <Select label="Kde" value={draft.context_id} onChange={(value) => setDraft((current) => ({ ...current, context_id: value }))} options={[{ value: "all", label: "Všechna místa" }, ...contexts.map((c) => ({ value: c.id, label: c.name }))]} />
            <p className="text-xs text-[var(--muted)]">Místo nebo nástroj, kde úkol zvládnu — Ranč, Počítač, Město.</p>
          </div>
          <Select label="Stav" value={draft.status} onChange={(value) => setDraft((current) => ({ ...current, status: value as TaskStatus | "all" }))} options={statuses.map(([value, label]) => ({ value, label }))} />
          <Select label="Priorita" value={draft.priority} onChange={(value) => setDraft((current) => ({ ...current, priority: value as TaskPriority | "all" }))} options={priorities.map(([value, label]) => ({ value, label }))} />
          <div className="grid gap-2">
            <span className="text-sm font-medium">Tagy</span>
            <div className="flex flex-wrap gap-2">
              {tags.length === 0 ? <span className="text-sm text-[var(--muted)]">Žádné tagy.</span> : tags.map((tag) => (
                <button key={tag.id} type="button" onClick={() => toggleTag(tag.id)} className={cn("focus-ring rounded-full border px-3 py-1 text-sm", draft.tag_ids.includes(tag.id) ? "border-[var(--accent)] bg-[var(--accent)] text-white" : "border-[var(--border)] text-[var(--muted)]")}>{tag.name}</button>
              ))}
            </div>
          </div>
        </div>
        <div className="sticky bottom-0 -mx-4 mt-5 flex gap-2 border-t border-[var(--border)] bg-[var(--surface)] p-4">
          <Button className="flex-1" onClick={() => onApply(draft)}>Použít filtry</Button>
          <Button variant="ghost" onClick={() => onApply({ status: "all", priority: "all", category_id: "all", context_id: "all", tag_ids: [] })}>Vyčistit</Button>
        </div>
      </div>
    </div>
  );
}

function Select({ label, value, options, onChange }: { label: string; value: string; options: Array<{ value: string; label: string }>; onChange: (value: string) => void }) {
  return (
    <label className="grid gap-1 text-sm font-medium">
      {label}
      <select className="focus-ring min-h-11 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-3 text-sm" value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
      </select>
    </label>
  );
}
