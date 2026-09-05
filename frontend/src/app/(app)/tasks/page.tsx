import { Suspense } from "react";
import { TaskWorkspace } from "@/components/tasks/task-workspace";
export default function TasksPage() { return <Suspense fallback={<div className="panel p-8">Načítám…</div>}><TaskWorkspace /></Suspense>; }
