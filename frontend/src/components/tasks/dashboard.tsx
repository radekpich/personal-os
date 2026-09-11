"use client";

import { AlertTriangle, CalendarCheck, CheckCircle2, Flame, Inbox, NotebookPen, Sunrise } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
import { rrulestr } from "rrule";
import type { Challenge, Note, Task } from "@/lib/api/types";
import { useChallenges, useCheckInChallenge, useNotes, useTasks, useTaxonomy, useVisions } from "@/lib/api/hooks";
import { TaskList } from "@/components/tasks/task-list";
import { TaskDetailPanel } from "./task-detail-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

function isScheduledToday(challenge: Challenge) {
  if (!challenge.is_active) return false;
  const now = new Date();
  const start = new Date(now);
  start.setHours(0, 0, 0, 0);
  const end = new Date(now);
  end.setHours(23, 59, 59, 999);
  const started = new Date(challenge.started_at);
  if (started > end) return false;
  try {
    const rule = rrulestr(`DTSTART:${challenge.started_at.replace(/[-:]/g, "").replace(/\.\d+/, "").replace("+0000", "Z")}\nRRULE:${challenge.schedule_rrule}`);
    return rule.between(start, end, true).length > 0;
  } catch {
    return true;
  }
}

export function Dashboard() {
  const today = useTasks({ view: "today", page_size: 8 });
  const tomorrow = useTasks({ view: "tomorrow", page_size: 8 });
  const overdue = useTasks({ view: "overdue", page_size: 6 });
  const inbox = useTasks({ view: "inbox", page_size: 1 });
  const challenges = useChallenges();
  const notes = useNotes({ kind: "diary", page_size: 3 });
  const checkIn = useCheckInChallenge();
  const { categories, contexts, tags } = useTaxonomy();
  const visions = useVisions();
  const [selected, setSelected] = useState<Task | null>(null);
  const cat = categories.data?.items ?? [];
  const ctx = contexts.data?.items ?? [];
  const tag = tags.data?.items ?? [];
  const vis = visions.data?.items ?? [];
  const todaysChallenges = useMemo(() => (challenges.data?.items ?? []).filter(isScheduledToday), [challenges.data?.items]);
  const todayItems = today.data?.items ?? [];
  const tomorrowItems = tomorrow.data?.items ?? [];
  const overdueTotal = overdue.data?.total ?? 0;
  const noteItems = notes.data?.items ?? [];

  return (
    <div className="grid gap-4 sm:gap-5">
      <div className="grid grid-cols-3 gap-2">
        <Metric href="/tasks?view=today" label="Dnes" value={today.data?.total ?? 0} icon={<CalendarCheck size={16}/>} />
        <Metric href="/tasks?view=overdue" label="Po termínu" value={overdueTotal} icon={<AlertTriangle size={16}/>} danger />
        <Metric href="/inbox" label="Inbox" value={inbox.data?.total ?? 0} icon={<Inbox size={16}/>} />
      </div>

      {overdueTotal > 0 ? (
        <Link href="/tasks?view=overdue" className="flex items-center justify-between rounded-[var(--radius-md)] border border-[var(--danger)]/30 bg-[var(--danger)]/10 px-3 py-2 text-sm font-medium text-[var(--danger)]">
          <span className="inline-flex items-center gap-2"><AlertTriangle size={16}/> Po termínu: {overdueTotal}</span>
          <span>Otevřít →</span>
        </Link>
      ) : null}

      {today.isLoading ? <Loading label="Načítám dnešek…" /> : todayItems.length > 0 ? (
        <TaskSection title="Dnes" subtitle="Co mám dnes dělat" href="/tasks?view=today" tasks={todayItems} categories={cat} contexts={ctx} tags={tag} visions={vis} onSelect={setSelected} primary />
      ) : null}

      {tomorrow.isLoading ? null : tomorrowItems.length > 0 ? (
        <TaskSection title="Zítra" subtitle="Ať víš, co tě čeká" href="/tasks?view=tomorrow" tasks={tomorrowItems} categories={cat} contexts={ctx} tags={tag} visions={vis} onSelect={setSelected} />
      ) : null}

      {challenges.isLoading ? null : todaysChallenges.length > 0 ? (
        <section className="grid gap-2">
          <div className="flex items-center justify-between">
            <h2 className="flex items-center gap-2 text-base font-semibold sm:text-lg"><Flame size={18}/> Návyky dnes</h2>
            <Link className="text-xs text-[var(--muted)] sm:text-sm" href="/challenges">Všechny</Link>
          </div>
          <div className="flex gap-3 overflow-x-auto pb-1">
            {todaysChallenges.map((challenge) => <ChallengeTodayCard key={challenge.id} challenge={challenge} pending={checkIn.isPending} onCheckIn={() => checkIn.mutate({ id: challenge.id, payload: { is_relapse: false } })} />)}
          </div>
        </section>
      ) : null}

      {notes.isLoading ? null : noteItems.length > 0 ? <DiarySection notes={noteItems} /> : null}

      {!today.isLoading && !tomorrow.isLoading && !challenges.isLoading && !notes.isLoading && todayItems.length === 0 && tomorrowItems.length === 0 && todaysChallenges.length === 0 && noteItems.length === 0 ? (
        <div className="panel p-6 text-center"><Sunrise className="mx-auto text-[var(--accent)]"/><h2 className="mt-2 text-lg font-semibold">Dnes máš čistý prostor</h2><p className="mt-1 text-sm text-[var(--muted)]">Žádné bloky nezabírají místo, protože není co řešit.</p></div>
      ) : null}

      <TaskDetailPanel task={selected} categories={cat} contexts={ctx} tags={tag} visions={vis} onClose={() => setSelected(null)} />
    </div>
  );
}

