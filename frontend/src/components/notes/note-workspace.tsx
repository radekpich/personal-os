"use client";

import { BookOpen, CalendarDays, FileText, Lightbulb, MessageSquareText, Plus, Save, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import { AttachmentGrid } from "@/components/attachments/attachment-grid";
import { AttachmentUploader } from "@/components/attachments/attachment-uploader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import {
  useCreateNote,
  useDeleteNote,
  useNotes,
  useTaxonomy,
  useUpdateNote,
  useVisions,
} from "@/lib/api/hooks";
import type { Note, NoteKind } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const kindLabels: Record<NoteKind, string> = {
  note: "Poznámka",
  diary: "Deník",
  meeting: "Schůzka",
  idea: "Nápad",
};

const kindIcons: Record<NoteKind, typeof FileText> = {
  note: FileText,
  diary: BookOpen,
  meeting: MessageSquareText,
  idea: Lightbulb,
};

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function formatDate(value: string | null) {
  if (!value) return "Bez data";
  return new Intl.DateTimeFormat("cs-CZ", { day: "numeric", month: "long", year: "numeric" }).format(new Date(`${value}T00:00:00`));
}

function emptyDraft(kind: NoteKind = "diary") {
  return {
    title: "",
    body: "",
    kind,
    entry_date: kind === "diary" ? todayIso() : "",
    entry_time: "",
    mood: "",
    category_id: "",
    vision_id: "",
    task_id: "",
  };
}

type Draft = ReturnType<typeof emptyDraft>;

