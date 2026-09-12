"use client";

import { BookOpen, Bot, CheckSquare, Flame, Inbox, LayoutDashboard, ListTodo, LogOut, Menu, Settings, Sparkles, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api/client";
import { useMe, useTaxonomy, useVisions } from "@/lib/api/hooks";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { QuickCapture } from "@/components/tasks/quick-capture";
import { CommandCenter } from "@/components/tasks/command-center";

const nav = [
  { href: "/dashboard", match: "/dashboard", label: "Přehled", icon: LayoutDashboard },
  { href: "/tasks", match: "/tasks", label: "Úkoly", icon: ListTodo },
  { href: "/inbox", match: "/inbox", label: "Inbox", icon: Inbox },
  { href: "/challenges", match: "/challenges", label: "Návyky", icon: Flame },
  { href: "/diary", match: "/diary", label: "Deník", icon: BookOpen },
  { href: "/visions", match: "/visions", label: "Vize", icon: Sparkles },
  { href: "/agent", match: "/agent", label: "Agent", icon: Bot },
  { href: "/settings", match: "/settings", label: "Nastavení", icon: Settings },
];

const primaryMobileNav = nav.slice(0, 4);
const moreMobileNav = nav.slice(4);

function isActivePath(pathname: string, item: (typeof nav)[number]) {
  if (item.label === "Inbox") return pathname === "/inbox";
  if (item.label === "Úkoly") return pathname === "/tasks";
  return pathname.startsWith(item.match);
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { data: me, error: meError } = useMe();
  const { categories, contexts, tags } = useTaxonomy();
  const visions = useVisions();
  const [now, setNow] = useState<Date | null>(null);
  const [moreOpen, setMoreOpen] = useState(false);
  const title = useMemo(() => nav.find((item) => isActivePath(pathname, item))?.label ?? "Personal OS", [pathname]);
  const showQuickTask = pathname === "/dashboard" || pathname === "/tasks" || pathname === "/inbox";

  useEffect(() => {
    setNow(new Date());
    const timer = window.setInterval(() => setNow(new Date()), 60_000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (meError instanceof ApiError && meError.status === 401) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [meError, pathname, router]);

  async function logout() {
    await api.logout().catch(() => undefined);
    queryClient.clear();
    router.replace("/login");
  }

  const dateTime = now ? new Intl.DateTimeFormat("cs-CZ", { weekday: "short", day: "numeric", month: "numeric", hour: "2-digit", minute: "2-digit" }).format(now) : "";

  return (
    <div className="app-grid">
      <aside className="sidebar">
        <div className="flex h-full flex-col gap-8">
          <div>
            <div className="flex items-center gap-3">
              <div className="flex size-10 items-center justify-center rounded-2xl bg-[var(--primary)] text-[var(--primary-foreground)]"><CheckSquare size={20} /></div>
              <div>
                <p className="font-semibold tracking-tight">Personal OS</p>
                <p className="text-xs text-[var(--muted)]">každodenní úkolovník</p>
              </div>
            </div>
          </div>
          <nav className="grid gap-1">
            {nav.map((item) => <NavLink key={item.href} {...item} active={isActivePath(pathname, item)} />)}
          </nav>
          <div className="min-h-0 flex-1 overflow-auto">
            <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-[.16em] text-[var(--muted-foreground)]">Kategorie</p>
            <div className="grid gap-1">
              {categories.data?.items.filter((c) => !c.is_archived).map((category) => (
                <Link key={category.id} href={`/tasks?category_id=${category.id}`} className="focus-ring flex items-center gap-2 rounded-[var(--radius-sm)] px-3 py-2 text-sm text-[var(--muted)] hover:bg-[var(--surface-muted)]">
                  <span className="size-2.5 rounded-full" style={{ background: category.color }} />{category.name}
                </Link>
              ))}
            </div>
          </div>
          <div className="grid gap-2 border-t border-[var(--border)] pt-4">
            <p className="truncate text-sm font-medium">{me?.display_name ?? "Nepřihlášen"}</p>
            <Button variant="ghost" size="sm" onClick={logout}><LogOut size={16} />Odhlásit</Button>
          </div>
        </div>
      </aside>
      <main className="workspace">
        <header className="mb-4 grid gap-3 sm:mb-6 sm:gap-4">
          <div className="flex items-center justify-between gap-3">
            <h1 className="truncate text-xl font-semibold tracking-tight sm:text-3xl">{title}</h1>
            <time className="shrink-0 text-right text-xs text-[var(--muted)] sm:text-sm" dateTime={now?.toISOString()}>{dateTime}</time>
          </div>
          {showQuickTask ? <QuickCapture categories={categories.data?.items ?? []} contexts={contexts.data?.items ?? []} tags={tags.data?.items ?? []} visions={visions.data?.items ?? []} /> : null}
        </header>
        {children}
      </main>
      <nav className="bottom-nav p-1 pb-[calc(0.25rem+env(safe-area-inset-bottom))]">
        {primaryMobileNav.map((item) => {
          const Icon = item.icon;
          return <Link key={item.href} href={item.href} className={cn("focus-ring flex min-w-0 flex-col items-center rounded-full px-1 py-2 text-[10px] text-[var(--muted)]", isActivePath(pathname, item) && "bg-[var(--primary)] text-[var(--primary-foreground)]")}><Icon size={17}/><span className="max-w-full truncate">{item.label}</span></Link>;
        })}
        <button type="button" onClick={() => setMoreOpen(true)} className="focus-ring flex min-w-0 flex-col items-center rounded-full px-1 py-2 text-[10px] text-[var(--muted)]"><Menu size={17}/><span className="max-w-full truncate">Více</span></button>
      </nav>
      {moreOpen ? (
        <div className="fixed inset-0 z-50 md:hidden" role="dialog" aria-modal="true" aria-label="Další stránky">
          <button type="button" className="absolute inset-0 bg-black/30" aria-label="Zavřít menu" onClick={() => setMoreOpen(false)} />
          <div className="absolute inset-x-3 bottom-3 rounded-[var(--radius-xl)] border border-[var(--border)] bg-[var(--surface)] p-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] shadow-2xl">
            <div className="mb-2 flex items-center justify-between">
              <p className="font-semibold">Více</p>
              <Button variant="ghost" size="sm" onClick={() => setMoreOpen(false)} aria-label="Zavřít"><X size={16}/></Button>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {moreMobileNav.map((item) => {
                const Icon = item.icon;
                return <Link key={item.href} href={item.href} onClick={() => setMoreOpen(false)} className={cn("focus-ring flex items-center gap-2 rounded-[var(--radius-md)] border border-[var(--border)] px-3 py-3 text-sm", isActivePath(pathname, item) && "bg-[var(--primary)] text-[var(--primary-foreground)]")}><Icon size={17}/>{item.label}</Link>;
              })}
            </div>
            <div className="mt-3 flex gap-2 border-t border-[var(--border)] pt-3">
              <Button variant="ghost" size="sm" onClick={logout}><LogOut size={16} />Odhlásit</Button>
            </div>
          </div>
        </div>
      ) : null}
      <CommandCenter />
    </div>
  );
}

function NavLink({ href, label, icon: Icon, active }: { href: string; label: string; icon: typeof LayoutDashboard; active: boolean }) {
  return <Link href={href} className={cn("focus-ring flex items-center gap-3 rounded-[var(--radius-md)] px-3 py-2.5 text-sm font-medium text-[var(--muted)] hover:bg-[var(--surface-muted)]", active && "bg-[var(--primary)] text-[var(--primary-foreground)] hover:bg-[var(--primary)]")}><Icon size={18}/>{label}</Link>;
}
