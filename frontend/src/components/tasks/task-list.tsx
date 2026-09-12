"use client";

import { Clock, PanelRightOpen, Trash2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import type { Category, Context, Tag, Task, TaskStatus, Vision } from "@/lib/api/types";
import { useDeleteTask, useToggleTaskDone } from "@/lib/api/hooks";
import { cn, formatHumanDate, isOverdue } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { MarkdownPreview } from "@/components/markdown-preview";
import { priorityLabels, statusLabels } from "./labels";

type Props = { tasks: Task[]; categories: Category[]; contexts: Context[]; tags: Tag[]; visions?: Vision[]; selectedId?: string | null; highlightedIds?: Set<string>; onSelect: (task: Task) => void };

export function TaskList({ tasks, categories, contexts, visions = [], selectedId, highlightedIds = new Set(), onSelect }: Props) {
  if (tasks.length === 0) return <div className="panel p-5 text-center text-sm text-[var(--muted)] sm:p-8">Nic tu není. Zapiš první úkol nahoře.</div>;
  return (
    <div className="grid gap-2 sm:gap-3">
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
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const done = task.status === "done";
  const overdue = isOverdue(task.due_date, task.status);
  const nextStatus: TaskStatus = done ? (task.category_id ? "todo" : "inbox") : "done";
  const showStatus = task.status !== "todo";

  function deleteTask() {
    if (!confirmingDelete) {
      setConfirmingDelete(true);
      window.setTimeout(() => setConfirmingDelete(false), 3500);
      return;
    }
    remove.mutate(task);
    setConfirmingDelete(false);
  }

  return (
    <article className={cn("task-row panel grid w-full min-w-0 max-w-full grid-cols-[auto_minmax(0,1fr)_auto] items-start gap-2 overflow-hidden p-3 sm:gap-3 sm:p-4", selected && "border-[var(--accent)]", (task.created_by === "agent" || highlighted) && "border-[var(--accent)]/70 bg-[var(--accent)]/5")}>
      <button type="button" aria-label={done ? "Vrátit úkol" : "Dokončit úkol"} onClick={() => toggle.mutate({ task, status: nextStatus })} className={cn("relative z-10 mt-0.5 size-5 rounded-full border-2 transition sm:mt-1 sm:size-6", done ? "border-[var(--success)] bg-[var(--success)]" : "border-[var(--border-strong)] bg-transparent")}>{done ? <span className="text-[10px] text-white sm:text-xs">✓</span> : null}</button>
      <div className="min-w-0 pr-1">
        <button type="button" onClick={onSelect} className={cn("block max-w-full break-words text-left text-sm font-medium tracking-tight sm:text-base", done && "text-[var(--muted-foreground)] line-through")}>{task.title}</button>
        <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-[11px] text-[var(--muted)] sm:mt-2 sm:gap-2 sm:text-xs">
          {category ? <Badge className="border-0 px-2 py-0.5" style={{ background: `${category.color}22`, color: category.color }}><span className="mr-1 size-2 rounded-full" style={{ background: category.color }} />{category.name}</Badge> : null}
          {context ? <span>{context.name}</span> : null}
          {vision ? <Badge className="border-[var(--accent)] px-2 py-0.5 text-[var(--accent)]">🎯 {vision.title}</Badge> : null}
          {task.priority !== "none" ? <Badge className={cn("px-2 py-0.5", task.priority === "high" && "border-[var(--danger)] text-[var(--danger)]", task.priority === "medium" && "border-[var(--warning)] text-[var(--warning)]")}>{priorityLabels[task.priority]}</Badge> : null}
          {task.due_date ? <span className={cn("inline-flex items-center gap-1", overdue && "font-semibold text-[var(--danger)]")}><Clock size={12}/>{formatHumanDate(task.due_date)}</span> : null}
          {showStatus ? <span>{statusLabels[task.status]}</span> : null}
          {task.created_by === "agent" ? (
            <Link href={taskAgentActivityHref(task)} onClick={(event) => event.stopPropagation()} aria-label="Zobrazit akci agenta pro tento úkol">
              <Badge className="border-[var(--accent)] px-2 py-0.5 text-[var(--accent)] hover:bg-[var(--accent)]/10">agent</Badge>
            </Link>
          ) : null}
          {highlighted ? <Badge className="border-[var(--success)] px-2 py-0.5 text-[var(--success)]">nové</Badge> : null}
          {task.tags.map((tag) => <span key={tag.id}>#{tag.name}</span>)}
        </div>
        {task.description ? <MarkdownPreview compact className="mt-2 text-sm text-[var(--muted)]">{task.description}</MarkdownPreview> : null}
        {confirmingDelete ? <p className="mt-2 text-xs text-[var(--danger)]">Klepni na koš ještě jednou pro smazání.</p> : null}
      </div>
      <div className="relative z-10 flex shrink-0 gap-0.5 sm:gap-1">
        <Button variant="ghost" size="sm" onClick={onSelect} aria-label="Otevřít detail"><PanelRightOpen size={15}/></Button>
        <Button variant={confirmingDelete ? "danger" : "ghost"} size="sm" onClick={deleteTask} aria-label={confirmingDelete ? "Potvrdit smazání" : "Smazat"}><Trash2 size={15}/></Button>
      </div>
    </article>
  );
}
