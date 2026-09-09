"use client";

import { AlertTriangle, CalendarCheck, Inbox, ListTodo } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import type { Task } from "@/lib/api/types";
import { useTasks, useTaxonomy, useVisions } from "@/lib/api/hooks";
import { TaskList } from "@/components/tasks/task-list";
import { TaskDetailPanel } from "./task-detail-panel";

export function Dashboard() {
  const today = useTasks({ view: "today", page_size: 8 });
  const overdue = useTasks({ view: "overdue", page_size: 8 });
  const inbox = useTasks({ view: "inbox", page_size: 8 });
  const { categories, contexts, tags } = useTaxonomy();
  const visions = useVisions();
  const [selected, setSelected] = useState<Task | null>(null);
  const cat = categories.data?.items ?? [];
  const ctx = contexts.data?.items ?? [];
  const tag = tags.data?.items ?? [];
  const vis = visions.data?.items ?? [];
  return (
    <div className="grid gap-4 sm:gap-6">
      <div className="grid grid-cols-3 gap-2 sm:gap-3">
        <Metric href="/tasks?view=today" label="Dnes" value={today.data?.total ?? 0} icon={<CalendarCheck size={18}/>} />
        <Metric href="/tasks?view=overdue" label="Po termínu" value={overdue.data?.total ?? 0} icon={<AlertTriangle size={18}/>} danger />
        <Metric href="/tasks?view=inbox" label="Inbox" value={inbox.data?.total ?? 0} icon={<Inbox size={18}/>} />
      </div>
      <section className="grid gap-2 sm:gap-3"><div className="flex items-center justify-between"><h2 className="text-base font-semibold sm:text-xl">Dnešní práce</h2><Link className="text-xs text-[var(--muted)] sm:text-sm" href="/tasks?view=today">Zobrazit vše</Link></div>{today.isLoading ? <Loading/> : <TaskList tasks={today.data?.items ?? []} categories={cat} contexts={ctx} tags={tag} visions={vis} onSelect={setSelected}/>}</section>
      <section className="grid gap-2 sm:gap-3"><div className="flex items-center gap-2"><ListTodo size={18}/><h2 className="text-base font-semibold sm:text-xl">Po termínu</h2></div>{overdue.isLoading ? <Loading/> : <TaskList tasks={overdue.data?.items ?? []} categories={cat} contexts={ctx} tags={tag} visions={vis} onSelect={setSelected}/>}</section>
      <TaskDetailPanel task={selected} categories={cat} contexts={ctx} tags={tag} visions={vis} onClose={() => setSelected(null)} />
    </div>
  );
}

function Metric({ label, value, icon, href, danger }: { label: string; value: number; icon: React.ReactNode; href: string; danger?: boolean }) {
  return <Link href={href} className="panel flex items-center justify-between p-3 sm:p-5"><div><p className="text-xs text-[var(--muted)] sm:text-sm">{label}</p><p className="mt-0.5 text-xl font-semibold sm:mt-1 sm:text-3xl">{value}</p></div><div className={danger ? "text-[var(--danger)]" : "text-[var(--accent)]"}>{icon}</div></Link>;
}
function Loading() { return <div className="panel p-4 text-sm text-[var(--muted)] sm:p-6">Načítám…</div>; }
