import { Suspense } from "react";
import { AgentWorkspace } from "@/components/agent/agent-workspace";

export default function AgentPage() {
  return (
    <Suspense fallback={<div className="panel p-8">Načítám…</div>}>
      <AgentWorkspace />
    </Suspense>
  );
}
