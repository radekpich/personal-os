"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { Activity, CheckCircle2, Flame, Plus, ShieldCheck, SlidersHorizontal, X } from "lucide-react";
import { useMemo, useState } from "react";
import {
  useChallengeHeatmap,
  useChallengeStats,
  useChallenges,
  useCheckInChallenge,
  useDeleteChallenge,
  useDeleteCheckIn,
  useTaxonomy,
} from "@/lib/api/hooks";
import type { Challenge, ChallengeHeatmapDay, ChallengeType } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { czechPlural, formatCzechCount } from "@/lib/czech";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ActionButton } from "@/components/ui/action-buttons";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { ChallengeDialog } from "@/components/challenges/challenge-dialog";

const challengeTypeLabels: Record<ChallengeType, string> = {
  daily_action: "Denní akce",
  abstinence: "Abstinence",
};

// Mirrors BACKFILL_LIMIT_DAYS in backend/app/services/challenge_service.py
const BACKFILL_LIMIT_DAYS = 7;

export function ChallengeWorkspace() {
  const challenges = useChallenges();
  const { categories } = useTaxonomy();
  const checkIn = useCheckInChallenge();
  const deleteCheckIn = useDeleteCheckIn();
  const remove = useDeleteChallenge();

  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingChallenge, setEditingChallenge] = useState<Challenge | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Challenge | null>(null);
  const [pendingDate, setPendingDate] = useState<string | null>(null);
  const [presetFilter, setPresetFilter] = useState<ChallengePreset>("all");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [advancedFilters, setAdvancedFilters] = useState<ChallengeFilters>(() => defaultChallengeFilters);

  const year = new Date().getFullYear();
  const deleteImpact = useChallengeStats(deleteTarget?.id ?? null);

  const filteredChallenges = useMemo(() => {
    const items = challenges.data?.items ?? [];
    return items.filter((challenge) => {
      if (!matchesPreset(challenge, presetFilter)) return false;
      if (advancedFilters.type !== "all" && challenge.type !== advancedFilters.type) return false;
      if (advancedFilters.categoryId !== "all" && challenge.category_id !== advancedFilters.categoryId) return false;
      if (advancedFilters.status === "active" && !challenge.is_active) return false;
      if (advancedFilters.status === "paused" && challenge.is_active) return false;
      if (advancedFilters.streak === "zero" && challenge.current_streak !== 0) return false;
      if (advancedFilters.streak === "short" && challenge.current_streak > 3) return false;
      if (advancedFilters.streak === "strong" && challenge.current_streak < 7) return false;
      return true;
    });
  }, [advancedFilters, challenges.data?.items, presetFilter]);

  const insights = useMemo(() => buildChallengeInsights(challenges.data?.items ?? []), [challenges.data?.items]);
  const activeAdvancedCount = countChallengeFilters(advancedFilters);

  function openCreate() {
    setEditingChallenge(null);
    setDialogOpen(true);
  }

  function openEdit(challenge: Challenge) {
    setEditingChallenge(challenge);
    setDialogOpen(true);
  }

  function toggleDetail(id: string) {
    setExpandedId((current) => (current === id ? null : id));
  }

  function requestDelete(challenge: Challenge) {
    setDeleteTarget(challenge);
  }

  async function confirmDelete() {
    if (!deleteTarget) return;
    await remove.mutateAsync(deleteTarget.id);
    if (expandedId === deleteTarget.id) setExpandedId(null);
    setDeleteTarget(null);
  }

  async function oneTap(challenge: Challenge) {
    await checkIn.mutateAsync({
      id: challenge.id,
      payload: { date: todayPrague(), is_relapse: challenge.type === "abstinence" },
    });
  }

  async function handleCheckInToggle(challenge: Challenge, day: ChallengeHeatmapDay) {
    setPendingDate(day.date);
    try {
      if (day.has_check_in) {
        await deleteCheckIn.mutateAsync({ id: challenge.id, date: day.date });
      } else {
        // TODO(value-based challenges): Challenge only has two types (daily_action/abstinence) and
        // no target-value/value-based flag — CheckIn.value exists but isn't tied to a challenge
        // subtype. Once that model lands, branch here to open a small numeric-input dialog before
        // submitting the check-in.
        await checkIn.mutateAsync({
          id: challenge.id,
          payload: { date: day.date, is_relapse: challenge.type === "abstinence" },
        });
      }
    } finally {
      setPendingDate(null);
    }
  }

  return (
    <div className="grid min-w-0 max-w-full gap-4">
      <div className="panel grid min-w-0 max-w-full gap-4 p-4 sm:p-5">
        <div className="flex min-w-0 flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <h2 className="text-xl font-semibold">Návyky a výzvy</h2>
          </div>
          <Button onClick={openCreate}><Plus size={16}/>Nová výzva</Button>
        </div>
        <div className="grid min-w-0 grid-cols-2 gap-2 text-sm sm:grid-cols-3 lg:grid-cols-5">
          {insights.map((insight) => <InsightCard key={insight.label} label={insight.label} value={insight.value} hint={insight.hint} tone={insight.tone} />)}
        </div>
      </div>

      <ChallengeFilterStrip
        preset={presetFilter}
        onPreset={setPresetFilter}
        filteredCount={filteredChallenges.length}
        totalCount={challenges.data?.items.length ?? 0}
        advancedCount={activeAdvancedCount}
        onOpenFilters={() => setFiltersOpen(true)}
      />

      {challenges.isLoading ? <p className="panel p-5 text-[var(--muted)]">Načítám návyky…</p> : null}
      {challenges.isError ? <p className="panel p-5 text-[var(--danger)]">Návyky se nepodařilo načíst.</p> : null}
      {!challenges.isLoading && !filteredChallenges.length ? (
        <p className="panel p-5 text-[var(--muted)]">
          {challenges.data?.items.length ? "Žádná výzva neodpovídá filtru." : "Zatím žádný návyk. Založ první výzvu tlačítkem nahoře."}
        </p>
      ) : null}

      <div className="grid min-w-0 max-w-full gap-3 md:grid-cols-2">
        {filteredChallenges.map((challenge) => (
          <ChallengeCard
            key={challenge.id}
            challenge={challenge}
            expanded={expandedId === challenge.id}
            pending={checkIn.isPending}
            pendingDate={pendingDate}
            year={year}
            onToggleDetail={() => toggleDetail(challenge.id)}
            onOneTap={() => oneTap(challenge)}
            onEdit={() => openEdit(challenge)}
            onDelete={() => requestDelete(challenge)}
            onCheckInToggle={handleCheckInToggle}
          />
        ))}
      </div>

      <ChallengeDialog open={dialogOpen} challenge={editingChallenge} onClose={() => setDialogOpen(false)} />
      {filtersOpen ? (
        <ChallengeFilterDialog
          initial={advancedFilters}
          categories={categories.data?.items ?? []}
          onApply={(filters) => { setAdvancedFilters(filters); setFiltersOpen(false); }}
          onClose={() => setFiltersOpen(false)}
        />
      ) : null}

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title={`Smazat výzvu „${deleteTarget?.title ?? ""}“?`}
        description="Tuto akci nejde vrátit zpět."
        confirmLabel="Smazat výzvu"
        onConfirm={confirmDelete}
        onCancel={() => setDeleteTarget(null)}
        confirmDisabled={remove.isPending}
      >
        {deleteImpact.data && deleteImpact.data.total_count > 0 ? (
          <p className="rounded-[var(--radius-sm)] border border-[var(--warning)] bg-[var(--warning)]/10 p-3 text-sm text-[var(--warning)]">
            {formatCzechCount(deleteImpact.data.total_count, "zápis", "zápisy", "zápisů")} bude nenávratně smazáno spolu s touto výzvou.
          </p>
        ) : null}
      </ConfirmDialog>
    </div>
  );
}

