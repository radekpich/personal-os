import { Suspense } from "react";
import { AppShell } from "@/components/app-shell";

export default function PrivateLayout({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<div className="workspace">Načítám…</div>}><AppShell>{children}</AppShell></Suspense>;
}
