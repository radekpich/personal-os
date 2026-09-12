"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { zodResolver } from "@hookform/resolvers/zod";
import { X } from "lucide-react";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { useCreateChallenge, useTaxonomy, useUpdateChallenge, useVisions } from "@/lib/api/hooks";
import type { Challenge, ChallengeType } from "@/lib/api/types";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { RecurrenceBuilder } from "@/components/recurrence/recurrence-builder";

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
  schedule_rrule: z.string().min(1),
  is_active: z.preprocess((value) => value === true || value === "true", z.boolean()),
  color: z.string().regex(/^#[0-9a-fA-F]{6}$/),
  icon: z.string().min(1),
});

type FormInput = z.input<typeof schema>;
type Values = z.output<typeof schema>;

const emptyValues: FormInput = {
  title: "",
  description: "",
  type: "daily_action",
  category_id: null,
  vision_id: null,
  target_days: null,
  allowed_gap_days: 0,
  schedule_rrule: "FREQ=DAILY",
  is_active: true,
  color: "#22c55e",
  icon: "activity",
};

type Props = {
  open: boolean;
  challenge?: Challenge | null;
  onClose: () => void;
};

export function ChallengeDialog({ open, challenge = null, onClose }: Props) {
  const { categories } = useTaxonomy();
  const visions = useVisions();
  const create = useCreateChallenge();
  const update = useUpdateChallenge();
  const mode = challenge ? "edit" : "create";
  const form = useForm<FormInput, unknown, Values>({ resolver: zodResolver(schema), defaultValues: emptyValues });
  const scheduleRule = form.watch("schedule_rrule");

  useEffect(() => {
    if (!open) return;
    if (challenge) {
      form.reset({
        title: challenge.title,
        description: challenge.description ?? "",
        type: challenge.type,
        category_id: challenge.category_id,
        vision_id: challenge.vision_id,
        target_days: challenge.target_days,
        allowed_gap_days: challenge.allowed_gap_days,
        schedule_rrule: challenge.schedule_rrule,
        is_active: challenge.is_active,
        color: challenge.color,
        icon: challenge.icon,
      });
    } else {
      form.reset(emptyValues);
    }
  }, [open, challenge, form]);

  async function submit(values: Values) {
    const description = values.description || null;
    const category_id = values.category_id || null;
    const vision_id = values.vision_id || null;
    const target_days = values.target_days || null;
    if (challenge) {
      // type cannot be changed after creation (backend ChallengeUpdate has no `type` field)
      await update.mutateAsync({
        id: challenge.id,
        payload: {
          title: values.title,
          description,
          category_id,
          vision_id,
          target_days,
          allowed_gap_days: values.allowed_gap_days,
          schedule_rrule: values.schedule_rrule,
          is_active: values.is_active,
          color: values.color,
          icon: values.icon,
        },
      });
    } else {
      await create.mutateAsync({
        ...values,
        description,
        category_id,
        vision_id,
        target_days,
        is_active: values.is_active,
      });
    }
    onClose();
  }

  const pending = create.isPending || update.isPending;

  return (
    <Dialog.Root open={open} onOpenChange={(next) => { if (!next) onClose(); }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/30" />
        <Dialog.Content className="fixed inset-x-0 bottom-0 z-[51] flex h-[96dvh] max-h-[96dvh] flex-col overflow-hidden rounded-t-[var(--radius-xl)] border border-[var(--border)] bg-[var(--surface)] shadow-2xl sm:inset-y-0 sm:left-auto sm:right-0 sm:h-dvh sm:w-full sm:max-w-xl sm:rounded-none sm:border-l">
          <div className="flex items-start justify-between gap-4 border-b border-[var(--border)] p-4 sm:p-6">
            <div>
              <Dialog.Title className="text-lg font-semibold">{mode === "edit" ? "Upravit výzvu" : "Nová výzva"}</Dialog.Title>
              <Dialog.Description className="text-sm text-[var(--muted)]">
                Denní akce se počítá z reálných zápisů; abstinence běží od startu a zapisuje jen relaps. Limit zpětného zápisu je 7 dní.
              </Dialog.Description>
            </div>
            <Dialog.Close asChild><Button variant="ghost" size="sm" aria-label="Zavřít"><X size={18} /></Button></Dialog.Close>
          </div>
          <form className="flex min-h-0 flex-1 flex-col" onSubmit={form.handleSubmit(submit)}>
            <div className="grid min-h-0 flex-1 gap-4 overflow-y-auto p-4 pb-24 sm:p-6">
              <label className="grid gap-1 text-sm font-medium">Název<Input {...form.register("title")} placeholder="Švihadlo" autoFocus /></label>
              <label className="grid gap-1 text-sm font-medium">Popis<Textarea rows={3} {...form.register("description")} /></label>
              <div className="grid gap-3 sm:grid-cols-2">
                {mode === "edit" ? (
                  <label className="grid gap-1 text-sm font-medium">Typ<Input value={challengeTypeLabels[challenge!.type]} disabled /></label>
                ) : (
                  <Select label="Typ" {...form.register("type")}>
                    <option value="daily_action">Denní akce</option>
                    <option value="abstinence">Abstinence</option>
                  </Select>
                )}
                <label className="grid gap-1 text-sm font-medium">Cíl dní<Input type="number" min={1} {...form.register("target_days")} /></label>
                <label className="grid gap-1 text-sm font-medium">
                  Povolené vynechání
                  <Input type="number" min={0} max={30} {...form.register("allowed_gap_days")} />
                  <span className="text-xs font-normal text-[var(--muted)]">Kolik dní z rozvrhu smím vynechat, aniž se šňůra přeruší.</span>
                </label>
                <label className="grid gap-1 text-sm font-medium">Barva<Input type="color" {...form.register("color")} /></label>
                <Select label="Stav" {...form.register("is_active")}>
                  <option value="true">Aktivní</option>
                  <option value="false">Pozastavená</option>
                </Select>
              </div>
              <RecurrenceBuilder
                label="Rozvrh výzvy"
                helperText="Výchozí je denně. Můžeš nastavit 3× týdně nebo konkrétní dny stejně jako u opakovaných úkolů."
                value={scheduleRule}
                onChange={(next) => form.setValue("schedule_rrule", next ?? "FREQ=DAILY", { shouldDirty: true, shouldValidate: true })}
              />
              <Select label="Kategorie" {...form.register("category_id")}>
                <option value="">Bez kategorie</option>
                {categories.data?.items.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
              </Select>
              <Select label="Vize" {...form.register("vision_id")}>
                <option value="">Bez vize</option>
                {visions.data?.items.map((vision) => <option key={vision.id} value={vision.id}>{vision.title}</option>)}
              </Select>
              <input type="hidden" {...form.register("icon")} />
            </div>
            <div className="relative z-10 flex shrink-0 justify-end gap-2 border-t border-[var(--border)] bg-[var(--surface)] p-4 pb-[calc(3.5rem+env(safe-area-inset-bottom))] sm:p-6">
              <Button type="button" variant="ghost" onClick={onClose}>Zrušit</Button>
              <Button disabled={pending}>{mode === "edit" ? "Uložit výzvu" : "Založit výzvu"}</Button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function Select({ label, children, ...props }: React.SelectHTMLAttributes<HTMLSelectElement> & { label: string }) {
  return <label className="grid gap-1 text-sm font-medium">{label}<select className="focus-ring min-h-11 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-3 text-base" {...props}>{children}</select></label>;
}