type ChallengePreset = "all" | "active" | "paused" | "daily_action" | "abstinence";
type ChallengeFilters = { type: ChallengeType | "all"; categoryId: string; status: "all" | "active" | "paused"; streak: "all" | "zero" | "short" | "strong" };
const defaultChallengeFilters: ChallengeFilters = { type: "all", categoryId: "all", status: "all", streak: "all" };
const challengePresets: Array<{ value: ChallengePreset; label: string }> = [
  { value: "all", label: "Vše" },
  { value: "active", label: "Aktivní" },
  { value: "paused", label: "Pauza" },
  { value: "daily_action", label: "Denní" },
  { value: "abstinence", label: "Abstinence" },
];

function matchesPreset(challenge: Challenge, preset: ChallengePreset) {
  if (preset === "active") return challenge.is_active;
  if (preset === "paused") return !challenge.is_active;
  if (preset === "daily_action" || preset === "abstinence") return challenge.type === preset;
  return true;
}

function countChallengeFilters(filters: ChallengeFilters) {
  return [filters.type !== "all", filters.categoryId !== "all", filters.status !== "all", filters.streak !== "all"].filter(Boolean).length;
}

function buildChallengeInsights(items: Challenge[]) {
  const active = items.filter((item) => item.is_active);
  const source = active.length ? active : items;
  const shortest = source.reduce<Challenge | null>((best, item) => (!best || item.current_streak < best.current_streak ? item : best), null);
  const best = source.reduce<Challenge | null>((top, item) => (!top || item.current_streak > top.current_streak ? item : top), null);
  const worst = source.filter((item) => item.current_streak === 0).length || source.reduce<Challenge | null>((low, item) => (!low || item.longest_streak - item.current_streak > low.longest_streak - low.current_streak ? item : low), null)?.title || "—";
  const record = source.reduce((max, item) => Math.max(max, item.longest_streak), 0);
  return [
    { label: "Nejkratší šňůra", value: shortest ? formatCzechCount(shortest.current_streak, "den", "dny", "dní") : "—", hint: shortest?.title ?? "bez návyků", tone: "warning" as const },
    { label: "Nejlepší", value: best ? formatCzechCount(best.current_streak, "den", "dny", "dní") : "—", hint: best?.title ?? "bez dat", tone: "success" as const },
    { label: "Nejhorší", value: typeof worst === "number" ? formatCzechCount(worst, "nulová", "nulové", "nulových") : worst, hint: typeof worst === "number" ? "bez šňůry" : "největší propad", tone: "danger" as const },
    { label: "Aktivní", value: active.length, hint: `${items.length} celkem`, tone: "neutral" as const },
    { label: "Rekord", value: formatCzechCount(record, "den", "dny", "dní"), hint: "nejdelší série", tone: "neutral" as const },
  ];
}

