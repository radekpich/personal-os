import { Suspense } from "react";
import { TaskWorkspace } from "@/components/tasks/task-workspace";
export default function InboxPage() { return <Suspense fallback={<div className="panel p-8">Načítám…</div>}><TaskWorkspace initialView="inbox" /></Suspense>; }
