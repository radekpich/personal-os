"use client";

import { Activity, Flame, Pencil, Plus, ShieldCheck, Trash2 } from "lucide-react";
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
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { FilterBar, FilterSelect } from "@/components/ui/filter-bar";
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
  const [typeFilter, setTypeFilter] = useState("all");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");

  const year = new Date().getFullYear();
  const deleteImpact = useChallengeStats(deleteTarget?.id ?? null);

  const filteredChallenges = useMemo(() => {
    const items = challenges.data?.items ?? [];
    return items.filter((challenge) => {
      if (typeFilter !== "all" && challenge.type !== typeFilter) return false;
      if (categoryFilter !== "all" && challenge.category_id !== categoryFilter) return false;
      if (statusFilter === "active" && !challenge.is_active) return false;
      if (statusFilter === "paused" && challenge.is_active) return false;
      return true;
    });
  }, [challenges.data?.items, typeFilter, categoryFilter, statusFilter]);

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
      payload: challenge.type === "abstinence" ? { is_relapse: true } : { is_relapse: false },
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
    <div className="grid gap-4">
      <div className="panel flex flex-wrap items-center justify-between gap-3 p-5">
        <div>
          <p className="text-sm text-[var(--muted)]">
            Daily akce se počítá z reálných zápisů; abstinence běží od startu a zapisuje jen relaps.
          </p>
          <h2 className="text-xl font-semibold">Návyky a výzvy</h2>
        </div>
        <Badge>{formatCzechCount(challenges.data?.items.length ?? 0, "aktivní měření", "aktivní měření", "aktivních měření")}</Badge>
        <Button onClick={openCreate}><Plus size={16}/>Nová výzva</Button>
      </div>

      <Filters
        type={typeFilter}
        categoryId={categoryFilter}
        status={statusFilter}
        categories={categories.data?.items ?? []}
        onType={setTypeFilter}
        onCategory={setCategoryFilter}
        onStatus={setStatusFilter}
      />

      {challenges.isLoading ? <p className="panel p-5 text-[var(--muted)]">Načítám návyky…</p> : null}
      {challenges.isError ? <p className="panel p-5 text-[var(--danger)]">Návyky se nepodařilo načíst.</p> : null}
      {!challenges.isLoading && !filteredChallenges.length ? (
        <p className="panel p-5 text-[var(--muted)]">
          {challenges.data?.items.length ? "Žádná výzva neodpovídá filtru." : "Zatím žádný návyk. Založ první výzvu tlačítkem nahoře."}
        </p>
      ) : null}

      <div className="grid gap-3 md:grid-cols-2">
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

function Filters({ type, categoryId, status, categories, onType, onCategory, onStatus }: {
  type: string;
  categoryId: string;
  status: string;
  categories: { id: string; name: string }[];
  onType: (value: string) => void;
  onCategory: (value: string) => void;
  onStatus: (value: string) => void;
}) {
  return (
    <FilterBar>
      <FilterSelect
        aria-label="Typ"
        value={type}
        onChange={onType}
        options={[{ value: "all", label: "Všechny typy" }, { value: "daily_action", label: "Denní akce" }, { value: "abstinence", label: "Abstinence" }]}
      />
      <FilterSelect
        aria-label="Kategorie"
        value={categoryId}
        onChange={onCategory}
        options={[{ value: "all", label: "Všechny kategorie" }, ...categories.map((category) => ({ value: category.id, label: category.name }))]}
      />
      <FilterSelect
        aria-label="Stav"
        value={status}
        onChange={onStatus}
        options={[{ value: "all", label: "Vše" }, { value: "active", label: "Aktivní" }, { value: "paused", label: "Pozastavené" }]}
      />
    </FilterBar>
  );
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
  return (
    <article className={cn("panel p-5 transition", expanded && "ring-2 ring-[var(--primary)]")}>
      <button className="w-full text-left" onClick={onToggleDetail}>
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
      <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <Badge>rekord {formatCzechCount(challenge.longest_streak, "den", "dny", "dní")}</Badge>
          {challenge.target_days ? <Badge>cíl {formatCzechCount(challenge.target_days, "den", "dny", "dní")}</Badge> : null}
        </div>
        <div className="flex items-center gap-1">
          <Button size="sm" variant={challenge.type === "abstinence" ? "danger" : "default"} onClick={onOneTap} disabled={pending}>
            <Flame size={15} /> {challenge.type === "abstinence" ? "Zapsat relaps" : "Zapsat dnešek"}
          </Button>
          <Button variant="ghost" size="sm" onClick={onEdit} aria-label="Upravit výzvu"><Pencil size={15} /></Button>
          <Button variant="ghost" size="sm" onClick={onDelete} aria-label="Smazat výzvu"><Trash2 size={15} /></Button>
        </div>
      </div>
      {expanded ? (
        <ChallengeDetail challenge={challenge} year={year} pendingDate={pendingDate} onEdit={onEdit} onDelete={onDelete} onCheckInToggle={onCheckInToggle} />
      ) : null}
    </article>
  );
}

function ChallengeDetail({ challenge, year, pendingDate, onEdit, onDelete, onCheckInToggle }: {
  challenge: Challenge;
  year: number;
  pendingDate: string | null;
  onEdit: () => void;
  onDelete: () => void;
  onCheckInToggle: (challenge: Challenge, day: ChallengeHeatmapDay) => void;
}) {
  const stats = useChallengeStats(challenge.id);
  const heatmap = useChallengeHeatmap(challenge.id, year);
  const todayStr = useMemo(() => new Date().toISOString().slice(0, 10), []);
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
    <div className="mt-4 grid gap-4 border-t border-[var(--border)] pt-4">
      <div className="flex flex-wrap justify-end gap-2">
        <Button variant="ghost" size="sm" onClick={onEdit}><Pencil size={15} />Upravit</Button>
        <Button variant="ghost" size="sm" onClick={onDelete}><Trash2 size={15} />Smazat</Button>
      </div>
      <div className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
        <Metric label="Aktuální šňůra" value={formatCzechCount(challenge.current_streak, "den", "dny", "dní")} />
        <Metric label="Rekordní šňůra" value={formatCzechCount(challenge.longest_streak, "den", "dny", "dní")} />
        <Metric label="Zápisů celkem" value={stats.data?.total_count ?? "—"} />
        <Metric label="Úspěšnost 30 / 90 dní" value={`${formatSuccessWindow(stats.data?.success_rate_30, stats.data?.active_days_30, 30)} / ${formatSuccessWindow(stats.data?.success_rate_90, stats.data?.active_days_90, 90)}`} />
      </div>
      <div>
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
      <div>
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
  return <div className="rounded-[var(--radius-md)] bg-[var(--surface-muted)] p-2.5 sm:p-3"><p className="text-xs text-[var(--muted)]">{label}</p><p className="font-semibold">{value}</p></div>;
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
    <div className="overflow-x-auto pb-2" aria-label="Heatmapa návyků podle rozvrhu">
      <div className="grid w-max grid-cols-[2rem_auto] gap-x-2 [--cell:1.75rem] sm:[--cell:0.9rem]">
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
