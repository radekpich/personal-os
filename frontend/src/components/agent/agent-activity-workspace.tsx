"use client";

import { RotateCcw, StickyNote, TimerReset, Undo2, WandSparkles } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";
import { ApiError } from "@/lib/api/client";
import {
  useAgentActions,
  useRevertAgentAction,
  useRevertAgentActionBatch,
} from "@/lib/api/hooks";
import type { AgentAction, AgentActionFilters } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const actionLabels: Record<string, string> = {
  create_task: "založil úkol",
  update_task: "upravil úkol",
  complete_task: "dokončil úkol",
  add_note: "přidal poznámku",
  update_note: "upravil poznámku",
  attach_file: "připojil soubor",
  schedule_task: "naplánoval úkol",
  checkin: "zapsal check-in",
  revert_action: "vrátil akci",
  revert_batch: "vrátil dávku",
};

const actionOptions = [
  "create_task",
  "update_task",
  "complete_task",
  "add_note",
  "update_note",
  "attach_file",
  "schedule_task",
  "checkin",
];

function entityHref(action: AgentAction) {
  if (!action.entity_id) return null;
  if (action.entity_type === "task") return `/tasks?task=${action.entity_id}`;
  if (action.entity_type === "note") return `/diary?note=${action.entity_id}`;
  return null;
}

function jsonRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function changedKeys(action: AgentAction) {
  const before = action.before_json;
  const after = jsonRecord(action.result_json);
  if (!before || !after) return [];
  return Array.from(new Set([...Object.keys(before), ...Object.keys(after)]))
    .filter((key) => JSON.stringify(before[key]) !== JSON.stringify(after[key]))
    .sort();
}

function valuePreview(value: unknown) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}

function parseConflict(error: unknown) {
  if (!(error instanceof ApiError) || error.status !== 409) return null;
  const body = error.body as { detail?: unknown } | undefined;
  const detail = body?.detail;
  if (!detail || typeof detail !== "object") return null;
  return detail as Record<string, unknown>;
}

export function AgentActivityWorkspace() {
  const searchParams = useSearchParams();
  const [filters, setFilters] = useState<AgentActionFilters>(() => ({
    action: searchParams.get("action") ?? undefined,
    entity_type: searchParams.get("entity_type") ?? undefined,
    entity_id: searchParams.get("entity_id") ?? undefined,
    only_unreverted: searchParams.get("only_unreverted") !== "false",
    page_size: 80,
  }));
  const [selected, setSelected] = useState<Set<string>>(() => new Set());
  const [conflict, setConflict] = useState<Record<string, unknown> | null>(null);
  const actions = useAgentActions(filters);
  const revert = useRevertAgentAction();
  const revertBatch = useRevertAgentActionBatch();
  const items = useMemo(() => actions.data?.items ?? [], [actions.data?.items]);
  const selectedBatchIds = useMemo(
    () => Array.from(new Set(items.filter((item) => selected.has(item.id)).map((item) => item.batch_id).filter(Boolean))),
    [items, selected],
  );

  function toggle(id: string) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function revertOne(id: string) {
    setConflict(null);
    try {
      await revert.mutateAsync(id);
      setSelected((current) => {
        const next = new Set(current);
        next.delete(id);
        return next;
      });
    } catch (error) {
      const detail = parseConflict(error);
      if (detail) setConflict(detail);
      else throw error;
    }
  }

  async function bulkRevert() {
    setConflict(null);
    try {
      if (selectedBatchIds.length === 1) {
        await revertBatch.mutateAsync({ batch_id: selectedBatchIds[0] });
      } else {
        for (const id of selected) await revert.mutateAsync(id);
      }
      setSelected(new Set());
    } catch (error) {
      const detail = parseConflict(error);
      if (detail) setConflict(detail);
      else throw error;
    }
  }

  return (
    <section className="grid gap-6">
      <div className="panel grid gap-4 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[.16em] text-[var(--muted)]">Agent</p>
            <h2 className="text-2xl font-semibold tracking-tight">Aktivita</h2>
            <p className="text-sm text-[var(--muted)]">
              Časová osa toho, co agent uvnitř aplikace založil, změnil nebo dokončil.
            </p>
          </div>
          <Button disabled={selected.size === 0 || revert.isPending || revertBatch.isPending} onClick={bulkRevert}>
            <RotateCcw size={16} /> Vrátit vybrané ({selected.size})
          </Button>
        </div>

        <div className="grid gap-3 md:grid-cols-5">
          <label className="grid gap-1 text-xs font-medium uppercase tracking-[.14em] text-[var(--muted)]">
            Typ akce
            <select
              className="focus-ring min-h-11 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-3 text-sm normal-case tracking-normal text-[var(--foreground)]"
              value={filters.action ?? "all"}
              onChange={(event) => setFilters({ ...filters, action: event.target.value })}
            >
              <option value="all">Vše</option>
              {actionOptions.map((action) => <option key={action} value={action}>{actionLabels[action]}</option>)}
            </select>
          </label>
          <label className="grid gap-1 text-xs font-medium uppercase tracking-[.14em] text-[var(--muted)]">
            Zdroj
            <Input value={filters.source ?? ""} onChange={(event) => setFilters({ ...filters, source: event.target.value })} placeholder="telegram" />
          </label>
          <label className="grid gap-1 text-xs font-medium uppercase tracking-[.14em] text-[var(--muted)]">
            Source system
            <Input value={filters.source_system ?? ""} onChange={(event) => setFilters({ ...filters, source_system: event.target.value })} placeholder="calendar" />
          </label>
          <label className="grid gap-1 text-xs font-medium uppercase tracking-[.14em] text-[var(--muted)]">
            Od
            <Input type="datetime-local" onChange={(event) => setFilters({ ...filters, created_from: event.target.value || undefined })} />
          </label>
          <label className="flex items-end gap-2 text-sm text-[var(--muted)]">
            <input
              type="checkbox"
              checked={Boolean(filters.only_unreverted)}
              onChange={(event) => setFilters({ ...filters, only_unreverted: event.target.checked })}
            />
            jen nevrácené
          </label>
        </div>

        {filters.entity_type && filters.entity_id ? (
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-[var(--radius-sm)] border border-[var(--accent)]/40 bg-[var(--accent)]/5 p-3 text-sm">
            <span>
              Zobrazuji aktivitu pro {filters.entity_type} <code>{filters.entity_id}</code>.
            </span>
            <Button variant="ghost" size="sm" onClick={() => setFilters({ ...filters, entity_type: undefined, entity_id: undefined, action: undefined })}>
              Zobrazit vše
            </Button>
          </div>
        ) : null}
      </div>

      {conflict ? <ConflictPreview detail={conflict} /> : null}

      <div className="grid gap-3">
        {actions.isLoading ? <div className="panel p-6 text-sm text-[var(--muted)]">Načítám aktivitu…</div> : null}
        {items.map((action) => (
          <ActionCard
            key={action.id}
            action={action}
            checked={selected.has(action.id)}
            onToggle={() => toggle(action.id)}
            onRevert={() => revertOne(action.id)}
            pending={revert.isPending || revertBatch.isPending}
          />
        ))}
        {!actions.isLoading && items.length === 0 ? (
          <div className="panel p-8 text-center text-sm text-[var(--muted)]">Zatím tu není žádná agentí akce.</div>
        ) : null}
      </div>
    </section>
  );
}

