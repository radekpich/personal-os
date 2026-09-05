"use client";

import { Check, Copy, RefreshCcw } from "lucide-react";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, calendarUrl } from "@/lib/api/client";
import { queryKeys, useMe } from "@/lib/api/hooks";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function SettingsPanel() {
  const { data: me, isLoading } = useMe();
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
