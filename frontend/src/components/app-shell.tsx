"use client";

import { BookOpen, Bot, CheckSquare, Flame, Inbox, LayoutDashboard, ListTodo, LogOut, Moon, Settings, Sparkles, Sun } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { useEffect, useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api/client";
import { useMe, useTaxonomy } from "@/lib/api/hooks";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { QuickCapture } from "@/components/tasks/quick-capture";
import { CommandCenter } from "@/components/tasks/command-center";

const nav = [
  { href: "/dashboard", label: "Přehled", icon: LayoutDashboard },
  { href: "/tasks", label: "Úkoly", icon: ListTodo },
  { href: "/inbox", label: "Inbox", icon: Inbox },
  { href: "/challenges", label: "Návyky", icon: Flame },
  { href: "/diary", label: "Deník", icon: BookOpen },
  { href: "/visions", label: "Vize", icon: Sparkles },
  { href: "/agent", label: "Agent", icon: Bot },
  { href: "/settings", label: "Nastavení", icon: Settings },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { setTheme, resolvedTheme } = useTheme();
  const { data: me, error: meError } = useMe();
  const { categories } = useTaxonomy();
  const title = useMemo(() => nav.find((item) => pathname.startsWith(item.href))?.label ?? "Personal OS", [pathname]);

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
            {nav.map((item) => <NavLink key={item.href} {...item} active={pathname.startsWith(item.href)} />)}
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
            <div className="flex gap-2">
              <Button variant="secondary" size="sm" onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")} aria-label="Přepnout režim">
                {resolvedTheme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
              </Button>
              <Button variant="ghost" size="sm" onClick={logout}><LogOut size={16} />Odhlásit</Button>
            </div>
          </div>
        </div>
      </aside>
      <main className="workspace">
        <header className="mb-6 grid gap-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm text-[var(--muted)]">{new Intl.DateTimeFormat("cs-CZ", { weekday: "long", day: "numeric", month: "long" }).format(new Date())}</p>
              <h1 className="text-3xl font-semibold tracking-tight">{title}</h1>
            </div>
            <Button variant="secondary" onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}>{resolvedTheme === "dark" ? <Sun size={16} /> : <Moon size={16} />} Režim</Button>
          </div>
          <QuickCapture />
        </header>
        {children}
      </main>
      <nav className="bottom-nav p-1">
        {nav.map((item) => {
          const Icon = item.icon;
          return <Link key={item.href} href={item.href} className={cn("focus-ring flex flex-col items-center rounded-full px-2 py-2 text-[11px] text-[var(--muted)]", pathname.startsWith(item.href) && "bg-[var(--primary)] text-[var(--primary-foreground)]")}><Icon size={18}/>{item.label}</Link>;
        })}
      </nav>
      <CommandCenter />
    </div>
  );
}

function NavLink({ href, label, icon: Icon, active }: { href: string; label: string; icon: typeof LayoutDashboard; active: boolean }) {
  return <Link href={href} className={cn("focus-ring flex items-center gap-3 rounded-[var(--radius-md)] px-3 py-2.5 text-sm font-medium text-[var(--muted)] hover:bg-[var(--surface-muted)]", active && "bg-[var(--primary)] text-[var(--primary-foreground)] hover:bg-[var(--primary)]")}><Icon size={18}/>{label}</Link>;
}
