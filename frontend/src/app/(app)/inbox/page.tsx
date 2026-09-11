import { Suspense } from "react";
import { InboxWorkspace } from "@/components/tasks/inbox-workspace";

export default function InboxPage() {
  return <Suspense fallback={<div className="panel p-8">Načítám inbox…</div>}><InboxWorkspace /></Suspense>;
}