function ActionCard({
  action,
  checked,
  onToggle,
  onRevert,
  pending,
}: {
  action: AgentAction;
  checked: boolean;
  onToggle: () => void;
  onRevert: () => void;
  pending: boolean;
}) {
  const href = entityHref(action);
  const Icon = action.entity_type === "note" ? StickyNote : action.action.includes("complete") ? TimerReset : WandSparkles;
  const keys = changedKeys(action);
  return (
    <article className={cn("panel grid gap-3 p-5", action.reverted_at && "opacity-55")}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <input type="checkbox" checked={checked} disabled={Boolean(action.reverted_at)} onChange={onToggle} className="mt-1" />
          <div className="flex size-10 shrink-0 items-center justify-center rounded-full bg-[var(--surface-muted)] text-[var(--accent)]">
            <Icon size={18} />
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="font-semibold">{actionLabels[action.action] ?? action.action}</h3>
              <Badge>{action.source}</Badge>
              {action.source_system ? <Badge>{action.source_system}</Badge> : null}
              {action.batch_id ? <Badge>dávka {action.batch_id}</Badge> : null}
              {action.reverted_at ? <Badge className="border-[var(--muted)] text-[var(--muted)]">vráceno</Badge> : null}
            </div>
            <p className="mt-1 text-sm text-[var(--muted)]">{new Intl.DateTimeFormat("cs-CZ", { dateStyle: "medium", timeStyle: "short" }).format(new Date(action.created_at))}</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {href ? <Button asChild variant="secondary" size="sm"><Link href={href}>Otevřít záznam</Link></Button> : null}
          <Button variant="ghost" size="sm" disabled={Boolean(action.reverted_at) || pending} onClick={onRevert}>
            <Undo2 size={15} /> Vrátit
          </Button>
        </div>
      </div>

      <p className="rounded-[var(--radius-sm)] bg-[var(--surface-muted)] p-3 text-sm">{action.reasoning}</p>

      {keys.length > 0 ? (
        <details className="rounded-[var(--radius-sm)] border border-[var(--border)] p-3 text-sm">
          <summary className="cursor-pointer font-medium">Porovnání před / po ({keys.length})</summary>
          <div className="mt-3 grid gap-2">
            {keys.map((key) => {
              const after = jsonRecord(action.result_json);
              return (
                <div key={key} className="grid gap-2 rounded-[var(--radius-sm)] bg-[var(--surface-muted)] p-3 md:grid-cols-[11rem_1fr_1fr]">
                  <span className="font-mono text-xs text-[var(--muted)]">{key}</span>
                  <span><span className="text-xs text-[var(--muted)]">Před:</span> {valuePreview(action.before_json?.[key])}</span>
                  <span><span className="text-xs text-[var(--muted)]">Po:</span> {valuePreview(after?.[key])}</span>
                </div>
              );
            })}
          </div>
        </details>
      ) : null}
    </article>
  );
}

function ConflictPreview({ detail }: { detail: Record<string, unknown> }) {
  return (
    <div className="panel border-[var(--warning)] bg-[var(--warning)]/10 p-5">
      <h3 className="font-semibold">Nelze vrátit bez rozhodnutí</h3>
      <p className="mt-1 text-sm text-[var(--muted)]">
        Záznam mezitím upravil člověk. Revert jsem zastavil a tady je náhled rozdílu.
      </p>
      <pre className="mt-3 max-h-80 overflow-auto rounded-[var(--radius-sm)] bg-[var(--surface)] p-3 text-xs">
        {JSON.stringify(detail, null, 2)}
      </pre>
    </div>
  );
}
