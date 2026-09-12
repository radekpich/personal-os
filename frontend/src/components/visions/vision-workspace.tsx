"use client";

import { ChevronDown, ChevronRight, GripVertical, Plus, Sparkles } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
import {
  useDeleteVision,
  useStagnatingVisions,
  useTasks,
  useVisionDeleteImpact,
  useVisionProgress,
  useVisionTree,
} from "@/lib/api/hooks";
import type { Vision, VisionHorizon, VisionTreeNode } from "@/lib/api/types";
import { cn, formatHumanDate } from "@/lib/utils";
import { formatCzechCount } from "@/lib/czech";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ActionButton } from "@/components/ui/action-buttons";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { MarkdownPreview } from "@/components/markdown-preview";
import { VisionDialog } from "@/components/visions/vision-dialog";

const horizonLabels: Record<VisionHorizon, string> = {
  life: "Život",
  "5y": "5 let",
  "1y": "1 rok",
  quarter: "Kvartál",
};

export function VisionWorkspace() {
  const tree = useVisionTree();
  const remove = useDeleteVision();
  const stagnating = useStagnatingVisions(14);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [expandedDetailId, setExpandedDetailId] = useState<string | null>(null);
  const [draggedId, setDraggedId] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingVision, setEditingVision] = useState<Vision | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Vision | null>(null);
  const [deleteChildren, setDeleteChildren] = useState(false);

  const nodes = useMemo(() => tree.data?.items ?? [], [tree.data?.items]);
  const flat = useMemo(() => flatten(nodes), [nodes]);
  const impact = useVisionDeleteImpact(deleteTarget?.id ?? null);

  function openCreate() {
    setEditingVision(null);
    setDialogOpen(true);
  }

  function openEdit(vision: Vision) {
    setEditingVision(vision);
    setDialogOpen(true);
  }

  function toggleDetail(id: string) {
    setExpandedDetailId((current) => (current === id ? null : id));
  }

  function requestDelete(vision: Vision) {
    setDeleteChildren(false);
    setDeleteTarget(vision);
  }

  async function confirmDelete() {
    if (!deleteTarget) return;
    await remove.mutateAsync({ id: deleteTarget.id, deleteChildren });
    if (expandedDetailId === deleteTarget.id) setExpandedDetailId(null);
    setDeleteTarget(null);
  }

  async function moveVision(targetParentId: string | null) {
    if (!draggedId || draggedId === targetParentId) return;
    const { api } = await import("@/lib/api/client");
    await api.updateVision(draggedId, { parent_id: targetParentId });
    setExpanded((current) => new Set([...current, targetParentId ?? "root"]));
    setDraggedId(null);
    await tree.refetch();
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_24rem]">
      <section className="grid gap-4">
        <div className="panel flex flex-wrap items-center justify-between gap-3 p-5">
          <div>
            <p className="text-sm text-[var(--muted)]">Sny → cíle → milníky → konkrétní kroky.</p>
            <h2 className="text-xl font-semibold">Strom dlouhodobých cílů</h2>
          </div>
          <Button onClick={openCreate}>
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
                expandedDetailId={expandedDetailId}
                onToggle={(id) => setExpanded((current) => toggleSet(current, id))}
                onToggleDetail={toggleDetail}
                onEdit={openEdit}
                onDelete={requestDelete}
                onDragStart={setDraggedId}
                onDrop={moveVision}
              />
            ))}
          </div>
        </div>
      </section>
      <aside className="grid h-fit gap-4">
        <div className="panel p-5">
          <h2 className="flex items-center gap-2 font-semibold"><Sparkles size={16} /> Stagnující vize</h2>
          <div className="mt-3 grid gap-2 text-sm">
            {stagnating.data?.items.length ? stagnating.data.items.map((item) => (
              <button key={item.vision.id} onClick={() => toggleDetail(item.vision.id)} className="rounded-[var(--radius-sm)] border border-[var(--border)] p-3 text-left hover:bg-[var(--surface-muted)]">
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

      <VisionDialog open={dialogOpen} vision={editingVision} onClose={() => setDialogOpen(false)} />

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title={`Smazat vizi „${deleteTarget?.title ?? ""}“?`}
        description="Tuto akci nejde vrátit zpět."
        confirmLabel="Smazat vizi"
        onConfirm={confirmDelete}
        onCancel={() => setDeleteTarget(null)}
        confirmDisabled={remove.isPending}
      >
        <div className="grid gap-3 text-sm">
          {impact.data && impact.data.task_count > 0 ? (
            <fieldset className="grid gap-2 rounded-[var(--radius-lg)] border border-[var(--warning)] bg-[var(--warning)]/10 p-3 text-[var(--warning)]">
              <legend className="px-1 font-semibold">Co s {formatCzechCount(impact.data.task_count, "navázaným úkolem", "navázanými úkoly", "navázanými úkoly")}?</legend>
              <label className="flex items-start gap-2 text-[var(--foreground)]">
                <input type="radio" checked readOnly />
                <span><strong>Zachovat úkoly</strong> — úkoly zůstanou v seznamu, jen se jim odebere vazba na mazanou vizi.</span>
              </label>
            </fieldset>
          ) : null}
          {impact.data && impact.data.child_count > 0 ? (
            <fieldset className="grid gap-2 rounded-[var(--radius-lg)] border border-[var(--border)] p-3">
              <legend className="px-1 font-semibold">Co s {formatCzechCount(impact.data.child_count, "podřízenou vizí", "podřízenými vizemi", "podřízenými vizemi")}?</legend>
              <label className="flex items-start gap-2">
                <input type="radio" checked={!deleteChildren} onChange={() => setDeleteChildren(false)} />
                <span><strong>Posunout nahoru</strong> — podřízené vize se přesunou k nadřazené vizi (nebo do kořene).</span>
              </label>
              <label className="flex items-start gap-2">
                <input type="radio" checked={deleteChildren} onChange={() => setDeleteChildren(true)} />
                <span><strong>Smazat i podřízené vize</strong> — celý podstrom zmizí spolu s touto vizí.</span>
              </label>
            </fieldset>
          ) : null}
        </div>
      </ConfirmDialog>
    </div>
  );
}

function VisionNode({ node, level, expanded, expandedDetailId, onToggle, onToggleDetail, onEdit, onDelete, onDragStart, onDrop }: {
  node: VisionTreeNode;
  level: number;
  expanded: Set<string>;
  expandedDetailId: string | null;
  onToggle: (id: string) => void;
  onToggleDetail: (id: string) => void;
  onEdit: (vision: Vision) => void;
  onDelete: (vision: Vision) => void;
  onDragStart: (id: string) => void;
  onDrop: (parentId: string | null) => void;
}) {
  const progress = useVisionProgress(node.id);
  const isExpanded = expanded.has(node.id) || level < 1;
  const hasChildren = node.children.length > 0;
  const detailOpen = expandedDetailId === node.id;
  const percent = progress.data && progress.data.total_tasks > 0 ? Math.round((progress.data.done_tasks / progress.data.total_tasks) * 100) : 0;
  const stagnant = (progress.data?.stagnation_days ?? 0) >= 14;
  return (
    <div className="grid gap-2" style={{ marginLeft: level ? 18 : 0 }}>
      <article
        draggable
        onDragStart={() => onDragStart(node.id)}
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => { event.stopPropagation(); onDrop(node.id); }}
        className={cn("rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-3 shadow-sm", detailOpen && "border-[var(--accent)]")}
      >
        <div className="grid grid-cols-[auto_1fr_auto] items-start gap-2">
          <button className="mt-1 text-[var(--muted)]" onClick={() => onToggle(node.id)} aria-label="Rozbalit podřízené vize">
            {hasChildren ? isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} /> : <GripVertical size={16} />}
          </button>
          <button onClick={() => onToggleDetail(node.id)} className="min-w-0 text-left" aria-label={`Detail vize ${node.title}`}>
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="font-semibold tracking-tight">{node.title}</h3>
              <Badge>{horizonLabels[node.horizon]}</Badge>
              {stagnant ? <Badge className="border-[var(--warning)] text-[var(--warning)]">{progress.data?.stagnation_days} dní stagnace</Badge> : null}
            </div>
            {node.description ? <MarkdownPreview compact className="mt-1 text-sm text-[var(--muted)]">{node.description}</MarkdownPreview> : null}
          </button>
          <div className="flex gap-0.5">
            <ActionButton icon="edit" label="Upravit vizi" onClick={() => onEdit(node)} />
            <ActionButton icon="delete" label="Smazat vizi" danger onClick={() => onDelete(node)} />
          </div>
        </div>
        <div className="mt-3 flex items-center gap-3 text-xs text-[var(--muted)]">
          <div className="h-2 min-w-24 flex-1 overflow-hidden rounded-full bg-[var(--surface-muted)]">
            <div className={cn("h-full rounded-full", percent === 100 ? "bg-[var(--success)]" : "bg-[var(--accent)]")} style={{ width: `${percent}%` }} />
          </div>
          <span>{progress.data?.done_tasks ?? 0}/{progress.data?.total_tasks ?? 0} úkolů</span>
        </div>
        {detailOpen ? <VisionDetail vision={node} /> : null}
      </article>
      {hasChildren && isExpanded ? node.children.map((child) => (
        <VisionNode key={child.id} node={child} level={level + 1} expanded={expanded} expandedDetailId={expandedDetailId} onToggle={onToggle} onToggleDetail={onToggleDetail} onEdit={onEdit} onDelete={onDelete} onDragStart={onDragStart} onDrop={onDrop} />
      )) : null}
    </div>
  );
}

