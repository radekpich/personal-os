"use client";

import { Clock, PanelRightOpen, Trash2 } from "lucide-react";
import Link from "next/link";
import type { Category, Context, Tag, Task, TaskStatus, Vision } from "@/lib/api/types";
import { useDeleteTask, useToggleTaskDone } from "@/lib/api/hooks";
import { cn, formatHumanDate, isOverdue } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { priorityLabels, statusLabels } from "./labels";

type Props = { tasks: Task[]; categories: Category[]; contexts: Context[]; tags: Tag[]; visions?: Vision[]; selectedId?: string | null; highlightedIds?: Set<string>; onSelect: (task: Task) => void };

export function TaskList({ tasks, categories, contexts, visions = [], selectedId, highlightedIds = new Set(), onSelect }: Props) {
  if (tasks.length === 0) return <div className="panel p-8 text-center text-[var(--muted)]">Nic tu není. Zapiš první úkol nahoře.</div>;
  return (
    <div className="grid gap-3">
      {tasks.map((task) => <TaskItem key={task.id} task={task} category={categories.find((c) => c.id === task.category_id)} context={contexts.find((c) => c.id === task.context_id)} vision={visions.find((v) => v.id === task.vision_id)} selected={task.id === selectedId} highlighted={highlightedIds.has(task.id)} onSelect={() => onSelect(task)} />)}
    </div>
  );
}

function taskAgentActivityHref(task: Task) {
  return `/agent?action=create_task&entity_type=task&entity_id=${task.id}`;
}

function TaskItem({ task, category, context, vision, selected, highlighted, onSelect }: { task: Task; category?: Category; context?: Context; vision?: Vision; selected: boolean; highlighted: boolean; onSelect: () => void }) {
  const toggle = useToggleTaskDone();
  const remove = useDeleteTask();
  const done = task.status === "done";
  const overdue = isOverdue(task.due_date, task.status);
  const nextStatus: TaskStatus = done ? (task.category_id ? "todo" : "inbox") : "done";
  return (
    <article className={cn("task-row panel grid grid-cols-[auto_1fr_auto] items-start gap-3 p-4", selected && "border-[var(--accent)]", (task.created_by === "agent" || highlighted) && "border-[var(--accent)]/70 bg-[var(--accent)]/5")}>
      <button aria-label={done ? "Vrátit úkol" : "Dokončit úkol"} onClick={() => toggle.mutate({ task, status: nextStatus })} className={cn("mt-1 size-6 rounded-full border-2 transition", done ? "border-[var(--success)] bg-[var(--success)]" : "border-[var(--border-strong)] bg-transparent")}>{done ? <span className="text-xs text-white">✓</span> : null}</button>
      <div className="min-w-0">
        <button onClick={onSelect} className={cn("block text-left text-base font-medium tracking-tight", done && "text-[var(--muted-foreground)] line-through")}>{task.title}</button>
        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-[var(--muted)]">
          {category ? <Badge className="border-0" style={{ background: `${category.color}22`, color: category.color }}><span className="mr-1 size-2 rounded-full" style={{ background: category.color }} />{category.name}</Badge> : <Badge>Inbox</Badge>}
          {context ? <span>{context.name}</span> : null}
          {vision ? <Badge className="border-[var(--accent)] text-[var(--accent)]">🎯 {vision.title}</Badge> : null}
          <Badge className={cn(task.priority === "high" && "border-[var(--danger)] text-[var(--danger)]", task.priority === "medium" && "border-[var(--warning)] text-[var(--warning)]")}>{priorityLabels[task.priority]}</Badge>
          <span className={cn("inline-flex items-center gap-1", overdue && "font-semibold text-[var(--danger)]")}><Clock size={13}/>{formatHumanDate(task.due_date)}</span>
          <span>{statusLabels[task.status]}</span>
          {task.created_by === "agent" ? (
            <Link href={taskAgentActivityHref(task)} onClick={(event) => event.stopPropagation()} aria-label="Zobrazit akci agenta pro tento úkol">
              <Badge className="border-[var(--accent)] text-[var(--accent)] hover:bg-[var(--accent)]/10">agent</Badge>
            </Link>
          ) : null}
          {highlighted ? <Badge className="border-[var(--success)] text-[var(--success)]">nové</Badge> : null}
          {task.tags.map((tag) => <span key={tag.id}>#{tag.name}</span>)}
        </div>
      </div>
      <div className="flex gap-1">
        <Button variant="ghost" size="sm" onClick={onSelect} aria-label="Otevřít detail"><PanelRightOpen size={16}/></Button>
        <Button variant="ghost" size="sm" onClick={() => remove.mutate(task)} aria-label="Smazat"><Trash2 size={16}/></Button>
      </div>
    </article>
  );
}
