import { Suspense } from "react";
import { AgentActivityWorkspace } from "@/components/agent/agent-activity-workspace";

export default function AgentPage() {
  return (
    <Suspense fallback={<div className="panel p-8">Načítám…</div>}>
      <AgentActivityWorkspace />
    </Suspense>
  );
}
