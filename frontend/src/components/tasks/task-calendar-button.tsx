"use client";

import { CalendarPlus, ExternalLink, RefreshCcw, Unlink, X } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
import type { ExternalCalendar, Task } from "@/lib/api/types";
import {
  useCreateCalendarRequest,
  useDisconnectCalendarRequest,
  useExternalCalendars,
  useRetryCalendarRequest,
  useUpdateTask,
} from "@/lib/api/hooks";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

const durations = [15, 30, 60, 120];

export function TaskCalendarButton({ task }: { task: Task }) {
  const calendars = useExternalCalendars();
  const createRequest = useCreateCalendarRequest();
  const updateTask = useUpdateTask();
  const [open, setOpen] = useState(false);
  const writable = useMemo(
    () => (calendars.data?.items ?? []).filter((calendar) => calendar.can_write && calendar.is_enabled),
    [calendars.data?.items],
  );
  const defaultCalendar = writable.find((calendar) => calendar.is_default) ?? writable[0] ?? null;

  async function quickCreate() {
    if (!defaultCalendar || !task.due_date || !task.due_time) {
      setOpen((value) => !value);
      return;
    }
    await createCalendarRequest(task, defaultCalendar, task.due_date, task.due_time, task.estimate_minutes ?? 30, false);
  }

  async function createCalendarRequest(
    sourceTask: Task,
    calendar: ExternalCalendar,
    date: string,
    time: string,
    durationMinutes: number,
    reminder: boolean,
  ) {
    const normalizedTime = toTimeInput(time);
    const start = `${date}T${normalizedTime}:00`;
    const endDate = new Date(`${date}T${normalizedTime}:00`);
    endDate.setMinutes(endDate.getMinutes() + durationMinutes);
    const end = toLocalInput(endDate);
    await createRequest.mutateAsync({
      task: sourceTask,
      payload: {
        operation: "create",
        calendar_external_id: calendar.external_id,
        title: sourceTask.title,
        description: sourceTask.description,
        starts_at: start,
        ends_at: end,
        all_day: false,
        reminder_minutes: reminder ? 15 : null,
        idempotency_key: `${sourceTask.id}:create:${calendar.external_id}:${start}`,
      },
    });
  }

  return (
    <div className="relative">
      <button
        type="button"
        className="focus-ring grid size-9 place-items-center rounded-[var(--radius-sm)] text-[var(--muted)] hover:bg-[var(--surface-muted)] hover:text-[var(--foreground)] disabled:opacity-50"
        title="Zapsat do Google Kalendáře přes agenta"
        aria-label="Zapsat do Google Kalendáře"
        onClick={(event) => {
          event.stopPropagation();
          void quickCreate();
        }}
        disabled={calendars.isLoading || createRequest.isPending}
      >
        <CalendarPlus size={15} />
      </button>
      {open ? (
        <CalendarPopover
          task={task}
          calendars={writable}
          defaultCalendar={defaultCalendar}
          pending={createRequest.isPending || updateTask.isPending}
          onClose={() => setOpen(false)}
          onSubmit={async ({ calendar, date, time, duration, reminder }) => {
            const payload = { due_date: date, due_time: time, estimate_minutes: duration };
            const updated =
              task.due_date !== date || task.due_time !== time || task.estimate_minutes !== duration
                ? await updateTask.mutateAsync({ task, payload })
                : task;
            await createCalendarRequest(updated, calendar, date, time, duration, reminder);
            setOpen(false);
          }}
        />
      ) : null}
    </div>
  );
}

