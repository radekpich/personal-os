"use client";

import { useEffect, useMemo, useState } from "react";
import { Frequency, RRule, rrulestr, type Options, type Weekday } from "rrule";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type FrequencyValue = "daily" | "weekly" | "monthly" | "yearly";
type EndMode = "never" | "count" | "until";
type MonthlyMode = "monthday" | "weekday";

type State = {
  enabled: boolean;
  frequency: FrequencyValue;
  interval: number;
  weekdays: number[];
  monthlyMode: MonthlyMode;
  monthday: number;
  ordinal: number;
  ordinalWeekday: number;
  endMode: EndMode;
  count: number;
  until: string;
  expanded: boolean;
};

type Props = {
  value: string | null | undefined;
  onChange: (value: string | null) => void;
  allowNone?: boolean;
  defaultRRule?: string;
  label?: string;
  helperText?: string;
};

const DEFAULT_RRULE = "FREQ=DAILY";
const weekdayRules = [RRule.MO, RRule.TU, RRule.WE, RRule.TH, RRule.FR, RRule.SA, RRule.SU];
const weekdayCodes = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"];
const weekdayLabels = ["Po", "Út", "St", "Čt", "Pá", "So", "Ne"];
const weekdayNames = ["pondělí", "úterý", "středu", "čtvrtek", "pátek", "sobotu", "neděli"];
const monthNames = ["ledna", "února", "března", "dubna", "května", "června", "července", "srpna", "září", "října", "listopadu", "prosince"];
const ordinalLabels: Record<number, string> = { 1: "první", 2: "druhé", 3: "třetí", 4: "čtvrté", [-1]: "poslední" };

const presets = [
  { label: "Denně", rrule: "FREQ=DAILY" },
  { label: "Každý pracovní den", rrule: "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR" },
  { label: "Týdně", rrule: "FREQ=WEEKLY" },
  { label: "3× týdně", rrule: "FREQ=WEEKLY;BYDAY=MO,WE,FR" },
  { label: "Měsíčně", rrule: "FREQ=MONTHLY" },
];

export function RecurrenceBuilder({
  value,
  onChange,
  allowNone = false,
  defaultRRule = DEFAULT_RRULE,
  label = "Opakování",
  helperText,
}: Props) {
  const [state, setState] = useState<State>(() => parseRule(value, allowNone, defaultRRule));

  useEffect(() => {
    setState(parseRule(value, allowNone, defaultRRule));
  }, [value, allowNone, defaultRRule]);

  const rule = useMemo(() => (state.enabled ? buildRule(state) : null), [state]);
  const summary = useMemo(() => (rule ? summarizeRule(rule) : "Bez opakování"), [rule]);

  function update(next: Partial<State>) {
    setState((previous) => {
      const merged = normalizeState({ ...previous, ...next });
      onChange(merged.enabled ? buildRule(merged).toString().replace(/^RRULE:/, "") : null);
      return merged;
    });
  }

  function applyPreset(rrule: string) {
    const parsed = parseRule(rrule, false, defaultRRule);
    const next = { ...parsed, enabled: true, expanded: false };
    setState(next);
    onChange(buildRule(next).toString().replace(/^RRULE:/, ""));
  }

  return (
    <section className="grid gap-3 rounded-[var(--radius-lg)] border border-[var(--border)] p-3 sm:p-4">
      <div className="grid gap-1">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <p className="text-sm font-semibold">{label}</p>
            {helperText ? <p className="text-xs text-[var(--muted)]">{helperText}</p> : null}
          </div>
          {allowNone ? (
            <Button type="button" size="sm" variant={state.enabled ? "secondary" : "default"} onClick={() => update({ enabled: !state.enabled })}>
              {state.enabled ? "Vypnout" : "Zapnout"}
            </Button>
          ) : null}
        </div>
        <p className="rounded-[var(--radius-md)] bg-[var(--surface-muted)] px-3 py-2 text-sm font-medium">{summary}</p>
      </div>

      {state.enabled ? (
        <>
          <div className="flex flex-wrap gap-2">
            {presets.map((preset) => (
              <button
                key={preset.label}
                type="button"
                onClick={() => applyPreset(preset.rrule)}
                className={cn(
                  "focus-ring rounded-full border border-[var(--border)] px-3 py-1.5 text-sm transition",
                  rule?.toString().replace(/^RRULE:/, "") === preset.rrule
                    ? "bg-[var(--primary)] text-white"
                    : "bg-[var(--surface)] text-[var(--foreground)] hover:bg-[var(--surface-muted)]"
                )}
              >
                {preset.label}
              </button>
            ))}
          </div>
          <button type="button" className="w-fit text-sm font-medium text-[var(--primary)] underline-offset-4 hover:underline" onClick={() => update({ expanded: !state.expanded })}>
            {state.expanded ? "Skrýt vlastní nastavení" : "Vlastní nastavení"}
          </button>
          {state.expanded ? <CustomControls state={state} update={update} /> : null}
        </>
      ) : null}
    </section>
  );
}

