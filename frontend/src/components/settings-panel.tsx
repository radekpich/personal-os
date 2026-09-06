"use client";

import { Check, Copy, RefreshCcw } from "lucide-react";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, calendarUrl } from "@/lib/api/client";
import { queryKeys, useMe, useStorageUsage } from "@/lib/api/hooks";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  return `${(kb / 1024).toFixed(1)} MB`;
}

export function SettingsPanel() {
  const { data: me, isLoading } = useMe();
  const storage = useStorageUsage();
  const queryClient = useQueryClient();
  const [copied, setCopied] = useState(false);
  const regenerate = useMutation({ mutationFn: api.regenerateCalendarToken, onSuccess: (user) => queryClient.setQueryData(queryKeys.me, user) });
  const url = me ? calendarUrl(me.calendar_token) : "";

  async function copy() {
    if (!url) return;
    await navigator.clipboard.writeText(url);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }

  if (isLoading) return <div className="panel p-6 text-[var(--muted)]">Načítám nastavení…</div>;
  return (
    <div className="grid max-w-3xl gap-5">
      <section className="panel p-5 sm:p-6">
        <h2 className="text-xl font-semibold">Profil</h2>
        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          <label className="grid gap-1 text-sm font-medium">Jméno<Input readOnly value={me?.display_name ?? ""} /></label>
          <label className="grid gap-1 text-sm font-medium">Email<Input readOnly value={me?.email ?? ""} /></label>
          <label className="grid gap-1 text-sm font-medium">Timezone<Input readOnly value={me?.timezone ?? "Europe/Prague"} /></label>
        </div>
        <p className="mt-3 text-sm text-[var(--muted)]">Úprava profilu zatím není v backendu vystavená; frontend hodnoty bezpečně zobrazuje.</p>
      </section>
      <section className="panel p-5 sm:p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold">Úložiště příloh</h2>
            <p className="mt-1 text-sm text-[var(--muted)]">Fotky, PDF a náhledy uložené v Personal OS.</p>
          </div>
          <Button type="button" variant="secondary" size="sm" onClick={() => void storage.refetch()} disabled={storage.isFetching}>
            <RefreshCcw size={14} />Obnovit
          </Button>
        </div>
        {storage.isLoading ? (
          <p className="mt-4 text-sm text-[var(--muted)]">Načítám využití úložiště…</p>
        ) : storage.data ? (
          <div className="mt-5 grid gap-3">
            <div className="h-3 overflow-hidden rounded-full bg-[var(--surface-muted)]">
              <div className="h-full rounded-full bg-[var(--primary)]" style={{ width: `${Math.min(100, storage.data.used_percent)}%` }} />
            </div>
            <div className="grid gap-2 text-sm text-[var(--muted)] sm:grid-cols-3">
              <div><span className="font-medium text-[var(--foreground)]">{formatBytes(storage.data.used_bytes)}</span><br />využito</div>
              <div><span className="font-medium text-[var(--foreground)]">{formatBytes(storage.data.remaining_bytes)}</span><br />zbývá</div>
              <div><span className="font-medium text-[var(--foreground)]">{storage.data.file_count}</span><br />souborů</div>
            </div>
            <p className="text-xs text-[var(--muted)]">Limit: {formatBytes(storage.data.max_bytes)} · využití {storage.data.used_percent.toFixed(1)} %</p>
          </div>
        ) : (
          <p className="mt-4 text-sm text-[var(--danger)]">Využití úložiště se nepodařilo načíst.</p>
        )}
      </section>
      <section className="panel p-5 sm:p-6">
        <h2 className="text-xl font-semibold">Kalendářový odkaz</h2>
        <p className="mt-1 text-sm text-[var(--muted)]">Read-only iCalendar feed pro Google/Apple/Outlook kalendář.</p>
        <div className="mt-4 flex flex-col gap-2 sm:flex-row"><Input readOnly value={url} /><Button variant="secondary" onClick={copy}>{copied ? <Check size={16}/> : <Copy size={16}/>}Kopírovat</Button><Button variant="secondary" onClick={() => regenerate.mutate()} disabled={regenerate.isPending}><RefreshCcw size={16}/>{regenerate.isPending ? "Generuji…" : "Přegenerovat"}</Button></div>
        {regenerate.isSuccess ? <p className="mt-3 text-sm text-[var(--success)]">Token byl přegenerovaný. Starý odkaz přestal fungovat.</p> : null}
      </section>
      <section className="panel p-5 sm:p-6">
        <h2 className="text-xl font-semibold">Klávesové zkratky</h2>
        <dl className="mt-4 grid gap-2 text-sm text-[var(--muted)] sm:grid-cols-2"><dt>Cmd/Ctrl+N</dt><dd>Rychlý zápis</dd><dt>Cmd/Ctrl+K</dt><dd>Command palette</dd><dt>Cmd/Ctrl+1–4</dt><dd>Pohledy: Dashboard, Úkoly, Inbox, Nastavení</dd></dl>
      </section>
    </div>
  );
}