function InsightCard({ label, value, hint, tone }: { label: string; value: string | number; hint: string; tone: "neutral" | "success" | "warning" | "danger" }) {
  return <div className={cn("min-w-0 rounded-[var(--radius-md)] border p-2.5", tone === "success" && "border-[var(--success)]/30 bg-[var(--success)]/10", tone === "warning" && "border-[var(--warning)]/30 bg-[var(--warning)]/10", tone === "danger" && "border-[var(--danger)]/30 bg-[var(--danger)]/10", tone === "neutral" && "border-[var(--border)] bg-[var(--surface-muted)]")}><p className="truncate text-[11px] text-[var(--muted)]">{label}</p><p className="truncate text-base font-semibold">{value}</p><p className="truncate text-[11px] text-[var(--muted)]">{hint}</p></div>;
}

function ChallengeFilterStrip({ preset, onPreset, filteredCount, totalCount, advancedCount, onOpenFilters }: { preset: ChallengePreset; onPreset: (value: ChallengePreset) => void; filteredCount: number; totalCount: number; advancedCount: number; onOpenFilters: () => void }) {
  return (
    <div className="panel flex min-w-0 max-w-full items-center gap-2 overflow-hidden p-2 sm:p-3">
      <div className="-mx-1 flex min-w-0 flex-1 gap-2 overflow-x-auto px-1 pb-1" role="tablist" aria-label="Rychlé filtry návyků">
        {challengePresets.map((view) => (
          <button key={view.value} type="button" onClick={() => onPreset(view.value)} className={cn("focus-ring inline-flex min-h-10 shrink-0 items-center gap-2 rounded-full border px-3 text-sm font-medium transition", preset === view.value ? "border-[var(--accent)] bg-[var(--accent)] text-white" : "border-[var(--border)] bg-[var(--surface)] text-[var(--muted)] hover:text-[var(--foreground)]")} aria-pressed={preset === view.value}>
            {view.label}
          </button>
        ))}
      </div>
      <Badge className="hidden shrink-0 sm:inline-flex">{filteredCount}/{totalCount}</Badge>
      <Button variant={advancedCount > 0 ? "default" : "secondary"} onClick={onOpenFilters} className="shrink-0">
        <SlidersHorizontal size={16} /> Filtry {advancedCount > 0 ? <Badge className="bg-white/20 px-2 py-0.5 text-xs text-current">{advancedCount}</Badge> : null}
      </Button>
    </div>
  );
}

