"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ChevronDown, ChevronRight, GripVertical, Plus, Sparkles, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import {
  useCreateVision,
  useDeleteVision,
  useStagnatingVisions,
  useUpdateVision,
  useVisionProgress,
  useVisionTree,
} from "@/lib/api/hooks";
import type { Vision, VisionHorizon, VisionTreeNode } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";

const horizonLabels: Record<VisionHorizon, string> = {
  life: "Život",
  "5y": "5 let",
  "1y": "1 rok",
  quarter: "Kvartál",
};

const schema = z.object({
  title: z.string().min(1),
  description: z.string().nullable(),
  horizon: z.enum(["life", "5y", "1y", "quarter"]),
  target_date: z.string().nullable(),
});

type Values = z.infer<typeof schema>;

export function VisionWorkspace() {
  const tree = useVisionTree();
  const create = useCreateVision();
  const update = useUpdateVision();
  const remove = useDeleteVision();
  const stagnating = useStagnatingVisions(14);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [selected, setSelected] = useState<Vision | null>(null);
  const [draggedId, setDraggedId] = useState<string | null>(null);
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { title: "", description: "", horizon: "1y", target_date: null },
  });

  const nodes = useMemo(() => tree.data?.items ?? [], [tree.data?.items]);
  const flat = useMemo(() => flatten(nodes), [nodes]);
  const selectedProgress = useVisionProgress(selected?.id ?? null);

  async function submit(values: Values) {
    const payload = {
      ...values,
      description: values.description || null,
      target_date: values.target_date || null,
    };
    if (selected) {
      await update.mutateAsync({ id: selected.id, payload });
    } else {
      const vision = await create.mutateAsync(payload);
      setSelected(vision);
    }
    form.reset({ title: "", description: "", horizon: "1y", target_date: null });
  }

  function edit(vision: Vision) {
    setSelected(vision);
    form.reset({
      title: vision.title,
      description: vision.description ?? "",
      horizon: vision.horizon,
      target_date: vision.target_date,
    });
  }

  async function moveVision(targetParentId: string | null) {
    if (!draggedId || draggedId === targetParentId) return;
    await update.mutateAsync({ id: draggedId, payload: { parent_id: targetParentId } });
    setExpanded((current) => new Set([...current, targetParentId ?? "root"]));
    setDraggedId(null);
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_24rem]">
      <section className="grid gap-4">
        <div className="panel flex flex-wrap items-center justify-between gap-3 p-5">
          <div>
            <p className="text-sm text-[var(--muted)]">Sny → cíle → milníky → konkrétní kroky.</p>
            <h2 className="text-xl font-semibold">Strom dlouhodobých cílů</h2>
          </div>
          <Button onClick={() => { setSelected(null); form.reset({ title: "", description: "", horizon: "1y", target_date: null }); }}>
            <Plus size={16} /> Nová vize
          </Button>
        </div>
        <div
          className="panel min-h-36 p-3"
          onDragOver={(event) => event.preventDefault()}
          onDrop={() => moveVision(null)}
        >
          {tree.isLoading ? <p className="p-5 text-[var(--muted)]">Načítám vize…</p> : null}
          {tree.isError ? <p className="p-5 text-[var(--danger)]">Vize se nepodařilo načíst.</p> : null}
          {!tree.isLoading && nodes.length === 0 ? <p className="p-5 text-[var(--muted)]">Zatím žádná vize. Založ první životní cíl.</p> : null}
          <div className="grid gap-2">
            {nodes.map((node) => (
              <VisionNode
                key={node.id}
                node={node}
                level={0}
                expanded={expanded}
                onToggle={(id) => setExpanded((current) => toggleSet(current, id))}
                onEdit={edit}
                onDelete={(id) => remove.mutate(id)}
                onDragStart={setDraggedId}
                onDrop={moveVision}
              />
            ))}
          </div>
        </div>
      </section>
      <aside className="grid h-fit gap-4">
        <form className="panel grid gap-4 p-5" onSubmit={form.handleSubmit(submit)}>
          <div>
            <h2 className="font-semibold">{selected ? "Upravit vizi" : "Nová vize"}</h2>
            <p className="text-sm text-[var(--muted)]">Markdown popis zatím ukládáme jako text; render přijde později.</p>
          </div>
          <label className="grid gap-1 text-sm font-medium">Název<Input {...form.register("title")} /></label>
          <label className="grid gap-1 text-sm font-medium">Popis Markdown<Textarea rows={5} {...form.register("description")} /></label>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
            <Select label="Horizont" {...form.register("horizon")}>
              {Object.entries(horizonLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </Select>
            <label className="grid gap-1 text-sm font-medium">Cílové datum<Input type="date" {...form.register("target_date")} /></label>
          </div>
          <Button disabled={create.isPending || update.isPending}>{selected ? "Uložit vizi" : "Založit vizi"}</Button>
        </form>
        {selected ? <ProgressCard title={selected.title} progress={selectedProgress.data} /> : null}
        <div className="panel p-5">
          <h2 className="flex items-center gap-2 font-semibold"><Sparkles size={16} /> Stagnující vize</h2>
          <div className="mt-3 grid gap-2 text-sm">
            {stagnating.data?.items.length ? stagnating.data.items.map((item) => (
              <button key={item.vision.id} onClick={() => edit(item.vision)} className="rounded-[var(--radius-sm)] border border-[var(--border)] p-3 text-left hover:bg-[var(--surface-muted)]">
                <span className="font-medium">{item.vision.title}</span>
                <span className="block text-xs text-[var(--warning)]">{item.progress.stagnation_days} dní bez pohybu</span>
              </button>
            )) : <p className="text-[var(--muted)]">Žádná vize nestagnuje déle než 14 dní.</p>}
          </div>
        </div>
        <div className="panel p-5 text-sm text-[var(--muted)]">
          <p className="font-medium text-[var(--foreground)]">Drag & drop</p>
          <p>Přetáhni vizi na jinou vizi pro změnu rodiče, nebo na prázdné místo stromu pro přesun do kořene. Backend hlídá cykly a hloubku max 4.</p>
          <p className="mt-3">Načteno uzlů: {flat.length}</p>
        </div>
      </aside>
    </div>
  );
}

