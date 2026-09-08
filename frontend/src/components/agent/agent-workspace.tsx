"use client";

import { AlertTriangle, CheckCircle2, KeyRound, LockKeyhole, PlayCircle, ShieldAlert, SlidersHorizontal } from "lucide-react";
import type { ReactNode } from "react";
import { useState } from "react";
import { AgentActivityWorkspace } from "@/components/agent/agent-activity-workspace";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  useAcknowledgeAgentConfigChange,
  useAgentConfigChanges,
  useAgentChannels,
  useAgentIntegrations,
  useAgentJobs,
  useAgentKeys,
  useAgentOverview,
  useAgentRuns,
  useAgentWatches,
  useRevokeAllAgentKeys,
} from "@/lib/api/hooks";
import type { AgentChannel, AgentConfigChange, AgentIntegration, AgentJob, AgentKey, AgentRun, AgentWatch } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const tabs = ["Aktivita", "Přehled", "Úlohy", "Přístupy", "Hlídání", "Historie", "Změny", "Klíče"] as const;
type AgentTab = (typeof tabs)[number];

function formatDate(value: string | null | undefined) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("cs-CZ", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function statusTone(status: string | null | undefined) {
  if (status === "success" || status === "active" || status === "running") return "border-emerald-500/40 text-emerald-700";
  if (status === "error" || status === "expired" || status === "stale") return "border-red-500/40 text-red-700";
  return "border-[var(--border)] text-[var(--muted)]";
}

export function AgentWorkspace() {
  const [tab, setTab] = useState<AgentTab>("Přehled");
  return (
    <section className="grid gap-5">
      <div className="panel p-3">
        <div className="flex gap-2 overflow-x-auto">
          {tabs.map((item) => (
            <Button key={item} variant={tab === item ? "default" : "ghost"} size="sm" onClick={() => setTab(item)}>
              {item}
            </Button>
          ))}
        </div>
      </div>
      {tab === "Aktivita" ? <AgentActivityWorkspace /> : null}
      {tab === "Přehled" ? <OverviewTab /> : null}
      {tab === "Úlohy" ? <JobsTab /> : null}
      {tab === "Přístupy" ? <IntegrationsTab /> : null}
      {tab === "Hlídání" ? <WatchesTab /> : null}
      {tab === "Historie" ? <RunsTab /> : null}
      {tab === "Změny" ? <ChangesTab /> : null}
      {tab === "Klíče" ? <KeysTab /> : null}
    </section>
  );
}

function OverviewTab() {
  const overview = useAgentOverview();
  const changes = useAgentConfigChanges({ acknowledged: false });
  const channels = useAgentChannels();
  const data = overview.data;
  return (
    <div className="grid gap-4">
      {(data?.unacknowledged_change_count ?? 0) > 0 ? (
        <div className="rounded-[var(--radius)] border border-amber-500/40 bg-amber-500/10 p-4 text-sm text-amber-900">
          <strong>Nepotvrzené změny konfigurace:</strong> {data?.unacknowledged_change_count}. Zkontroluj záložku Změny — mohl přibýt nový přístup nebo úloha.
        </div>
      ) : null}
      <div className="grid gap-3 md:grid-cols-4">
        <Metric title="Stav" value={data?.agent?.status ?? "unknown"} icon={<CheckCircle2 size={18} />} tone={statusTone(data?.agent?.status)} />
        <Metric title="Heartbeat" value={formatDate(data?.agent?.last_heartbeat_at)} />
        <Metric title="Aktivní úlohy" value={String(data?.active_job_count ?? 0)} />
        <Metric title="Aktivní přístupy" value={String(data?.active_integration_count ?? 0)} />
        <Metric title="Běhy za 24 h" value={String(data?.run_count_24h ?? 0)} />
        <Metric title="Spotřeba měsíc" value={`${(data?.cost_estimate_month ?? 0).toFixed(2)} $`} />
        <Metric title="Agent" value={data?.agent ? `${data.agent.name}@${data.agent.host}` : "—"} />
        <Metric title="Config hash" value={data?.agent?.config_hash ?? "—"} />
      </div>
      {(data?.warnings ?? []).length > 0 ? (
        <div className="panel grid gap-2 p-4">
          <h3 className="flex items-center gap-2 font-semibold text-red-700"><AlertTriangle size={18} /> Varování</h3>
          {data?.warnings.map((warning) => <p key={warning} className="text-sm text-[var(--muted)]">{warning}</p>)}
        </div>
      ) : null}
      <ListPanel title="Kanály" items={channels.data?.items ?? []} render={(channel: AgentChannel) => (
        <div className="grid gap-2 rounded-[var(--radius-sm)] border border-[var(--border)] p-4 md:grid-cols-4">
          <strong>{channel.channel_type}</strong>
          <code>{channel.identifier}</code>
          <Badge>{channel.is_active ? "aktivní" : "vypnuto"}</Badge>
          <p className="text-sm text-[var(--muted)]">24 h: {channel.message_count_24h} · měsíc: {channel.message_count_month}<br />Poslední: {formatDate(channel.last_message_at)}</p>
        </div>
      )} />
      <ListPanel title="Poslední nepotvrzené změny" items={changes.data?.items ?? []} render={(change) => <ChangeRow change={change} compact />} />
    </div>
  );
}

function Metric({ title, value, icon, tone }: { title: string; value: string; icon?: ReactNode; tone?: string }) {
  return (
    <div className={cn("panel p-4", tone)}>
      <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[.14em] text-[var(--muted)]">{icon}{title}</p>
      <p className="mt-2 break-words text-xl font-semibold">{value}</p>
    </div>
  );
}

function JobsTab() {
  const jobs = useAgentJobs();
  return <ListPanel title="Úlohy" items={jobs.data?.items ?? []} render={(job: AgentJob) => (
    <div className="grid gap-2 rounded-[var(--radius-sm)] border border-[var(--border)] p-4 md:grid-cols-5">
      <div className="md:col-span-2"><p className="font-semibold">{job.name}</p><p className="text-sm text-[var(--muted)]">{job.description ?? "—"}</p></div>
      <p className="text-sm">{job.schedule_description ?? job.schedule ?? "—"}</p>
      <p className="text-sm">Poslední: {formatDate(job.last_run_at)}<br /><Badge className={statusTone(job.last_status)}>{job.last_status ?? "unknown"}</Badge></p>
      <p className="text-sm">Příští: {formatDate(job.next_run_at)}<br />Běhů: {job.run_count}, selhání: {job.consecutive_failures}</p>
    </div>
  )} />;
}

function IntegrationsTab() {
  const integrations = useAgentIntegrations();
  const grouped = new Map<string, AgentIntegration[]>();
  for (const item of integrations.data?.items ?? []) grouped.set(item.kind, [...(grouped.get(item.kind) ?? []), item]);
  return (
    <div className="grid gap-4">
      {Array.from(grouped.entries()).map(([kind, items]) => (
        <ListPanel key={kind} title={kind} items={items} render={(integration) => <IntegrationCard integration={integration} />} />
      ))}
    </div>
  );
}

function IntegrationCard({ integration }: { integration: AgentIntegration }) {
  const writable = integration.scopes.some((scope) => /write|modify|delete|send|create/i.test(scope));
  return (
    <div className={cn("rounded-[var(--radius-sm)] border p-4", writable ? "border-amber-500/50 bg-amber-500/5" : "border-[var(--border)]")}>
      <div className="flex flex-wrap items-center gap-2"><h3 className="font-semibold">{integration.name}</h3><Badge className={statusTone(integration.status)}>{integration.status}</Badge>{writable ? <Badge>zápisový přístup</Badge> : <Badge>read-only</Badge>}</div>
      <p className="mt-2 text-sm text-[var(--muted)]">Scopes: {integration.scopes.join(", ") || "—"}</p>
      <p className="text-xs text-[var(--muted)]">Poslední použití: {formatDate(integration.last_used_at)} · Chyby: {integration.error_count}</p>
    </div>
  );
}

function WatchesTab() {
  const watches = useAgentWatches();
  return <ListPanel title="Hlídání" items={watches.data?.items ?? []} render={(watch: AgentWatch) => (
    <div className="rounded-[var(--radius-sm)] border border-[var(--border)] p-4">
      <div className="flex flex-wrap items-center gap-2"><h3 className="font-semibold">{watch.name}</h3><Badge>{watch.kind}</Badge>{watch.is_active ? <Badge>aktivní</Badge> : <Badge>vypnuto</Badge>}</div>
      <p className="text-sm text-[var(--muted)]">{watch.description ?? "—"}</p>
      <p className="text-xs text-[var(--muted)]">Kontrola: {formatDate(watch.last_checked_at)} · Trigger: {formatDate(watch.last_triggered_at)} · Počet: {watch.trigger_count}</p>
      <pre className="mt-2 overflow-x-auto rounded bg-[var(--surface-muted)] p-2 text-xs">{JSON.stringify(watch.config_json, null, 2)}</pre>
    </div>
  )} />;
}

function RunsTab() {
  const [q, setQ] = useState("");
  const [trigger, setTrigger] = useState("");
  const [status, setStatus] = useState("");
  const runs = useAgentRuns({ q, trigger, status, page_size: 50 });
  return (
    <div className="grid gap-4">
      <div className="panel grid gap-3 p-4 md:grid-cols-3">
        <Input value={q} onChange={(event) => setQ(event.target.value)} placeholder="Hledat ve shrnutí" />
        <Input value={trigger} onChange={(event) => setTrigger(event.target.value)} placeholder="trigger: schedule/telegram" />
        <Input value={status} onChange={(event) => setStatus(event.target.value)} placeholder="status: success/error" />
      </div>
      <ListPanel title="Historie běhů" items={runs.data?.items ?? []} render={(run: AgentRun) => (
        <div className="rounded-[var(--radius-sm)] border border-[var(--border)] p-4">
          <div className="flex flex-wrap items-center gap-2"><PlayCircle size={16} /><strong>{run.summary}</strong><Badge className={statusTone(run.status)}>{run.status}</Badge><Badge>{run.trigger}</Badge></div>
          <p className="text-sm text-[var(--muted)]">{formatDate(run.started_at)} · {run.duration_ms ?? 0} ms · tokens {run.tokens_used ?? 0} · cost {(run.cost_estimate ?? 0).toFixed(3)} $</p>
          {run.detail ? <p className="mt-2 text-sm">{run.detail}</p> : null}
          {run.error ? <p className="mt-2 text-sm text-red-700">{run.error}</p> : null}
        </div>
      )} />
    </div>
  );
}

function ChangesTab() {
  const changes = useAgentConfigChanges();
  const ack = useAcknowledgeAgentConfigChange();
  return <ListPanel title="Změny konfigurace" items={changes.data?.items ?? []} render={(change: AgentConfigChange) => <ChangeRow change={change} onAck={() => ack.mutate(change.id)} />} />;
}

function ChangeRow({ change, compact, onAck }: { change: AgentConfigChange; compact?: boolean; onAck?: () => void }) {
  return (
    <div className="rounded-[var(--radius-sm)] border border-[var(--border)] p-4">
      <div className="flex flex-wrap items-center justify-between gap-2"><div className="flex flex-wrap items-center gap-2"><ShieldAlert size={16} /><strong>{change.target_type}: {change.target_name}</strong><Badge>{change.change_type}</Badge>{!change.acknowledged_at ? <Badge>nová</Badge> : null}</div>{onAck && !change.acknowledged_at ? <Button size="sm" onClick={onAck}>Potvrdit</Button> : null}</div>
      <p className="text-xs text-[var(--muted)]">{formatDate(change.timestamp)}</p>
      {!compact ? <pre className="mt-2 max-h-80 overflow-auto rounded bg-[var(--surface-muted)] p-2 text-xs">{JSON.stringify(change.diff_json, null, 2)}</pre> : null}
    </div>
  );
}

function KeysTab() {
  const keys = useAgentKeys();
  const revokeAll = useRevokeAllAgentKeys();
  function confirmRevoke() {
    if (window.confirm("Opravdu okamžitě zneplatnit všechny agentní API klíče?")) revokeAll.mutate();
  }
  return (
    <div className="grid gap-4">
      <div className="rounded-[var(--radius)] border-2 border-red-500/50 bg-red-500/5 p-4">
        <h3 className="flex items-center gap-2 font-semibold text-red-700"><LockKeyhole size={18} /> Nouzové odebrání přístupu</h3>
        <p className="mt-1 text-sm text-[var(--muted)]">Zneplatní všechny agentní klíče okamžitě, ne až po vypršení cache.</p>
        <Button className="mt-3" variant="danger" onClick={confirmRevoke} disabled={revokeAll.isPending}>Zneplatnit všechny agentní klíče</Button>
      </div>
      <ListPanel title="Klíče" items={keys.data?.items ?? []} render={(key: AgentKey) => (
        <div className="grid gap-2 rounded-[var(--radius-sm)] border border-[var(--border)] p-4 md:grid-cols-4">
          <div className="flex items-center gap-2"><KeyRound size={16} /><strong>{key.name}</strong></div>
          <code>{key.key_prefix}…</code>
          <p className="text-sm text-[var(--muted)]">{key.scopes.join(", ")}</p>
          <p className="text-sm text-[var(--muted)]">Použití: {formatDate(key.last_used_at)}<br />Revokace: {formatDate(key.revoked_at)}</p>
        </div>
      )} />
    </div>
  );
}

function ListPanel<T>({ title, items, render }: { title: string; items: T[]; render: (item: T) => ReactNode }) {
  return (
    <div className="panel grid gap-3 p-5">
      <h2 className="flex items-center gap-2 text-xl font-semibold"><SlidersHorizontal size={18} /> {title}</h2>
      {items.length === 0 ? <p className="text-sm text-[var(--muted)]">Zatím žádná data. Panel ukazuje jen to, co agent nahlásí.</p> : null}
      {items.map((item, index) => <div key={index}>{render(item)}</div>)}
    </div>
  );
}