export function NoteWorkspace() {
  const [kind, setKind] = useState<NoteKind | "all">("all");
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft>(() => emptyDraft());
  const [editing, setEditing] = useState<Note | null>(null);
  const notes = useNotes({ kind, q: query, page_size: 80 });
  const { categories } = useTaxonomy();
  const visions = useVisions();
  const create = useCreateNote();
  const update = useUpdateNote();
  const remove = useDeleteNote();

  const items = useMemo(() => notes.data?.items ?? [], [notes.data?.items]);
  const selected = useMemo(() => items.find((item) => item.id === selectedId) ?? editing ?? items[0] ?? null, [editing, items, selectedId]);

  function startNew(nextKind: NoteKind = "diary") {
    setEditing(null);
    setSelectedId(null);
    setDraft(emptyDraft(nextKind));
  }

  function edit(note: Note) {
    setEditing(note);
    setSelectedId(note.id);
    setDraft({
      title: note.title,
      body: note.body ?? "",
      kind: note.kind,
      entry_date: note.entry_date ?? "",
      entry_time: note.entry_time ?? "",
      mood: note.mood ?? "",
      category_id: note.category_id ?? "",
      vision_id: note.vision_id ?? "",
      task_id: note.task_id ?? "",
    });
  }

  async function save() {
    const payload = {
      title: draft.title.trim() || (draft.kind === "diary" ? "Denní zápis" : "Bez názvu"),
      body: draft.body.trim() || null,
      kind: draft.kind,
      entry_date: draft.entry_date || null,
      entry_time: draft.entry_time || null,
      mood: draft.mood.trim() || null,
      category_id: draft.category_id || null,
      vision_id: draft.vision_id || null,
      task_id: draft.task_id || null,
    };
    const saved = editing ? await update.mutateAsync({ id: editing.id, payload }) : await create.mutateAsync(payload);
    setEditing(saved);
    setSelectedId(saved.id);
  }

  async function deleteSelected(note: Note) {
    await remove.mutateAsync(note.id);
    setEditing(null);
    setSelectedId(null);
    setDraft(emptyDraft());
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_28rem]">
      <section className="grid gap-4">
        <div className="panel flex flex-wrap items-center justify-between gap-3 p-5">
          <div>
            <p className="text-sm text-[var(--muted)]">Denní zápisy, nápady a poznámky propojené s přílohami.</p>
            <h2 className="text-xl font-semibold">Deník a poznámky</h2>
          </div>
          <Button onClick={() => startNew("diary")}><Plus size={16} />Nový zápis</Button>
        </div>

        <div className="panel flex flex-wrap gap-3 p-3">
          <select className="focus-ring min-h-10 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-3" value={kind} onChange={(event) => setKind(event.target.value as NoteKind | "all")}>
            <option value="all">Všechny typy</option>
            {Object.entries(kindLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
          <Input className="min-w-56 flex-1" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Hledat v názvu nebo textu…" />
        </div>

        {notes.isLoading ? <p className="panel p-5 text-[var(--muted)]">Načítám poznámky…</p> : null}
        {notes.isError ? <p className="panel p-5 text-[var(--danger)]">Poznámky se nepodařilo načíst.</p> : null}
        {!notes.isLoading && items.length === 0 ? <p className="panel p-5 text-[var(--muted)]">Zatím žádné poznámky. Založ první zápis vpravo.</p> : null}

        <div className="grid gap-3 md:grid-cols-2">
          {items.map((note) => <NoteCard key={note.id} note={note} selected={selected?.id === note.id} onSelect={() => edit(note)} />)}
        </div>
      </section>

      <aside className="grid h-fit gap-4">
        <section className="panel grid gap-4 p-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-sm text-[var(--muted)]">{editing ? "Upravit zápis" : "Nový zápis"}</p>
              <h2 className="text-lg font-semibold">Editor</h2>
            </div>
            {editing ? <Badge>{kindLabels[editing.kind]}</Badge> : null}
          </div>
          <Input value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} placeholder="Název" />
          <div className="grid gap-3 sm:grid-cols-2">
            <Select label="Typ" value={draft.kind} onChange={(value) => setDraft({ ...draft, kind: value as NoteKind, entry_date: draft.entry_date || (value === "diary" ? todayIso() : "") })}>
              {Object.entries(kindLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </Select>
            <label className="grid gap-1 text-sm font-medium">Datum<Input type="date" value={draft.entry_date} onChange={(event) => setDraft({ ...draft, entry_date: event.target.value })} /></label>
            <label className="grid gap-1 text-sm font-medium">Čas<Input type="time" value={draft.entry_time} onChange={(event) => setDraft({ ...draft, entry_time: event.target.value })} /></label>
            <label className="grid gap-1 text-sm font-medium">Nálada<Input value={draft.mood} onChange={(event) => setDraft({ ...draft, mood: event.target.value })} placeholder="klid / energie…" /></label>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <Select label="Kategorie" value={draft.category_id} onChange={(value) => setDraft({ ...draft, category_id: value })}>
              <option value="">Bez kategorie</option>
              {categories.data?.items.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
            </Select>
            <Select label="Vize" value={draft.vision_id} onChange={(value) => setDraft({ ...draft, vision_id: value })}>
              <option value="">Bez vize</option>
              {visions.data?.items.map((vision) => <option key={vision.id} value={vision.id}>{vision.title}</option>)}
            </Select>
          </div>
          <Textarea rows={9} value={draft.body} onChange={(event) => setDraft({ ...draft, body: event.target.value })} placeholder="Markdown zápis…" />
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => void save()} disabled={create.isPending || update.isPending}><Save size={16} />Uložit</Button>
            <Button variant="secondary" onClick={() => startNew(draft.kind)}>Nový</Button>
            {editing ? <Button variant="danger" onClick={() => void deleteSelected(editing)} disabled={remove.isPending}><Trash2 size={16} />Smazat</Button> : null}
          </div>
        </section>

        {selected ? (
          <section className="panel grid gap-4 p-5">
            <div>
              <p className="text-sm text-[var(--muted)]">Přílohy k poznámce</p>
              <h2 className="font-semibold">{selected.title}</h2>
            </div>
            <AttachmentUploader noteId={selected.id} />
            <AttachmentGrid noteId={selected.id} />
          </section>
        ) : null}
      </aside>
    </div>
  );
}

function NoteCard({ note, selected, onSelect }: { note: Note; selected: boolean; onSelect: () => void }) {
  const Icon = kindIcons[note.kind];
  return (
    <button type="button" onClick={onSelect} className={cn("panel p-5 text-left transition hover:-translate-y-0.5", selected && "ring-2 ring-[var(--primary)]")}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="flex size-9 items-center justify-center rounded-2xl bg-[var(--surface-muted)] text-[var(--muted)]"><Icon size={17} /></span>
            <div className="min-w-0">
              <h3 className="truncate font-semibold">{note.title}</h3>
              <p className="text-xs text-[var(--muted)]">{kindLabels[note.kind]}</p>
            </div>
          </div>
          {note.body ? <p className="mt-3 line-clamp-3 text-sm text-[var(--muted)]">{note.body}</p> : null}
        </div>
        <div className="shrink-0 text-right text-xs text-[var(--muted)]">
          <CalendarDays className="ml-auto mb-1" size={15} />
          {formatDate(note.entry_date)}
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {note.mood ? <Badge>{note.mood}</Badge> : null}
        {note.category_id ? <Badge>kategorie</Badge> : null}
        {note.vision_id ? <Badge>vize</Badge> : null}
      </div>
    </button>
  );
}

function Select({ label, value, onChange, children }: { label: string; value: string; onChange: (value: string) => void; children: React.ReactNode }) {
  return (
    <label className="grid gap-1 text-sm font-medium">
      {label}
      <select className="focus-ring min-h-10 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-3" value={value} onChange={(event) => onChange(event.target.value)}>
        {children}
      </select>
    </label>
  );
}
