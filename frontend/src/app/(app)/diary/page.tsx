import { Suspense } from "react";
import { NoteWorkspace } from "@/components/notes/note-workspace";

export default function DiaryPage() {
  return (
    <Suspense fallback={<div className="panel p-8">Načítám…</div>}>
      <NoteWorkspace />
    </Suspense>
  );
}
