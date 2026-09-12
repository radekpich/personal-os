"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { BookOpen, CalendarDays, FileText, Lightbulb, MessageSquareText, Plus, Save, Send, Trash2, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { AttachmentGrid } from "@/components/attachments/attachment-grid";
import { AttachmentUploader } from "@/components/attachments/attachment-uploader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Input, Textarea } from "@/components/ui/input";
import { useCreateNote, useDeleteNote, useNotes, useTaxonomy, useUpdateNote, useVisions } from "@/lib/api/hooks";
import type { Note, NoteKind } from "@/lib/api/types";
import { ApiError } from "@/lib/api/client";
import { cn } from "@/lib/utils";
import { MarkdownPreview } from "@/components/markdown-preview";

const kindLabels: Record<NoteKind, string> = { note: "Poznámka", diary: "Deník", meeting: "Schůzka", idea: "Nápad" };
const kindIcons: Record<NoteKind, typeof FileText> = { note: FileText, diary: BookOpen, meeting: MessageSquareText, idea: Lightbulb };

function todayIso() { return new Date().toISOString().slice(0, 10); }
function formatDate(value: string | null) { return value ? new Intl.DateTimeFormat("cs-CZ", { day: "numeric", month: "long", year: "numeric" }).format(new Date(`${value}T00:00:00`)) : "Bez data"; }
function emptyDraft(kind: NoteKind = "diary") { return { title: "", body: "", kind, entry_date: kind === "diary" ? todayIso() : "", entry_time: "", mood: "", category_id: "", vision_id: "", task_id: "" }; }
type Draft = ReturnType<typeof emptyDraft>;

