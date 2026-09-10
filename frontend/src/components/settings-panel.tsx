"use client";

import { Check, Copy, GripVertical, Moon, RefreshCcw, Sun, Trash2 } from "lucide-react";
import { useTheme } from "next-themes";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, calendarUrl } from "@/lib/api/client";
import {
  queryKeys,
  useCreateCategory,
  useCreateContext,
  useCreateTag,
  useDeleteCategory,
  useDeleteContext,
  useDeleteTag,
  useMe,
  useStorageUsage,
  useTaxonomy,
  useUpdateCategory,
  useUpdateContext,
  useUpdateTag,
} from "@/lib/api/hooks";
import type { Category, Context, Tag } from "@/lib/api/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type TaxonomyKind = "category" | "context" | "tag";
type TaxonomyItem = (Category | Context | Tag) & { parent_id?: string | null };

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
  const { theme, setTheme } = useTheme();
  const [copied, setCopied] = useState(false);
  const regenerate = useMutation({ mutationFn: api.regenerateCalendarToken, onSuccess: (user) => queryClient.setQueryData(queryKeys.me, user) });
  const url = me ? calendarUrl(me.calendar_token) : "";
  const taxonomy = useTaxonomy();

  async function copy() {
    if (!url) return;
    await navigator.clipboard.writeText(url);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }

  if (isLoading) return <div className="panel p-6 text-[var(--muted)]">Načítám nastavení…</div>;
  return (
    <div className="grid max-w-5xl gap-5">
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
        <h2 className="text-xl font-semibold">Vzhled</h2>
        <p className="mt-1 text-sm text-[var(--muted)]">Režim aplikace je v Nastavení, ne v hlavičce.</p>
        <div className="mt-4 grid gap-2 sm:grid-cols-3">
          <ThemeButton active={theme === "system"} onClick={() => setTheme("system")}>Podle systému</ThemeButton>
          <ThemeButton active={theme === "light"} onClick={() => setTheme("light")}><Sun size={16}/>Světlý</ThemeButton>
          <ThemeButton active={theme === "dark"} onClick={() => setTheme("dark")}><Moon size={16}/>Tmavý</ThemeButton>
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-3">
        <TaxonomySection kind="category" title="Kategorie" description="Jedna úroveň vnoření: u podkategorie vyber rodiče." items={taxonomy.categories.data?.items ?? []} parents={taxonomy.categories.data?.items ?? []} />
        <TaxonomySection kind="context" title="Místa" description="Místo nebo nástroj, kde úkol zvládnu — Ranč, Počítač, Město." items={taxonomy.contexts.data?.items ?? []} />
        <TaxonomySection kind="tag" title="Tagy" description="Volné štítky pro jemnější třídění úkolů." items={taxonomy.tags.data?.items ?? []} />
      </section>

      <section className="panel p-5 sm:p-6">
        <div className="flex items-start justify-between gap-4">
          <div><h2 className="text-xl font-semibold">Úložiště příloh</h2><p className="mt-1 text-sm text-[var(--muted)]">Fotky, PDF a náhledy uložené v Personal OS.</p></div>
          <Button type="button" variant="secondary" size="sm" onClick={() => void storage.refetch()} disabled={storage.isFetching}><RefreshCcw size={14} />Obnovit</Button>
        </div>
        {storage.isLoading ? <p className="mt-4 text-sm text-[var(--muted)]">Načítám využití úložiště…</p> : storage.data ? (
          <div className="mt-5 grid gap-3"><div className="h-3 overflow-hidden rounded-full bg-[var(--surface-muted)]"><div className="h-full rounded-full bg-[var(--primary)]" style={{ width: `${Math.min(100, storage.data.used_percent)}%` }} /></div><div className="grid gap-2 text-sm text-[var(--muted)] sm:grid-cols-3"><div><span className="font-medium text-[var(--foreground)]">{formatBytes(storage.data.used_bytes)}</span><br />využito</div><div><span className="font-medium text-[var(--foreground)]">{formatBytes(storage.data.remaining_bytes)}</span><br />zbývá</div><div><span className="font-medium text-[var(--foreground)]">{storage.data.file_count}</span><br />souborů</div></div><p className="text-xs text-[var(--muted)]">Limit: {formatBytes(storage.data.max_bytes)} · využití {storage.data.used_percent.toFixed(1)} %</p></div>
        ) : <p className="mt-4 text-sm text-[var(--danger)]">Využití úložiště se nepodařilo načíst.</p>}
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

function ThemeButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return <Button type="button" variant={active ? "default" : "secondary"} onClick={onClick}>{children}</Button>;
}

