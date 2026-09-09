"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import type { Task, TaskFilters, TaskStatus, TaskView } from "@/lib/api/types";
import { useTasks, useTaxonomy, useVisions } from "@/lib/api/hooks";
import { TaskDetailPanel } from "@/components/tasks/task-detail-panel";
import { TaskList } from "@/components/tasks/task-list";

const statuses: Array<[TaskStatus | "all", string]> = [["all", "Vše"], ["inbox", "Inbox"], ["todo", "Čeká"], ["doing", "Rozpracováno"], ["done", "Hotovo"]];

export function TaskWorkspace({ initialView }: { initialView?: TaskView }) {
  const params = useSearchParams();
  const router = useRouter();
  const [selected, setSelected] = useState<Task | null>(null);
  const filters = useMemo<TaskFilters>(() => ({
    view: (params.get("view") as TaskView | null) ?? initialView,
    status: (params.get("status") as TaskStatus | null) ?? undefined,
    category_id: params.get("category_id") ?? undefined,
    context_id: params.get("context_id") ?? undefined,
    tag_ids: params.getAll("tag_ids"),
    q: params.get("q") ?? undefined,
    page_size: 50,
  }), [params, initialView]);
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

  function setParam(key: string, value: string) {
    const next = new URLSearchParams(params.toString());
    if (!value || value === "all") next.delete(key); else next.set(key, value);
    const query = next.toString();
    router.push(query ? `/tasks?${query}` : "/tasks");
  }

  const selectedFromUrl = params.get("selected");
  const activeSelected = selected ?? tasks.data?.items.find((task) => task.id === selectedFromUrl) ?? null;

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_20rem]">
      <section className="grid gap-4">
        <Filters status={filters.status ?? "all"} categoryId={filters.category_id ?? "all"} contextId={filters.context_id ?? "all"} categories={categories.data?.items ?? []} contexts={contexts.data?.items ?? []} onStatus={(value) => setParam("status", value)} onCategory={(value) => setParam("category_id", value)} onContext={(value) => setParam("context_id", value)} />
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
      <TaskDetailPanel task={activeSelected} categories={categories.data?.items ?? []} contexts={contexts.data?.items ?? []} tags={tags.data?.items ?? []} visions={visions.data?.items ?? []} onClose={() => { setSelected(null); if (selectedFromUrl) { const next = new URLSearchParams(params.toString()); next.delete("selected"); const query = next.toString(); router.push(query ? `/tasks?${query}` : "/tasks"); } }} />
    </div>
  );
}

function Filters({ status, categoryId, contextId, categories, contexts, onStatus, onCategory, onContext }: { status: string; categoryId: string; contextId: string; categories: { id: string; name: string }[]; contexts: { id: string; name: string }[]; onStatus: (value: string) => void; onCategory: (value: string) => void; onContext: (value: string) => void }) {
  return (
    <div className="panel flex flex-wrap gap-3 p-3">
      <select className="focus-ring min-h-10 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-3" value={status} onChange={(e) => onStatus(e.target.value)}>{statuses.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
      <select className="focus-ring min-h-10 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-3" value={categoryId} onChange={(e) => onCategory(e.target.value)}><option value="all">Všechny kategorie</option>{categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select>
      <select className="focus-ring min-h-10 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-3" value={contextId} onChange={(e) => onContext(e.target.value)}><option value="all">Všechny kontexty</option>{contexts.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select>
    </div>
  );
}