function ChallengeFilterDialog({ initial, categories, onApply, onClose }: { initial: ChallengeFilters; categories: { id: string; name: string }[]; onApply: (filters: ChallengeFilters) => void; onClose: () => void }) {
  const [draft, setDraft] = useState<ChallengeFilters>(initial);
  return (
    <Dialog.Root open onOpenChange={(next) => { if (!next) onClose(); }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/30" />
        <Dialog.Content className="fixed inset-x-0 bottom-0 z-[51] flex h-[96dvh] max-h-[96dvh] flex-col overflow-hidden rounded-t-[var(--radius-xl)] border border-[var(--border)] bg-[var(--surface)] shadow-2xl sm:inset-y-0 sm:left-auto sm:right-0 sm:h-dvh sm:w-full sm:max-w-xl sm:rounded-none sm:border-l">
          <div className="flex shrink-0 items-start justify-between gap-4 border-b border-[var(--border)] p-4 sm:p-6">
            <div className="min-w-0"><Dialog.Title className="text-lg font-semibold">Filtry návyků</Dialog.Title><Dialog.Description className="text-sm text-[var(--muted)]">Vyber jen výzvy, které chceš právě řešit.</Dialog.Description></div>
            <Dialog.Close asChild><Button variant="ghost" size="sm" aria-label="Zavřít filtry"><X size={18}/></Button></Dialog.Close>
          </div>
          <div className="grid min-h-0 flex-1 gap-3 overflow-y-auto p-4 pb-24 sm:p-6">
            <Select label="Typ návyku" value={draft.type} onChange={(value) => setDraft((current) => ({ ...current, type: value as ChallengeType | "all" }))} options={[{ value: "all", label: "Libovolný typ" }, { value: "daily_action", label: "Denní akce" }, { value: "abstinence", label: "Abstinence" }]} />
            <Select label="Kategorie" value={draft.categoryId} onChange={(value) => setDraft((current) => ({ ...current, categoryId: value }))} options={[{ value: "all", label: "Libovolná kategorie" }, ...categories.map((category) => ({ value: category.id, label: category.name }))]} />
            <Select label="Stav" value={draft.status} onChange={(value) => setDraft((current) => ({ ...current, status: value as ChallengeFilters["status"] }))} options={[{ value: "all", label: "Libovolný stav" }, { value: "active", label: "Aktivní" }, { value: "paused", label: "Pozastavené" }]} />
            <Select label="Šňůra" value={draft.streak} onChange={(value) => setDraft((current) => ({ ...current, streak: value as ChallengeFilters["streak"] }))} options={[{ value: "all", label: "Libovolná" }, { value: "zero", label: "Bez šňůry" }, { value: "short", label: "Krátká do 3 dnů" }, { value: "strong", label: "Silná 7+ dnů" }]} />
          </div>
          <div className="relative z-10 flex shrink-0 justify-end gap-2 border-t border-[var(--border)] bg-[var(--surface)] p-4 pb-[calc(1rem+env(safe-area-inset-bottom))] sm:p-6">
            <Button type="button" variant="ghost" onClick={() => onApply(defaultChallengeFilters)}>Vyčistit</Button>
            <Button type="button" onClick={() => onApply(draft)}>Použít filtry</Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function Select({ label, value, options, onChange }: { label: string; value: string; options: Array<{ value: string; label: string }>; onChange: (value: string) => void }) {
  return <label className="grid gap-1 text-sm font-medium">{label}<select className="focus-ring min-h-11 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-3 text-sm" value={value} onChange={(event) => onChange(event.target.value)}>{options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>;
}

function todayPrague() {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Prague", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
}

function ChallengeCard({ challenge, expanded, pending, pendingDate, year, onToggleDetail, onOneTap, onEdit, onDelete, onCheckInToggle }: {
  challenge: Challenge;
  expanded: boolean;
  pending: boolean;
  pendingDate: string | null;
  year: number;
  onToggleDetail: () => void;
  onOneTap: () => void;
  onEdit: () => void;
  onDelete: () => void;
  onCheckInToggle: (challenge: Challenge, day: ChallengeHeatmapDay) => void;
}) {
  const Icon = challenge.type === "abstinence" ? ShieldCheck : Activity;
  const todayStr = todayPrague();
  const todayHeatmap = useChallengeHeatmap(challenge.id, Number(todayStr.slice(0, 4)));
  const todayCell = todayHeatmap.data?.days.find((day) => day.date === todayStr);
  const checkedToday = Boolean(todayCell?.has_check_in);
  const doneLabel = challenge.type === "abstinence" ? "Relaps zapsán" : "Splněno dnes";
  const todoLabel = challenge.type === "abstinence" ? "Zapsat relaps" : "Hotovo dnes";
  return (
    <article className={cn("panel min-w-0 max-w-full p-4 transition sm:p-5", expanded && "ring-2 ring-[var(--primary)]")}>
      <button className="w-full min-w-0 text-left" onClick={onToggleDetail}>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="flex size-9 items-center justify-center rounded-2xl text-white" style={{ background: challenge.color }}><Icon size={18} /></span>
              <div>
                <h3 className="truncate font-semibold">{challenge.title}</h3>
                <p className="text-xs text-[var(--muted)]">
                  {challengeTypeLabels[challenge.type]}
                  {!challenge.is_active ? " · pozastaveno" : ""}
                </p>
              </div>
            </div>
            {challenge.description ? <p className="mt-3 line-clamp-2 text-sm text-[var(--muted)]">{challenge.description}</p> : null}
          </div>
          <div className="text-right">
            <p className="text-3xl font-semibold tabular-nums sm:text-4xl">{challenge.current_streak}</p>
            <p className="text-xs text-[var(--muted)]">{czechPlural(challenge.current_streak, "den", "dny", "dní")} šňůra</p>
          </div>
        </div>
      </button>
      <div className="mt-4 flex min-w-0 flex-wrap items-center justify-between gap-2">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <Badge>rekord {formatCzechCount(challenge.longest_streak, "den", "dny", "dní")}</Badge>
          {challenge.target_days ? <Badge>cíl {formatCzechCount(challenge.target_days, "den", "dny", "dní")}</Badge> : null}
        </div>
        <div className="flex min-w-0 flex-wrap items-center justify-end gap-1">
          <Button
            size="sm"
            variant={checkedToday ? "secondary" : challenge.type === "abstinence" ? "danger" : "default"}
            onClick={onOneTap}
            disabled={pending || checkedToday}
            aria-pressed={checkedToday}
            className={cn(checkedToday && "border-[var(--success)] bg-[var(--success)]/12 text-[var(--success)]")}
          >
            {challenge.type === "abstinence" ? <Flame size={15} /> : <CheckCircle2 size={15} />} {checkedToday ? doneLabel : todoLabel}
          </Button>
          <ActionButton icon="edit" label="Upravit výzvu" onClick={onEdit} />
          <ActionButton icon="delete" label="Smazat výzvu" danger onClick={onDelete} />
        </div>
      </div>
      {expanded ? (
        <ChallengeDetail challenge={challenge} year={year} pendingDate={pendingDate} onCheckInToggle={onCheckInToggle} />
      ) : null}
    </article>
  );
}

function ChallengeDetail({ challenge, year, pendingDate, onCheckInToggle }: {
  challenge: Challenge;
  year: number;
  pendingDate: string | null;
  onCheckInToggle: (challenge: Challenge, day: ChallengeHeatmapDay) => void;
}) {
  const stats = useChallengeStats(challenge.id);
  const heatmap = useChallengeHeatmap(challenge.id, year);
  const todayStr = useMemo(() => todayPrague(), []);
  const cutoffStr = useMemo(() => {
    const cutoff = new Date(`${todayStr}T00:00:00`);
    cutoff.setDate(cutoff.getDate() - BACKFILL_LIMIT_DAYS);
    return cutoff.toISOString().slice(0, 10);
  }, [todayStr]);
  const recentCheckIns = useMemo(
    () =>
      (heatmap.data?.days ?? [])
        .filter((day) => day.has_check_in)
        .sort((a, b) => (a.date < b.date ? 1 : -1))
        .slice(0, 5),
    [heatmap.data?.days],
  );

  return (
    <div className="mt-4 grid min-w-0 max-w-full gap-4 overflow-hidden border-t border-[var(--border)] pt-4">
      <div className="grid min-w-0 grid-cols-1 gap-2 text-sm min-[420px]:grid-cols-2 lg:grid-cols-4">
        <Metric label="Aktuální šňůra" value={formatCzechCount(challenge.current_streak, "den", "dny", "dní")} />
        <Metric label="Rekordní šňůra" value={formatCzechCount(challenge.longest_streak, "den", "dny", "dní")} />
        <Metric label="Zápisů celkem" value={stats.data?.total_count ?? "—"} />
        <Metric label="Úspěšnost 30 / 90 dní" value={`${formatSuccessWindow(stats.data?.success_rate_30, stats.data?.active_days_30, 30)} / ${formatSuccessWindow(stats.data?.success_rate_90, stats.data?.active_days_90, 90)}`} />
      </div>
      <div className="min-w-0 max-w-full overflow-hidden">
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">Heatmapa · {year}</p>
        {heatmap.isLoading ? (
          <p className="mt-2 text-sm text-[var(--muted)]">Načítám heatmapu…</p>
        ) : (
          <ContributionHeatmap
            days={heatmap.data?.days ?? []}
            color={challenge.color}
            todayStr={todayStr}
            cutoffStr={cutoffStr}
            pendingDate={pendingDate}
            onDayClick={(day) => onCheckInToggle(challenge, day)}
          />
        )}
      </div>
      <div className="min-w-0 max-w-full">
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">Poslední zápisy</p>
        {recentCheckIns.length ? (
          <ul className="mt-2 grid gap-1 text-sm">
            {recentCheckIns.map((day) => (
              <li key={day.date} className="flex items-center justify-between rounded-[var(--radius-sm)] bg-[var(--surface-muted)] px-2.5 py-1.5">
                <span>{formatDateLong(day.date)}</span>
                <span className="text-xs text-[var(--muted)]">{day.is_relapse ? "relaps" : day.value !== null ? `hodnota ${day.value}` : "hotovo"}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-sm text-[var(--muted)]">Zatím žádné zápisy.</p>
        )}
      </div>
    </div>
  );
}

function formatSuccessWindow(rate: number | undefined, activeDays: number | undefined, windowDays: number) {
  if (rate === undefined || activeDays === undefined) return "—";
  if (activeDays < windowDays) return `běží ${formatCzechCount(activeDays, "den", "dny", "dní")}`;
  return `${rate}%`;
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return <div className="min-w-0 rounded-[var(--radius-md)] bg-[var(--surface-muted)] p-2.5 sm:p-3"><p className="text-xs text-[var(--muted)]">{label}</p><p className="break-words font-semibold leading-snug">{value}</p></div>;
}

function ContributionHeatmap({ days, color, todayStr, cutoffStr, pendingDate, onDayClick }: {
  days: ChallengeHeatmapDay[];
  color: string;
  todayStr: string;
  cutoffStr: string;
  pendingDate: string | null;
  onDayClick: (day: ChallengeHeatmapDay) => void;
}) {
  const weeks = useMemo(() => buildHeatmapWeeks(days), [days]);
  const monthLabels = useMemo(() => buildMonthLabels(weeks), [weeks]);
  if (!days.length) return <p className="text-sm text-[var(--muted)]">Zatím nejsou žádné dny k vykreslení.</p>;
  return (
    <div className="w-full max-w-full overflow-hidden" aria-label="Heatmapa návyků podle rozvrhu">
      <div className="overflow-x-auto overscroll-x-contain pb-2">
        <div className="grid w-max max-w-none grid-cols-[1.75rem_auto] gap-x-1 [--cell:1.65rem] sm:grid-cols-[2rem_auto] sm:gap-x-2 sm:[--cell:0.9rem]">
        <div className="sticky left-0 z-10 bg-[var(--surface)]" />
        <div className="grid gap-1" style={{ gridTemplateColumns: `repeat(${weeks.length}, var(--cell))` }}>
          {monthLabels.map((label, index) => (
            <div key={`${label}-${index}`} className="h-5 text-[10px] text-[var(--muted)]">{label}</div>
          ))}
        </div>
        <div className="sticky left-0 z-10 grid grid-rows-7 gap-1 bg-[var(--surface)] pr-1 text-[10px] text-[var(--muted)]">
          {weekDayAxis.map((label, index) => (
            <span key={`${label}-${index}`} className="flex h-[var(--cell)] items-center justify-end">{label}</span>
          ))}
        </div>
        <div className="grid grid-flow-col grid-rows-7 gap-1">
          {weeks.flatMap((week, weekIndex) =>
            week.map((day, dayIndex) => {
              if (!day) return <div key={`empty-${weekIndex}-${dayIndex}`} className="size-[var(--cell)] opacity-0" />;
              const clickable = day.is_scheduled && day.date <= todayStr && day.date >= cutoffStr;
              return (
                <button
                  key={day.date}
                  type="button"
                  disabled={!clickable || pendingDate === day.date}
                  onClick={() => onDayClick(day)}
                  className={cn(
                    "focus-ring size-[var(--cell)] rounded-[3px] transition disabled:cursor-not-allowed disabled:opacity-40",
                    day.is_scheduled ? "border border-[var(--border)]" : "border border-transparent opacity-45",
                    clickable && "cursor-pointer hover:ring-2 hover:ring-[var(--accent)]",
                  )}
                  style={{ background: heatColor(color, day) }}
                  title={heatTooltip(day)}
                  aria-label={`${formatDateLong(day.date)}${clickable ? "" : " – nelze zapsat"}`}
                />
              );
            })
          )}
        </div>
        </div>
      </div>
    </div>
  );
}

const weekDayAxis = ["Po", "", "St", "", "Pá", "", ""];
const shortMonths = ["Led", "Úno", "Bře", "Dub", "Kvě", "Čvn", "Čvc", "Srp", "Zář", "Říj", "Lis", "Pro"];

function buildHeatmapWeeks(days: ChallengeHeatmapDay[]) {
  if (!days.length) return [];
  const first = new Date(`${days[0].date}T00:00:00`);
  const mondayBased = (first.getDay() + 6) % 7;
  const cells: Array<ChallengeHeatmapDay | null> = [...Array.from<null>({ length: mondayBased }).fill(null), ...days];
  while (cells.length % 7 !== 0) cells.push(null);
  const weeks: Array<Array<ChallengeHeatmapDay | null>> = [];
  for (let index = 0; index < cells.length; index += 7) weeks.push(cells.slice(index, index + 7));
  return weeks;
}

function buildMonthLabels(weeks: Array<Array<ChallengeHeatmapDay | null>>) {
  let previousMonth = -1;
  return weeks.map((week) => {
    const firstDay = week.find(Boolean);
    if (!firstDay) return "";
    const month = new Date(`${firstDay.date}T00:00:00`).getMonth();
    if (month === previousMonth) return "";
    previousMonth = month;
    return shortMonths[month];
  });
}

function heatColor(color: string, day: ChallengeHeatmapDay) {
  if (day.is_paused) return "var(--surface-muted)";
  if (!day.is_scheduled) return "color-mix(in srgb, var(--surface-muted) 70%, transparent)";
  if (day.intensity === 0) return "var(--surface-muted)";
  const alpha = [0, 0.25, 0.45, 0.68, 0.95][day.intensity] ?? 0.25;
  return `${color}${Math.round(alpha * 255).toString(16).padStart(2, "0")}`;
}

function heatTooltip(day: ChallengeHeatmapDay) {
  const parts = [formatDateLong(day.date)];
  parts.push(day.is_scheduled ? "v rozvrhu" : "mimo rozvrh");
  if (day.value !== null) parts.push(`hodnota: ${day.value}`);
  if (day.is_relapse) parts.push("relaps");
  if (day.is_paused) parts.push("pauza");
  if (day.note) parts.push(day.note);
  return parts.join(" · ");
}

function formatDateLong(value: string) {
  return new Intl.DateTimeFormat("cs-CZ", { dateStyle: "medium" }).format(new Date(`${value}T00:00:00`));
}