function CalendarPopover({
  task,
  calendars,
  defaultCalendar,
  pending,
  onClose,
  onSubmit,
}: {
  task: Task;
  calendars: ExternalCalendar[];
  defaultCalendar: ExternalCalendar | null;
  pending: boolean;
  onClose: () => void;
  onSubmit: (payload: { calendar: ExternalCalendar; date: string; time: string; duration: number; reminder: boolean }) => Promise<void>;
}) {
  const [calendarId, setCalendarId] = useState(defaultCalendar?.external_id ?? calendars[0]?.external_id ?? "");
  const [date, setDate] = useState(task.due_date ?? todayIso());
  const [time, setTime] = useState(task.due_time ? toTimeInput(task.due_time) : "09:00");
  const [duration, setDuration] = useState(task.estimate_minutes && durations.includes(task.estimate_minutes) ? task.estimate_minutes : 30);
  const [reminder, setReminder] = useState(false);
  const [showDateError, setShowDateError] = useState(false);
  const selectedCalendar = calendars.find((calendar) => calendar.external_id === calendarId) ?? null;

  function quickDate(kind: "today" | "tomorrow" | "monday") {
    const value = new Date();
    if (kind === "tomorrow") value.setDate(value.getDate() + 1);
    if (kind === "monday") {
      const day = value.getDay();
      const delta = day === 0 ? 1 : 8 - day;
      value.setDate(value.getDate() + delta);
    }
    setDate(toDateInput(value));
    setShowDateError(false);
  }

  return (
    <div
      className="absolute right-0 z-40 mt-1 grid max-h-[min(70dvh,520px)] w-[min(92vw,340px)] gap-3 overflow-y-auto rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-3 text-sm shadow-xl"
      onClick={(event) => event.stopPropagation()}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-semibold">Zapsat do kalendáře</p>
          <p className="text-xs text-[var(--muted)]">Požadavek provede agent, ne aplikace.</p>
        </div>
        <button type="button" className="text-[var(--muted)]" onClick={onClose} aria-label="Zavřít"><X size={16} /></button>
      </div>
      {!calendars.length ? (
        <p className="rounded-[var(--radius-md)] border border-dashed border-[var(--border)] p-3 text-[var(--muted)]">
          Agent zatím nenahlásil žádný zapisovatelný kalendář. Obnovu spusť na stránce <Link className="underline" href="/agent">Agent</Link> podle AGENT.md.
        </p>
      ) : (
        <>
          <label className="grid gap-1 font-medium">
            Kalendář
            <select className="focus-ring min-h-10 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-3" value={calendarId} onChange={(event) => setCalendarId(event.target.value)}>
              {calendars.map((calendar) => (
                <option key={calendar.external_id} value={calendar.external_id}>{calendar.name}{calendar.is_shared ? " · sdílený" : ""}</option>
              ))}
            </select>
          </label>
          <div className="flex flex-wrap gap-1.5">
            {calendars.map((calendar) => (
              <button key={calendar.external_id} type="button" onClick={() => setCalendarId(calendar.external_id)} className={cn("rounded-full border px-2 py-1 text-xs", calendar.external_id === calendarId ? "border-[var(--accent)]" : "border-[var(--border)] text-[var(--muted)]")}>
                <span className="mr-1 inline-block size-2 rounded-full" style={{ background: calendar.color ?? "#64748b" }} />{calendar.name}{calendar.is_shared ? " · sdíl." : ""}
              </button>
            ))}
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            <label className="grid gap-1 font-medium">Datum<Input type="date" value={date} onChange={(event) => { setDate(event.target.value); setShowDateError(false); }} /></label>
            <label className="grid gap-1 font-medium">Čas<Input type="time" value={time} onChange={(event) => setTime(event.target.value)} /></label>
          </div>
          <div className="flex flex-wrap gap-1.5">
            <Button type="button" size="sm" variant="secondary" onClick={() => quickDate("today")}>Dnes</Button>
            <Button type="button" size="sm" variant="secondary" onClick={() => quickDate("tomorrow")}>Zítra</Button>
            <Button type="button" size="sm" variant="secondary" onClick={() => quickDate("monday")}>Pondělí</Button>
          </div>
          {showDateError ? <p className="text-xs font-medium text-[var(--danger)]">Bez data nejde požadavek odeslat.</p> : null}
          <fieldset className="grid gap-1">
            <legend className="font-medium">Délka</legend>
            <div className="grid grid-cols-4 gap-1.5">
              {durations.map((value) => <button key={value} type="button" onClick={() => setDuration(value)} className={cn("rounded-[var(--radius-sm)] border px-2 py-1", duration === value ? "border-[var(--accent)] bg-[var(--accent)]/10" : "border-[var(--border)]")}>{value}</button>)}
            </div>
          </fieldset>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={reminder} onChange={(event) => setReminder(event.target.checked)} />Upozornění 15 minut předem</label>
          <Button
            type="button"
            disabled={pending || !selectedCalendar}
            onClick={() => {
              if (!date) { setShowDateError(true); return; }
              if (selectedCalendar) void onSubmit({ calendar: selectedCalendar, date, time, duration, reminder });
            }}
          >{pending ? "Odesílám…" : "Zadat požadavek"}</Button>
        </>
      )}
    </div>
  );
}

export function TaskCalendarStatus({ task }: { task: Task }) {
  const retry = useRetryCalendarRequest();
  const disconnect = useDisconnectCalendarRequest();
  const request = task.calendar_request;
  if (!request || request.status === "cancelled") return null;
  const pendingLong = ["pending", "claimed"].includes(request.status) && Date.now() - new Date(request.created_at).getTime() > 10 * 60 * 1000;
  if (request.status === "done") {
    return (
      <Badge className="border-[var(--success)] px-2 py-0.5 text-[var(--success)]">
        <span className="mr-1 size-2 rounded-full" style={{ background: request.calendar_color ?? "#22c55e" }} />
        v kalendáři {request.calendar_name ?? request.calendar_external_id}
        {request.external_event_link ? <a className="ml-1 underline" href={request.external_event_link} target="_blank" rel="noreferrer"><ExternalLink size={11} /></a> : null}
        <button type="button" className="ml-1" title="Odpojit bez mazání události" onClick={(event) => { event.stopPropagation(); void disconnect.mutateAsync(request.id); }}><Unlink size={11} /></button>
      </Badge>
    );
  }
  if (request.status === "failed") {
    return (
      <Badge className="border-[var(--danger)] px-2 py-0.5 text-[var(--danger)]">
        nepovedlo se: {request.error_message ?? "bez detailu"}
        <button type="button" className="ml-1 underline" onClick={(event) => { event.stopPropagation(); void retry.mutateAsync(request.id); }}><RefreshCcw size={11} /></button>
      </Badge>
    );
  }
  return (
    <Badge className={cn("px-2 py-0.5", pendingLong ? "border-[var(--warning)] text-[var(--warning)]" : "border-[var(--accent)] text-[var(--accent)]")}>
      čeká na zápis {formatTime(request.created_at)}
      {pendingLong ? <Link className="ml-1 underline" href="/agent">agent?</Link> : null}
    </Badge>
  );
}

function todayIso() {
  return toDateInput(new Date());
}

function toDateInput(date: Date) {
  return date.toISOString().slice(0, 10);
}

function toTimeInput(value: string) {
  return value.slice(0, 5);
}

function toLocalInput(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `${year}-${month}-${day}T${hours}:${minutes}:00`;
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat("cs-CZ", { timeStyle: "short", dateStyle: "short" }).format(new Date(value));
}