function TaxonomySection({ kind, title, description, items, parents = [] }: { kind: TaxonomyKind; title: string; description: string; items: TaxonomyItem[]; parents?: Category[] }) {
  const createCategory = useCreateCategory();
  const updateCategory = useUpdateCategory();
  const deleteCategory = useDeleteCategory();
  const createContext = useCreateContext();
  const updateContext = useUpdateContext();
  const deleteContext = useDeleteContext();
  const createTag = useCreateTag();
  const updateTag = useUpdateTag();
  const deleteTag = useDeleteTag();
  const [name, setName] = useState("");
  const [dragId, setDragId] = useState<string | null>(null);
  const defaults = kind === "category" ? { color: "#0EA5E9", icon: "folder" } : kind === "context" ? { color: "#64748B", icon: "map-pin" } : { color: "#64748B", icon: "hash" };

  async function createItem() {
    const trimmed = name.trim();
    if (!trimmed) return;
    const position = items.length;
    if (kind === "category") await createCategory.mutateAsync({ name: trimmed, color: defaults.color, icon: defaults.icon, position });
    if (kind === "context") await createContext.mutateAsync({ name: trimmed, color: defaults.color, icon: defaults.icon, position });
    if (kind === "tag") await createTag.mutateAsync({ name: trimmed, color: defaults.color, icon: defaults.icon, position });
    setName("");
  }

  async function updateItem(id: string, payload: Partial<TaxonomyItem>) {
    if (kind === "category") await updateCategory.mutateAsync({ id, payload });
    if (kind === "context") await updateContext.mutateAsync({ id, payload });
    if (kind === "tag") await updateTag.mutateAsync({ id, payload });
  }

  async function deleteItem(item: TaxonomyItem) {
    const action = item.task_count > 0 ? "archivovat" : "smazat";
    if (!window.confirm(`${action[0].toUpperCase()}${action.slice(1)} položku „${item.name}“?`)) return;
    if (kind === "category") await deleteCategory.mutateAsync(item.id);
    if (kind === "context") await deleteContext.mutateAsync(item.id);
    if (kind === "tag") await deleteTag.mutateAsync(item.id);
  }

  async function dropOn(targetId: string) {
    if (!dragId || dragId === targetId) return;
    const ordered = [...items];
    const from = ordered.findIndex((item) => item.id === dragId);
    const to = ordered.findIndex((item) => item.id === targetId);
    if (from < 0 || to < 0) return;
    const [moved] = ordered.splice(from, 1);
    ordered.splice(to, 0, moved);
    await Promise.all(ordered.map((item, index) => updateItem(item.id, { position: index })));
    setDragId(null);
  }

  return (
    <section className="panel grid gap-4 p-4 sm:p-5">
      <div><h2 className="text-lg font-semibold">{title}</h2><p className="mt-1 text-sm text-[var(--muted)]">{description}</p></div>
      <div className="flex gap-2"><Input value={name} onChange={(event) => setName(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void createItem(); }} placeholder={`Přidat ${title.toLocaleLowerCase("cs-CZ")}`} /><Button type="button" onClick={() => void createItem()} disabled={!name.trim()}>Přidat</Button></div>
      <div className="grid gap-2">
        {items.map((item) => (
          <div key={item.id} draggable onDragStart={() => setDragId(item.id)} onDragOver={(event) => event.preventDefault()} onDrop={() => void dropOn(item.id)} className="grid gap-2 rounded-[var(--radius-lg)] border border-[var(--border)] p-3">
            <div className="flex items-center justify-between gap-2"><div className="flex items-center gap-2"><GripVertical size={16} className="cursor-grab text-[var(--muted)]"/><span className="h-3 w-3 rounded-full" style={{ background: item.color }} /><strong className="text-sm">{item.name}</strong></div><span className="text-xs text-[var(--muted)]">{item.task_count} úkolů</span></div>
            <div className="grid gap-2 sm:grid-cols-[1fr_92px_1fr]">
              <Input aria-label="Název" value={item.name} onChange={(event) => void updateItem(item.id, { name: event.target.value })} />
              <Input aria-label="Barva" type="color" value={item.color} onChange={(event) => void updateItem(item.id, { color: event.target.value })} />
              <Input aria-label="Ikona" value={item.icon} onChange={(event) => void updateItem(item.id, { icon: event.target.value })} />
            </div>
            {kind === "category" ? <select className="focus-ring min-h-10 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-3 text-sm" value={item.parent_id ?? ""} onChange={(event) => void updateItem(item.id, { parent_id: event.target.value || null })}><option value="">Bez rodiče</option>{parents.filter((parent) => parent.id !== item.id && !parent.parent_id).map((parent) => <option key={parent.id} value={parent.id}>{parent.name}</option>)}</select> : null}
            <div className="flex justify-between gap-2"><Button type="button" variant="secondary" size="sm" onClick={() => void updateItem(item.id, { is_archived: true })}>Archivovat</Button><Button type="button" variant="ghost" size="sm" onClick={() => void deleteItem(item)}><Trash2 size={14}/>{item.task_count > 0 ? "Archivovat" : "Smazat"}</Button></div>
          </div>
        ))}
        {!items.length ? <p className="rounded-[var(--radius-lg)] border border-dashed border-[var(--border)] p-4 text-sm text-[var(--muted)]">Zatím prázdné. Doplň výchozí sadu přes seed nebo založ položku ručně.</p> : null}
      </div>
    </section>
  );
}
