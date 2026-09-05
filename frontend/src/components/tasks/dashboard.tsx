"use client";

import { AlertTriangle, CalendarCheck, Inbox, ListTodo } from "lucide-react";
import Link from "next/link";
import { useTasks, useVisions } from "@/lib/api/hooks";
import { TaskList } from "@/components/tasks/task-list";
import { useTaxonomy } from "@/lib/api/hooks";
import { useState } from "react";
import type { Task } from "@/lib/api/types";
import { TaskDetailPanel } from "./task-detail-panel";

export function Dashboard() {
  const today = useTasks({ view: "today", page_size: 8 });
  const overdue = useTasks({ view: "overdue", page_size: 8 });
  const inbox = useTasks({ view: "inbox", page_size: 8 });
  const { categories, contexts, tags } = useTaxonomy();
  const visions = useVisions();
  const [selected, setSelected] = useState<Task | null>(null);
  const cat = categories.data?.items ?? []; const ctx = contexts.data?.items ?? []; const tag = tags.data?.items ?? []; const vis = visions.data?.items ?? [];
  return (
    <div className="grid gap-6">
      <div className="grid gap-3 sm:grid-cols-3">
        <Metric href="/tasks?view=today" label="Dnes" value={today.data?.total ?? 0} icon={<CalendarCheck size={20}/>} />
        <Metric href="/tasks?view=overdue" label="Po termínu" value={overdue.data?.total ?? 0} icon={<AlertTriangle size={20}/>} danger />
        <Metric href="/inbox" label="Inbox" value={inbox.data?.total ?? 0} icon={<Inbox size={20}/>} />
      </div>
      <section className="grid gap-3"><div className="flex items-center justify-between"><h2 className="text-xl font-semibold">Dnešní práce</h2><Link className="text-sm text-[var(--muted)]" href="/tasks?view=today">Zobrazit vše</Link></div>{today.isLoading ? <Loading/> : <TaskList tasks={today.data?.items ?? []} categories={cat} contexts={ctx} tags={tag} visions={vis} onSelect={setSelected}/>}</section>
      <section className="grid gap-3"><div className="flex items-center gap-2"><ListTodo size={20}/><h2 className="text-xl font-semibold">Po termínu</h2></div>{overdue.isLoading ? <Loading/> : <TaskList tasks={overdue.data?.items ?? []} categories={cat} contexts={ctx} tags={tag} visions={vis} onSelect={setSelected}/>}</section>
      <TaskDetailPanel task={selected} categories={cat} contexts={ctx} tags={tag} visions={vis} onClose={() => setSelected(null)} />
    </div>
  );
}

function Metric({ label, value, icon, href, danger }: { label: string; value: number; icon: React.ReactNode; href: string; danger?: boolean }) {
  return <Link href={href} className="panel flex items-center justify-between p-5"><div><p className="text-sm text-[var(--muted)]">{label}</p><p className="mt-1 text-3xl font-semibold">{value}</p></div><div className={danger ? "text-[var(--danger)]" : "text-[var(--accent)]"}>{icon}</div></Link>;
}
function Loading() { return <div className="panel p-6 text-[var(--muted)]">Načítám…</div>; }