function TaskSection({ title, subtitle, href, tasks, categories, contexts, tags, visions, onSelect, primary }: { title: string; subtitle: string; href: string; tasks: Task[]; categories: Parameters<typeof TaskList>[0]["categories"]; contexts: Parameters<typeof TaskList>[0]["contexts"]; tags: Parameters<typeof TaskList>[0]["tags"]; visions: Parameters<typeof TaskList>[0]["visions"]; onSelect: (task: Task) => void; primary?: boolean }) {
  return (
    <section className="grid gap-2 sm:gap-3">
      <div className="flex items-center justify-between">
        <div><h2 className={primary ? "text-lg font-semibold sm:text-xl" : "text-base font-semibold sm:text-lg"}>{title}</h2><p className="text-xs text-[var(--muted)] sm:text-sm">{subtitle}</p></div>
        <Link className="text-xs text-[var(--muted)] sm:text-sm" href={href}>Zobrazit vše</Link>
      </div>
      <TaskList tasks={tasks} categories={categories} contexts={contexts} tags={tags} visions={visions} onSelect={onSelect}/>
    </section>
  );
}

function Metric({ label, value, icon, href, danger }: { label: string; value: number; icon: React.ReactNode; href: string; danger?: boolean }) {
  return <Link href={href} className="panel flex min-h-16 items-center justify-between p-3"><div><p className="text-[11px] uppercase tracking-[0.2em] text-[var(--muted)]">{label}</p><p className="mt-0.5 text-xl font-semibold">{value}</p></div><div className={danger ? "text-[var(--danger)]" : "text-[var(--accent)]"}>{icon}</div></Link>;
}

function ChallengeTodayCard({ challenge, pending, onCheckIn }: { challenge: Challenge; pending: boolean; onCheckIn: () => void }) {
  return (
    <article className="panel min-w-56 p-3">
      <div className="flex items-start justify-between gap-3"><div><p className="text-lg">{challenge.icon}</p><h3 className="mt-1 line-clamp-2 text-sm font-semibold">{challenge.title}</h3></div><Badge className="px-2 py-0.5 text-xs">{challenge.current_streak} dní</Badge></div>
      <Button className="mt-3 w-full" size="sm" onClick={onCheckIn} disabled={pending}><CheckCircle2 size={15}/> Zapsat dnes</Button>
    </article>
  );
}

function DiarySection({ notes }: { notes: Note[] }) {
  return (
    <section className="grid gap-2">
      <div className="flex items-center justify-between"><h2 className="flex items-center gap-2 text-base font-semibold sm:text-lg"><NotebookPen size={18}/> Poslední zápisky z deníku</h2><Link className="text-xs text-[var(--muted)] sm:text-sm" href="/diary">Deník</Link></div>
      <div className="grid gap-2 sm:grid-cols-3">
        {notes.map((note) => <Link key={note.id} href="/diary" className="panel p-3"><p className="text-xs text-[var(--muted)]">{note.entry_date ?? note.created_at.slice(0, 10)}</p><h3 className="mt-1 line-clamp-2 text-sm font-semibold">{note.title}</h3>{note.body ? <p className="mt-1 line-clamp-2 text-xs text-[var(--muted)]">{note.body}</p> : null}</Link>)}
      </div>
    </section>
  );
}

function Loading({ label }: { label: string }) { return <div className="panel p-4 text-sm text-[var(--muted)]">{label}</div>; }