function VisionDetail({ vision }: { vision: VisionTreeNode }) {
  const progress = useVisionProgress(vision.id);
  const tasks = useTasks({ vision_id: vision.id, page_size: 50 });
  return (
    <div className="mt-4 grid gap-4 border-t border-[var(--border)] pt-4 text-sm">
      {vision.description ? (
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">Popis</p>
          <MarkdownPreview className="mt-1 text-sm">{vision.description}</MarkdownPreview>
        </div>
      ) : null}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Metric label="Horizont" value={horizonLabels[vision.horizon]} />
        <Metric label="Cílové datum" value={vision.target_date ? formatHumanDate(vision.target_date) : "Bez termínu"} />
        <Metric label="Progres" value={`${progress.data?.done_tasks ?? 0}/${progress.data?.total_tasks ?? 0}`} />
        <Metric label="Stagnace" value={progress.data?.stagnation_days != null ? formatCzechCount(progress.data.stagnation_days, "den", "dny", "dní") : "—"} />
      </div>
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">Propojené úkoly</p>
        {tasks.isLoading ? <p className="mt-1 text-[var(--muted)]">Načítám úkoly…</p> : null}
        {!tasks.isLoading && !tasks.data?.items.length ? <p className="mt-1 text-[var(--muted)]">Žádné propojené úkoly.</p> : null}
        <ul className="mt-2 grid gap-1.5">
          {tasks.data?.items.map((task) => (
            <li key={task.id}>
              <Link href={`/tasks?selected=${task.id}`} className="text-[var(--accent)] hover:underline">
                {task.title}
              </Link>
            </li>
          ))}
        </ul>
      </div>
      {vision.children.length ? (
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">Podřízené vize</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {vision.children.map((child) => <Badge key={child.id}>{child.title}</Badge>)}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return <div className="rounded-[var(--radius-md)] bg-[var(--surface-muted)] p-2.5"><p className="text-xs text-[var(--muted)]">{label}</p><p className="font-semibold">{value}</p></div>;
}

function toggleSet(current: Set<string>, id: string) {
  const next = new Set(current);
  if (next.has(id)) next.delete(id); else next.add(id);
  return next;
}

function flatten(nodes: VisionTreeNode[]): Vision[] {
  return nodes.flatMap((node) => [node, ...flatten(node.children)]);
}