export function NoteWorkspace() {
  const [kind, setKind] = useState<NoteKind | "all">("all");
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft>(() => emptyDraft());
  const [editing, setEditing] = useState<Note | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Note | null>(null);
  const [editorOpen, setEditorOpen] = useState(false);
  const [conflict, setConflict] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [quickNote, setQuickNote] = useState("");
  const notes = useNotes({ kind, q: query, page_size: 80 });
  const { categories } = useTaxonomy();
  const visions = useVisions();
  const create = useCreateNote();
  const update = useUpdateNote();
  const remove = useDeleteNote();
  const items = useMemo(() => notes.data?.items ?? [], [notes.data?.items]);
  const selected = useMemo(() => items.find((item) => item.id === selectedId) ?? editing ?? items[0] ?? null, [editing, items, selectedId]);
  const [highlightedIds, setHighlightedIds] = useState<Set<string>>(() => new Set());
  const seenIds = useRef<Set<string> | null>(null);

  useEffect(() => {
    const current = notes.data?.items.map((note) => note.id) ?? null;
    if (!current) return;
    if (seenIds.current === null) { seenIds.current = new Set(current); return; }
    const added = current.filter((id) => !seenIds.current?.has(id));
    seenIds.current = new Set(current);
    if (!added.length) return;
    setHighlightedIds(new Set(added));
    const timeout = window.setTimeout(() => setHighlightedIds(new Set()), 10_000);
    return () => window.clearTimeout(timeout);
  }, [notes.data?.items]);

  function openNew(nextKind: NoteKind = "diary", body = "") {
    setConflict(null); setSaveError(null); setEditing(null); setSelectedId(null); setDraft({ ...emptyDraft(nextKind), body }); setEditorOpen(true);
  }
  function edit(note: Note) {
    setConflict(null); setSaveError(null); setEditing(note); setSelectedId(note.id); setDraft({ title: note.title, body: note.body ?? "", kind: note.kind, entry_date: note.entry_date ?? "", entry_time: note.entry_time ?? "", mood: note.mood ?? "", category_id: note.category_id ?? "", vision_id: note.vision_id ?? "", task_id: note.task_id ?? "" }); setEditorOpen(true);
  }
  async function save() {
    const payload = { title: draft.title.trim() || (draft.kind === "diary" ? "Denní zápis" : "Bez názvu"), body: draft.body.trim() || null, kind: draft.kind, entry_date: draft.entry_date || null, entry_time: draft.entry_time || null, mood: draft.mood.trim() || null, category_id: draft.category_id || null, vision_id: draft.vision_id || null, task_id: draft.task_id || null };
    try {
      setConflict(null); setSaveError(null);
      const saved = editing ? await update.mutateAsync({ note: editing, payload }) : await create.mutateAsync(payload);
      setEditing(saved); setSelectedId(saved.id); setEditorOpen(false);
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) { setConflict("Poznámku mezitím upravil web nebo agent. Načti aktuální stav a zkus změnu znovu."); return; }
      setSaveError(error instanceof Error ? error.message : "Zápis se nepodařilo uložit. Zkus to prosím znovu.");
    }
  }
  async function createQuickNote() {
    const body = quickNote.trim(); if (!body) return; setQuickNote(""); setSaveError(null);
    try { const saved = await create.mutateAsync({ title: "Rychlá poznámka", body, kind: "note", entry_date: todayIso() }); setEditing(saved); setSelectedId(saved.id); }
    catch (error) { setQuickNote(body); setSaveError(error instanceof Error ? error.message : "Poznámku se nepodařilo uložit. Zkus to prosím znovu."); }
  }
  async function deleteSelected(note: Note) { await remove.mutateAsync(note); setEditing(null); setSelectedId(null); setDraft(emptyDraft()); setEditorOpen(false); setDeleteTarget(null); }

  return (
    <div className="grid gap-5">
      <section className="grid gap-4">
        <div className="panel flex flex-wrap items-center justify-between gap-3 p-4 sm:p-5"><div><p className="text-sm text-[var(--muted)]">Denní zápisy, nápady a poznámky propojené s přílohami.</p><h2 className="text-lg font-semibold sm:text-xl">Deník a poznámky</h2></div><Button onClick={() => openNew("diary")}><Plus size={16} />Nový zápis</Button></div>
        <div className="panel grid gap-1 p-2"><div className="flex items-center gap-2"><Input value={quickNote} onChange={(event) => setQuickNote(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void createQuickNote(); }} placeholder="Rychle zapsat poznámku…" aria-label="Rychlá poznámka" className="min-w-0 border-0 bg-transparent text-sm shadow-none focus-visible:outline-none sm:text-base" /><Button type="button" size="sm" onClick={() => void createQuickNote()} disabled={create.isPending || !quickNote.trim()} aria-label="Uložit rychlou poznámku"><Send size={15}/></Button><Button type="button" size="sm" variant="secondary" onClick={() => { openNew("note", quickNote); setQuickNote(""); }}><Plus size={15}/>Plný</Button></div>{saveError ? <p className="px-2 pb-1 text-sm text-[var(--danger)]">Uložení se nepovedlo: {saveError}</p> : null}</div>
        <div className="panel flex flex-wrap gap-2 p-3 sm:gap-3"><select className="focus-ring min-h-10 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-3" value={kind} onChange={(event) => setKind(event.target.value as NoteKind | "all")}><option value="all">Všechny typy</option>{Object.entries(kindLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select><Input className="min-w-56 flex-1" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Hledat v názvu nebo textu…" /></div>
        {notes.isLoading ? <p className="panel p-5 text-[var(--muted)]">Načítám poznámky…</p> : null}
        {notes.isError ? <p className="panel p-5 text-[var(--danger)]">Poznámky se nepodařilo načíst.</p> : null}
        {!notes.isLoading && items.length === 0 ? <p className="panel p-5 text-[var(--muted)]">Zatím žádné poznámky. Založ první zápis tlačítkem nahoře.</p> : null}
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">{items.map((note) => <NoteCard key={note.id} note={note} selected={selected?.id === note.id} highlighted={highlightedIds.has(note.id)} onSelect={() => edit(note)} />)}</div>
      </section>
      <NoteDialog open={editorOpen} editing={editing} draft={draft} setDraft={setDraft} conflict={conflict} saveError={saveError} categories={categories.data?.items ?? []} visions={visions.data?.items ?? []} saving={create.isPending || update.isPending} deleting={remove.isPending} onClose={() => setEditorOpen(false)} onSave={save} onDelete={editing ? () => setDeleteTarget(editing) : undefined} />
      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title={`Smazat poznámku „${deleteTarget?.title ?? ""}“?`}
        description="Tuto akci nejde vrátit zpět."
        confirmLabel="Smazat poznámku"
        destructive
        confirmDisabled={remove.isPending}
        onConfirm={() => { if (deleteTarget) void deleteSelected(deleteTarget); }}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}

function NoteDialog({ open, editing, draft, setDraft, conflict, saveError, categories, visions, saving, deleting, onClose, onSave, onDelete }: { open: boolean; editing: Note | null; draft: Draft; setDraft: (draft: Draft) => void; conflict: string | null; saveError: string | null; categories: { id: string; name: string }[]; visions: { id: string; title: string }[]; saving: boolean; deleting: boolean; onClose: () => void; onSave: () => Promise<void>; onDelete?: () => void | Promise<void> }) {
  return <Dialog.Root open={open} onOpenChange={(next) => { if (!next) onClose(); }}><Dialog.Portal><Dialog.Overlay className="fixed inset-0 z-50 bg-black/30"/><Dialog.Content className="fixed inset-x-0 bottom-0 z-50 flex max-h-[96dvh] flex-col overflow-hidden rounded-t-[var(--radius-xl)] border border-[var(--border)] bg-[var(--surface)] shadow-2xl sm:inset-y-0 sm:left-auto sm:right-0 sm:h-dvh sm:w-full sm:max-w-xl sm:rounded-none sm:border-l"><div className="flex items-start justify-between gap-4 border-b border-[var(--border)] p-4 sm:p-6"><div><Dialog.Title className="text-lg font-semibold">{editing ? "Upravit zápis" : "Nový zápis"}</Dialog.Title><Dialog.Description className="text-sm text-[var(--muted)]">Stejný vzor zakládání jako v ostatních částech aplikace.</Dialog.Description></div><Dialog.Close asChild><Button variant="ghost" size="sm"><X size={18}/></Button></Dialog.Close></div><div className="grid flex-1 gap-3 overflow-y-auto p-4 pb-24 sm:p-6"><Input value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} placeholder="Název" />{conflict ? <p className="rounded-[var(--radius-sm)] border border-[var(--warning)] bg-[var(--warning)]/10 p-3 text-sm text-[var(--warning)]">{conflict}</p> : null}{saveError ? <p className="rounded-[var(--radius-sm)] border border-[var(--danger)] bg-[var(--danger)]/10 p-3 text-sm text-[var(--danger)]">Uložení se nepovedlo: {saveError}</p> : null}<div className="grid gap-3 sm:grid-cols-2"><Select label="Typ" value={draft.kind} onChange={(value) => setDraft({ ...draft, kind: value as NoteKind, entry_date: draft.entry_date || (value === "diary" ? todayIso() : "") })}>{Object.entries(kindLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</Select><label className="grid gap-1 text-sm font-medium">Datum<Input type="date" value={draft.entry_date} onChange={(event) => setDraft({ ...draft, entry_date: event.target.value })} /></label><label className="grid gap-1 text-sm font-medium">Čas<Input type="time" value={draft.entry_time} onChange={(event) => setDraft({ ...draft, entry_time: event.target.value })} /></label><label className="grid gap-1 text-sm font-medium">Nálada<Input value={draft.mood} onChange={(event) => setDraft({ ...draft, mood: event.target.value })} placeholder="klid / energie…" /></label></div><div className="grid gap-3 sm:grid-cols-2"><Select label="Kategorie" value={draft.category_id} onChange={(value) => setDraft({ ...draft, category_id: value })}><option value="">Bez kategorie</option>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</Select><Select label="Vize" value={draft.vision_id} onChange={(value) => setDraft({ ...draft, vision_id: value })}><option value="">Bez vize</option>{visions.map((vision) => <option key={vision.id} value={vision.id}>{vision.title}</option>)}</Select></div><Textarea rows={9} value={draft.body} onChange={(event) => setDraft({ ...draft, body: event.target.value })} placeholder="Markdown zápis…" />{editing ? <section className="grid gap-3 rounded-[var(--radius-lg)] border border-dashed border-[var(--border)] p-3"><p className="font-medium">Přílohy</p><AttachmentUploader noteId={editing.id} /><AttachmentGrid noteId={editing.id} /></section> : <p className="rounded-[var(--radius-lg)] border border-dashed border-[var(--border)] p-3 text-sm text-[var(--muted)]">Přílohy půjdou nahrát hned po prvním uložení poznámky.</p>}</div><div className="sticky bottom-0 flex justify-between gap-2 border-t border-[var(--border)] bg-[var(--surface)] p-4 pb-[calc(1rem+env(safe-area-inset-bottom))] sm:p-6"><div>{onDelete ? <Button variant="danger" onClick={() => void onDelete()} disabled={deleting}><Trash2 size={16}/>Smazat</Button> : null}</div><div className="flex gap-2"><Button variant="ghost" onClick={onClose}>Zrušit</Button><Button onClick={() => void onSave()} disabled={saving}><Save size={16}/>Uložit</Button></div></div></Dialog.Content></Dialog.Portal></Dialog.Root>;
}

function noteAgentActivityHref(note: Note) { return `/agent?action=add_note&entity_type=note&entity_id=${note.id}`; }
function NoteCard({ note, selected, highlighted, onSelect }: { note: Note; selected: boolean; highlighted: boolean; onSelect: () => void }) { const Icon = kindIcons[note.kind]; return <article className={cn("panel p-5 transition hover:-translate-y-0.5", selected && "ring-2 ring-[var(--primary)]", (note.created_by === "agent" || highlighted) && "border-[var(--accent)]/70 bg-[var(--accent)]/5")}><button type="button" onClick={onSelect} className="block w-full text-left"><div className="flex items-start justify-between gap-3"><div className="min-w-0"><div className="flex items-center gap-2"><span className="flex size-9 items-center justify-center rounded-2xl bg-[var(--surface-muted)] text-[var(--muted)]"><Icon size={17} /></span><div className="min-w-0"><h3 className="truncate font-semibold">{note.title}</h3><p className="text-xs text-[var(--muted)]">{kindLabels[note.kind]}</p></div></div>{note.body ? <MarkdownPreview compact className="mt-3 text-sm text-[var(--muted)]">{note.body}</MarkdownPreview> : null}</div><div className="shrink-0 text-right text-xs text-[var(--muted)]"><CalendarDays className="ml-auto mb-1" size={15} />{formatDate(note.entry_date)}</div></div></button><div className="mt-4 flex flex-wrap gap-2">{note.mood ? <Badge>{note.mood}</Badge> : null}{note.category_id ? <Badge>kategorie</Badge> : null}{note.vision_id ? <Badge>vize</Badge> : null}{note.created_by === "agent" ? <Link href={noteAgentActivityHref(note)} aria-label="Zobrazit akci agenta pro tuto poznámku"><Badge className="border-[var(--accent)] text-[var(--accent)] hover:bg-[var(--accent)]/10">agent</Badge></Link> : null}{highlighted ? <Badge className="border-[var(--success)] text-[var(--success)]">nové</Badge> : null}</div></article>; }
function Select({ label, value, onChange, children }: { label: string; value: string; onChange: (value: string) => void; children: React.ReactNode }) { return <label className="grid gap-1 text-sm font-medium">{label}<select className="focus-ring min-h-10 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-3" value={value} onChange={(event) => onChange(event.target.value)}>{children}</select></label>; }