function VisionNode({ node, level, expanded, onToggle, onEdit, onDelete, onDragStart, onDrop }: {
  node: VisionTreeNode;
  level: number;
  expanded: Set<string>;
  onToggle: (id: string) => void;
  onEdit: (vision: Vision) => void;
  onDelete: (id: string) => void;
  onDragStart: (id: string) => void;
  onDrop: (parentId: string | null) => void;
}) {
  const progress = useVisionProgress(node.id);
  const isExpanded = expanded.has(node.id) || level < 1;
  const hasChildren = node.children.length > 0;
  const percent = progress.data && progress.data.total_tasks > 0 ? Math.round((progress.data.done_tasks / progress.data.total_tasks) * 100) : 0;
  const stagnant = (progress.data?.stagnation_days ?? 0) >= 14;
  return (
    <div className="grid gap-2" style={{ marginLeft: level ? 18 : 0 }}>
      <article
        draggable
        onDragStart={() => onDragStart(node.id)}
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => { event.stopPropagation(); onDrop(node.id); }}
        className="rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-3 shadow-sm"
      >
        <div className="grid grid-cols-[auto_1fr_auto] items-start gap-2">
          <button className="mt-1 text-[var(--muted)]" onClick={() => onToggle(node.id)} aria-label="Rozbalit vizi">
            {hasChildren ? isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} /> : <GripVertical size={16} />}
          </button>
          <button onClick={() => onEdit(node)} className="min-w-0 text-left">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="font-semibold tracking-tight">{node.title}</h3>
              <Badge>{horizonLabels[node.horizon]}</Badge>
              {stagnant ? <Badge className="border-[var(--warning)] text-[var(--warning)]">{progress.data?.stagnation_days} dní stagnace</Badge> : null}
            </div>
            {node.description ? <p className="mt-1 line-clamp-2 text-sm text-[var(--muted)]">{node.description}</p> : null}
          </button>
          <Button variant="ghost" size="sm" onClick={() => onDelete(node.id)} aria-label="Smazat vizi"><Trash2 size={15} /></Button>
        </div>
        <div className="mt-3 flex items-center gap-3 text-xs text-[var(--muted)]">
          <div className="h-2 min-w-24 flex-1 overflow-hidden rounded-full bg-[var(--surface-muted)]">
            <div className={cn("h-full rounded-full", percent === 100 ? "bg-[var(--success)]" : "bg-[var(--accent)]")} style={{ width: `${percent}%` }} />
          </div>
          <span>{progress.data?.done_tasks ?? 0}/{progress.data?.total_tasks ?? 0} úkolů</span>
        </div>
      </article>
      {hasChildren && isExpanded ? node.children.map((child) => (
        <VisionNode key={child.id} node={child} level={level + 1} expanded={expanded} onToggle={onToggle} onEdit={onEdit} onDelete={onDelete} onDragStart={onDragStart} onDrop={onDrop} />
      )) : null}
    </div>
  );
}

function ProgressCard({ title, progress }: { title: string; progress?: { total_tasks: number; done_tasks: number; stagnation_days: number | null } }) {
  const percent = progress && progress.total_tasks > 0 ? Math.round((progress.done_tasks / progress.total_tasks) * 100) : 0;
  return (
    <div className="panel p-5">
      <h2 className="font-semibold">Progress: {title}</h2>
      <div className="mt-3 h-3 overflow-hidden rounded-full bg-[var(--surface-muted)]"><div className="h-full bg-[var(--accent)]" style={{ width: `${percent}%` }} /></div>
      <p className="mt-2 text-sm text-[var(--muted)]">{progress?.done_tasks ?? 0}/{progress?.total_tasks ?? 0} úkolů hotovo · {progress?.stagnation_days ?? "—"} dní stagnace</p>
    </div>
  );
}

function Select({ label, children, ...props }: React.SelectHTMLAttributes<HTMLSelectElement> & { label: string }) {
  return <label className="grid gap-1 text-sm font-medium">{label}<select className="focus-ring min-h-11 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-3 text-base" {...props}>{children}</select></label>;
}

function toggleSet(current: Set<string>, id: string) {
  const next = new Set(current);
  if (next.has(id)) next.delete(id); else next.add(id);
  return next;
}

function flatten(nodes: VisionTreeNode[]): Vision[] {
  return nodes.flatMap((node) => [node, ...flatten(node.children)]);
}
