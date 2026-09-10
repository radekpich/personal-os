"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { zodResolver } from "@hookform/resolvers/zod";
import { Activity, Flame, Plus, ShieldCheck, X } from "lucide-react";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import {
  useChallengeHeatmap,
  useChallengeStats,
  useChallenges,
  useCheckInChallenge,
  useCreateChallenge,
  useTaxonomy,
  useVisions,
} from "@/lib/api/hooks";
import type { Challenge, ChallengeHeatmapDay, ChallengeType } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { czechPlural, formatCzechCount } from "@/lib/czech";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";

const challengeTypeLabels: Record<ChallengeType, string> = {
  daily_action: "Denní akce",
  abstinence: "Abstinence",
};

const schema = z.object({
  title: z.string().min(1),
  description: z.string().nullable(),
  type: z.enum(["daily_action", "abstinence"]),
  category_id: z.string().nullable(),
  vision_id: z.string().nullable(),
  target_days: z.coerce.number().int().positive().nullable(),
  allowed_gap_days: z.coerce.number().int().min(0).max(30),
  color: z.string().regex(/^#[0-9a-fA-F]{6}$/),
  icon: z.string().min(1),
});

type FormInput = z.input<typeof schema>;
type Values = z.output<typeof schema>;

export function ChallengeWorkspace() {
  const challenges = useChallenges();
  const { categories } = useTaxonomy();
  const visions = useVisions();
  const create = useCreateChallenge();
  const checkIn = useCheckInChallenge();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const selected = useMemo(() => {
    const items = challenges.data?.items ?? [];
    return items.find((item) => item.id === selectedId) ?? items[0] ?? null;
  }, [challenges.data?.items, selectedId]);
  const year = new Date().getFullYear();
  const stats = useChallengeStats(selected?.id ?? null);
  const heatmap = useChallengeHeatmap(selected?.id ?? null, year);
  const form = useForm<FormInput, unknown, Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      title: "",
      description: "",
      type: "daily_action",
      category_id: null,
      vision_id: null,
      target_days: null,
      allowed_gap_days: 0,
      color: "#22c55e",
      icon: "activity",
    },
  });

  async function submit(values: Values) {
    const created = await create.mutateAsync({
      ...values,
      description: values.description || null,
      category_id: values.category_id || null,
      vision_id: values.vision_id || null,
      target_days: values.target_days || null,
      allowed_gap_days: values.type === "abstinence" ? 0 : values.allowed_gap_days,
    });
    setSelectedId(created.id);
    form.reset({
      title: "",
      description: "",
      type: "daily_action",
      category_id: null,
      vision_id: null,
      target_days: null,
      allowed_gap_days: 0,
      color: "#22c55e",
      icon: "activity",
    });
    setCreateOpen(false);
  }

  async function oneTap(challenge: Challenge) {
    await checkIn.mutateAsync({
      id: challenge.id,
      payload: challenge.type === "abstinence" ? { is_relapse: true } : { is_relapse: false },
    });
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_24rem]">
      <section className="grid gap-4">
        <div className="panel flex flex-wrap items-center justify-between gap-3 p-5">
          <div>
            <p className="text-sm text-[var(--muted)]">
              Daily akce se počítá z reálných zápisů; abstinence běží od startu a zapisuje jen relaps.
            </p>
            <h2 className="text-xl font-semibold">Návyky a výzvy</h2>
          </div>
          <Badge>{formatCzechCount(challenges.data?.items.length ?? 0, "aktivní měření", "aktivní měření", "aktivních měření")}</Badge>
          <Button onClick={() => setCreateOpen(true)}><Plus size={16}/>Nová výzva</Button>
        </div>

        {challenges.isLoading ? <p className="panel p-5 text-[var(--muted)]">Načítám návyky…</p> : null}
        {challenges.isError ? <p className="panel p-5 text-[var(--danger)]">Návyky se nepodařilo načíst.</p> : null}
        {!challenges.isLoading && !challenges.data?.items.length ? (
          <p className="panel p-5 text-[var(--muted)]">Zatím žádný návyk. Založ první výzvu tlačítkem nahoře.</p>
        ) : null}

        <div className="grid gap-3 md:grid-cols-2">
          {challenges.data?.items.map((challenge) => (
            <ChallengeCard
              key={challenge.id}
              challenge={challenge}
              selected={selected?.id === challenge.id}
              pending={checkIn.isPending}
              onSelect={() => setSelectedId(challenge.id)}
              onOneTap={() => oneTap(challenge)}
            />
          ))}
        </div>

        {selected ? (
          <div className="panel grid gap-4 p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm text-[var(--muted)]">Roční kalendářová mřížka · {year}</p>
                <h2 className="text-lg font-semibold">Heatmapa: {selected.title}</h2>
              </div>
              <div className="flex gap-2 text-xs text-[var(--muted)]">
                <span>30 dní: {formatSuccessWindow(stats.data?.success_rate_30, stats.data?.active_days_30, 30)}</span>
                <span>90 dní: {formatSuccessWindow(stats.data?.success_rate_90, stats.data?.active_days_90, 90)}</span>
              </div>
            </div>
            <ContributionHeatmap days={heatmap.data?.days ?? []} color={selected.color} />
          </div>
        ) : null}
      </section>

      <aside className="grid h-fit gap-4">
        {selected ? <StatsPanel challenge={selected} stats={stats.data} /> : null}
      </aside>

      <Dialog.Root open={createOpen} onOpenChange={setCreateOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/30" />
          <Dialog.Content className="fixed inset-x-0 bottom-0 z-50 flex max-h-[96dvh] flex-col overflow-hidden rounded-t-[var(--radius-xl)] border border-[var(--border)] bg-[var(--surface)] shadow-2xl sm:inset-y-0 sm:left-auto sm:right-0 sm:h-dvh sm:w-full sm:max-w-xl sm:rounded-none sm:border-l">
            <div className="flex items-start justify-between gap-4 border-b border-[var(--border)] p-4 sm:p-6">
              <div><Dialog.Title className="text-lg font-semibold">Nová výzva</Dialog.Title><Dialog.Description className="text-sm text-[var(--muted)]">Stejný dialogový vzor jako nový úkol a nový zápis. Limit zpětného zápisu je 7 dní.</Dialog.Description></div>
              <Dialog.Close asChild><Button variant="ghost" size="sm"><X size={18}/></Button></Dialog.Close>
            </div>
            <form className="flex min-h-0 flex-1 flex-col" onSubmit={form.handleSubmit(submit)}>
              <div className="grid flex-1 gap-4 overflow-y-auto p-4 pb-24 sm:p-6">
                <label className="grid gap-1 text-sm font-medium">Název<Input {...form.register("title")} placeholder="Švihadlo" autoFocus /></label>
                <label className="grid gap-1 text-sm font-medium">Popis<Textarea rows={3} {...form.register("description")} /></label>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Select label="Typ" {...form.register("type")}><option value="daily_action">Denní akce</option><option value="abstinence">Abstinence</option></Select>
                  <label className="grid gap-1 text-sm font-medium">Cíl dní<Input type="number" min={1} {...form.register("target_days")} /></label>
                  <label className="grid gap-1 text-sm font-medium">Grace dny<Input type="number" min={0} max={30} {...form.register("allowed_gap_days")} /></label>
                  <label className="grid gap-1 text-sm font-medium">Barva<Input type="color" {...form.register("color")} /></label>
                </div>
                <Select label="Kategorie" {...form.register("category_id")}><option value="">Bez kategorie</option>{categories.data?.items.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</Select>
                <Select label="Vize" {...form.register("vision_id")}><option value="">Bez vize</option>{visions.data?.items.map((vision) => <option key={vision.id} value={vision.id}>{vision.title}</option>)}</Select>
                <input type="hidden" {...form.register("icon")} />
              </div>
              <div className="sticky bottom-0 flex justify-end gap-2 border-t border-[var(--border)] bg-[var(--surface)] p-4 pb-[calc(1rem+env(safe-area-inset-bottom))] sm:p-6">
                <Button type="button" variant="ghost" onClick={() => setCreateOpen(false)}>Zrušit</Button>
                <Button disabled={create.isPending}>Uložit</Button>
              </div>
            </form>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}

function ChallengeCard({ challenge, selected, pending, onSelect, onOneTap }: {
  challenge: Challenge;
  selected: boolean;
  pending: boolean;
  onSelect: () => void;
  onOneTap: () => void;
}) {
  const Icon = challenge.type === "abstinence" ? ShieldCheck : Activity;
  return (
    <article className={cn("panel p-5 transition", selected && "ring-2 ring-[var(--primary)]")}>
      <button className="w-full text-left" onClick={onSelect}>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="flex size-9 items-center justify-center rounded-2xl text-white" style={{ background: challenge.color }}><Icon size={18} /></span>
              <div>
                <h3 className="truncate font-semibold">{challenge.title}</h3>
                <p className="text-xs text-[var(--muted)]">{challengeTypeLabels[challenge.type]}</p>
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
        <Badge>rekord {formatCzechCount(challenge.longest_streak, "den", "dny", "dní")}</Badge>
        {challenge.target_days ? <Badge>cíl {formatCzechCount(challenge.target_days, "den", "dny", "dní")}</Badge> : null}
        <Button size="sm" variant={challenge.type === "abstinence" ? "danger" : "default"} onClick={onOneTap} disabled={pending}>
          <Flame size={15} /> {challenge.type === "abstinence" ? "Zapsat relaps" : "Zapsat dnešek"}
        </Button>
      </div>
    </article>
  );
}

function StatsPanel({ challenge, stats }: { challenge: Challenge; stats?: { total_count: number; success_rate_30: number; success_rate_90: number; active_days_30: number; active_days_90: number } }) {
  return (
    <div className="panel grid gap-3 p-4 text-sm sm:p-5">
      <h2 className="font-semibold">Statistiky: {challenge.title}</h2>
      <div className="grid grid-cols-2 gap-2">
        <Metric label="Zápisů" value={stats?.total_count ?? "—"} />
        <Metric label="Rekord" value={formatCzechCount(challenge.longest_streak, "den", "dny", "dní")} />
        <Metric label="Úspěšnost 30d" value={formatSuccessWindow(stats?.success_rate_30, stats?.active_days_30, 30)} />
        <Metric label="Úspěšnost 90d" value={formatSuccessWindow(stats?.success_rate_90, stats?.active_days_90, 90)} />
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

function ContributionHeatmap({ days, color }: { days: ChallengeHeatmapDay[]; color: string }) {
  const padded = useMemo(() => padHeatmap(days), [days]);
  return (
    <div className="overflow-x-auto pb-20 md:pb-2" aria-label="Roční heatmapa návyků">
      <div className="grid w-max grid-flow-col grid-rows-7 gap-1">
        {padded.map((day, index) => (
          <div
            key={day?.date ?? `empty-${index}`}
            className={cn("size-3 rounded-[3px] border border-[var(--border)]", !day && "opacity-0")}
            style={{ background: day ? heatColor(color, day.intensity, day.is_paused) : "transparent" }}
            title={day ? `${day.date}${day.note ? ` · ${day.note}` : ""}${day.is_paused ? " · pauza" : ""}` : undefined}
          />
        ))}
      </div>
    </div>
  );
}

function padHeatmap(days: ChallengeHeatmapDay[]) {
  if (!days.length) return [];
  const first = new Date(`${days[0].date}T00:00:00`);
  const mondayBased = (first.getDay() + 6) % 7;
  return [...Array.from<null>({ length: mondayBased }).fill(null), ...days];
}

function heatColor(color: string, intensity: number, paused: boolean) {
  if (paused) return "var(--surface-muted)";
  if (intensity === 0) return "var(--surface-muted)";
  const alpha = [0, 0.25, 0.45, 0.68, 0.95][intensity] ?? 0.25;
  return `${color}${Math.round(alpha * 255).toString(16).padStart(2, "0")}`;
}

function Select({ label, children, ...props }: React.SelectHTMLAttributes<HTMLSelectElement> & { label: string }) {
  return <label className="grid gap-1 text-sm font-medium">{label}<select className="focus-ring min-h-11 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-3 text-base" {...props}>{children}</select></label>;
}