function CustomControls({ state, update }: { state: State; update: (next: Partial<State>) => void }) {
  return (
    <div className="grid gap-4 rounded-[var(--radius-md)] bg-[var(--surface-muted)] p-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="grid gap-1 text-sm font-medium">
          Frekvence
          <select className="focus-ring min-h-10 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-3 text-sm" value={state.frequency} onChange={(event) => update({ frequency: event.target.value as FrequencyValue })}>
            <option value="daily">Denně</option>
            <option value="weekly">Týdně</option>
            <option value="monthly">Měsíčně</option>
            <option value="yearly">Ročně</option>
          </select>
        </label>
        <label className="grid gap-1 text-sm font-medium">
          Interval
          <span className="flex items-center gap-2">
            <span>Každý</span>
            <Input className="w-20" type="number" min={1} max={99} value={state.interval} onChange={(event) => update({ interval: Number(event.target.value) || 1 })} />
            <span>{intervalUnit(state.frequency, state.interval)}</span>
          </span>
        </label>
      </div>

      {state.frequency === "weekly" ? (
        <div className="grid gap-2">
          <p className="text-sm font-medium">Dny v týdnu</p>
          <div className="flex flex-wrap gap-2">
            {weekdayLabels.map((label, index) => (
              <button
                key={label}
                type="button"
                onClick={() => update({ weekdays: toggleNumber(state.weekdays, index) })}
                className={cn(
                  "focus-ring min-w-10 rounded-full border px-3 py-1.5 text-sm font-medium",
                  state.weekdays.includes(index) ? "border-[var(--primary)] bg-[var(--primary)] text-white" : "border-[var(--border)] bg-[var(--surface)]"
                )}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {state.frequency === "monthly" ? (
        <div className="grid gap-3">
          <p className="text-sm font-medium">Měsíční opakování</p>
          <label className="flex items-center gap-2 text-sm">
            <input type="radio" checked={state.monthlyMode === "monthday"} onChange={() => update({ monthlyMode: "monthday" })} />
            Konkrétní den v měsíci
          </label>
          {state.monthlyMode === "monthday" ? (
            <label className="grid max-w-44 gap-1 text-sm font-medium">
              Den v měsíci
              <Input type="number" min={1} max={31} value={state.monthday} onChange={(event) => update({ monthday: Number(event.target.value) || 1 })} />
            </label>
          ) : null}
          <label className="flex items-center gap-2 text-sm">
            <input type="radio" checked={state.monthlyMode === "weekday"} onChange={() => update({ monthlyMode: "weekday" })} />
            Např. druhé pondělí v měsíci
          </label>
          {state.monthlyMode === "weekday" ? (
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="grid gap-1 text-sm font-medium">
                Pořadí
                <select className="focus-ring min-h-10 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-3 text-sm" value={state.ordinal} onChange={(event) => update({ ordinal: Number(event.target.value) })}>
                  <option value={1}>První</option>
                  <option value={2}>Druhé</option>
                  <option value={3}>Třetí</option>
                  <option value={4}>Čtvrté</option>
                  <option value={-1}>Poslední</option>
                </select>
              </label>
              <label className="grid gap-1 text-sm font-medium">
                Den
                <select className="focus-ring min-h-10 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-3 text-sm" value={state.ordinalWeekday} onChange={(event) => update({ ordinalWeekday: Number(event.target.value) })}>
                  {weekdayLabels.map((day, index) => <option key={day} value={index}>{weekdayNames[index]}</option>)}
                </select>
              </label>
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="grid gap-3">
        <p className="text-sm font-medium">Konec</p>
        <div className="grid gap-2 sm:grid-cols-3">
          <label className="flex items-center gap-2 text-sm"><input type="radio" checked={state.endMode === "never"} onChange={() => update({ endMode: "never" })} />Nikdy</label>
          <label className="flex items-center gap-2 text-sm"><input type="radio" checked={state.endMode === "count"} onChange={() => update({ endMode: "count" })} />Po N opakováních</label>
          <label className="flex items-center gap-2 text-sm"><input type="radio" checked={state.endMode === "until"} onChange={() => update({ endMode: "until" })} />Do data</label>
        </div>
        {state.endMode === "count" ? <Input className="max-w-44" type="number" min={1} max={999} value={state.count} onChange={(event) => update({ count: Number(event.target.value) || 1 })} /> : null}
        {state.endMode === "until" ? <Input className="max-w-56" type="date" value={state.until} onChange={(event) => update({ until: event.target.value })} /> : null}
      </div>
    </div>
  );
}

function parseRule(value: string | null | undefined, allowNone: boolean, defaultRRule: string): State {
  if (!value && allowNone) return { ...defaultState(defaultRRule), enabled: false };
  const source = value || defaultRRule || DEFAULT_RRULE;
  try {
    const rule = rrulestr(source) as RRule;
    const options = rule.origOptions as Partial<Options>;
    const frequency = frequencyFromRRule(options.freq ?? Frequency.DAILY);
    const byweekday = Array.isArray(options.byweekday) ? options.byweekday : options.byweekday !== undefined ? [options.byweekday] : [];
    const weekdays = byweekday.map(weekdayToIndex).filter((item): item is number => item !== null);
    const bymonthday = Array.isArray(options.bymonthday) ? options.bymonthday[0] : options.bymonthday;
    const bysetpos = Array.isArray(options.bysetpos) ? options.bysetpos[0] : options.bysetpos;
    const ordinalWeekday = weekdays[0] ?? 0;
    const until = options.until instanceof Date ? toDateInput(options.until) : "";
    return normalizeState({
      enabled: true,
      frequency,
      interval: options.interval ?? 1,
      weekdays,
      monthlyMode: frequency === "monthly" && bysetpos ? "weekday" : "monthday",
      monthday: typeof bymonthday === "number" ? bymonthday : 1,
      ordinal: typeof bysetpos === "number" ? bysetpos : 2,
      ordinalWeekday,
      endMode: options.count ? "count" : options.until ? "until" : "never",
      count: options.count ?? 10,
      until,
      expanded: false,
    });
  } catch {
    return defaultState(defaultRRule);
  }
}

function defaultState(defaultRRule: string): State {
  if (defaultRRule !== DEFAULT_RRULE) return parseRule(defaultRRule, false, DEFAULT_RRULE);
  return {
    enabled: true,
    frequency: "daily",
    interval: 1,
    weekdays: [],
    monthlyMode: "monthday",
    monthday: 1,
    ordinal: 2,
    ordinalWeekday: 0,
    endMode: "never",
    count: 10,
    until: "",
    expanded: false,
  };
}

function normalizeState(state: State): State {
  return {
    ...state,
    interval: clampInt(state.interval, 1, 99),
    weekdays: state.frequency === "weekly" ? (state.weekdays.length ? state.weekdays : [0]) : state.weekdays,
    monthday: clampInt(state.monthday, 1, 31),
    ordinal: [1, 2, 3, 4, -1].includes(state.ordinal) ? state.ordinal : 2,
    ordinalWeekday: clampInt(state.ordinalWeekday, 0, 6),
    count: clampInt(state.count, 1, 999),
  };
}

function buildRule(state: State): RRule {
  const options: Partial<Options> = {
    freq: frequencyToRRule(state.frequency),
    interval: state.interval,
  };
  if (state.frequency === "weekly") options.byweekday = state.weekdays.map((index) => weekdayRules[index]).filter(Boolean) as Weekday[];
  if (state.frequency === "monthly") {
    if (state.monthlyMode === "weekday") {
      options.byweekday = [weekdayRules[state.ordinalWeekday]];
      options.bysetpos = state.ordinal;
    } else {
      options.bymonthday = state.monthday;
    }
  }
  if (state.endMode === "count") options.count = state.count;
  if (state.endMode === "until" && state.until) options.until = new Date(`${state.until}T23:59:59`);
  return new RRule(options);
}

function summarizeRule(rule: RRule): string {
  const options = rule.origOptions as Partial<Options>;
  const frequency = frequencyFromRRule(options.freq ?? Frequency.DAILY);
  const interval = options.interval ?? 1;
  const byweekday = Array.isArray(options.byweekday) ? options.byweekday : options.byweekday !== undefined ? [options.byweekday] : [];
  const weekdays = byweekday.map(weekdayToIndex).filter((item): item is number => item !== null);
  const base = summarizeBase(frequency, interval, weekdays, options);
  const ending = summarizeEnding(options);
  return ending ? `${base}, ${ending}` : base;
}

function summarizeBase(frequency: FrequencyValue, interval: number, weekdays: number[], options: Partial<Options>): string {
  if (frequency === "daily") return interval === 1 ? "Každý den" : `Každý ${interval}. den`;
  if (frequency === "weekly") {
    const days = weekdays.length ? listCzech(weekdays.map((index) => weekdayNames[index])) : ["týden"];
    return interval === 1 ? `Každé ${days}` : `Každý ${interval}. týden: ${days}`;
  }
  if (frequency === "monthly") {
    const bysetpos = Array.isArray(options.bysetpos) ? options.bysetpos[0] : options.bysetpos;
    if (typeof bysetpos === "number" && weekdays.length) {
      const text = `${ordinalLabels[bysetpos] ?? `${bysetpos}.`} ${weekdayNames[weekdays[0]]} v měsíci`;
      return interval === 1 ? `Každé ${text}` : `Každý ${interval}. měsíc: ${text}`;
    }
    const bymonthday = Array.isArray(options.bymonthday) ? options.bymonthday[0] : options.bymonthday;
    const day = typeof bymonthday === "number" ? bymonthday : 1;
    return interval === 1 ? `Každý měsíc ${day}. dne` : `Každý ${interval}. měsíc ${day}. dne`;
  }
  return interval === 1 ? "Každý rok" : `Každý ${interval}. rok`;
}

function summarizeEnding(options: Partial<Options>): string | null {
  if (options.count) return `po ${options.count} opakováních`;
  if (options.until instanceof Date) return `do ${formatDate(options.until)}`;
  return null;
}

function frequencyToRRule(value: FrequencyValue) {
  return { daily: Frequency.DAILY, weekly: Frequency.WEEKLY, monthly: Frequency.MONTHLY, yearly: Frequency.YEARLY }[value];
}

function frequencyFromRRule(value: Frequency): FrequencyValue {
  if (value === Frequency.WEEKLY) return "weekly";
  if (value === Frequency.MONTHLY) return "monthly";
  if (value === Frequency.YEARLY) return "yearly";
  return "daily";
}

function weekdayToIndex(value: Weekday | number | string | null): number | null {
  if (value === null) return null;
  if (typeof value === "number") return value >= 0 && value <= 6 ? value : null;
  if (typeof value === "string") {
    const index = weekdayCodes.indexOf(value.slice(0, 2).toUpperCase());
    return index >= 0 ? index : null;
  }
  const weekday = value.weekday;
  return typeof weekday === "number" ? weekday : null;
}

function toggleNumber(values: number[], value: number) {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value].sort((a, b) => a - b);
}

function clampInt(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, Math.trunc(Number.isFinite(value) ? value : min)));
}

function intervalUnit(frequency: FrequencyValue, interval: number) {
  if (frequency === "daily") return interval === 1 ? "den" : "dny";
  if (frequency === "weekly") return interval === 1 ? "týden" : "týdny";
  if (frequency === "monthly") return interval === 1 ? "měsíc" : "měsíce";
  return interval === 1 ? "rok" : "roky";
}

function listCzech(items: string[]) {
  if (items.length <= 1) return items[0] ?? "";
  return `${items.slice(0, -1).join(", ")} a ${items.at(-1)}`;
}

function toDateInput(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function formatDate(date: Date) {
  return `${date.getDate()}. ${monthNames[date.getMonth()]} ${date.getFullYear()}`;
}
