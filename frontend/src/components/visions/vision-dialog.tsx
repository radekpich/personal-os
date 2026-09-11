"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { zodResolver } from "@hookform/resolvers/zod";
import { X } from "lucide-react";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import type { Vision, VisionHorizon } from "@/lib/api/types";
import { useCreateVision, useUpdateVision } from "@/lib/api/hooks";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";

const horizonLabels: Record<VisionHorizon, string> = {
  life: "Život",
  "5y": "5 let",
  "1y": "1 rok",
  quarter: "Kvartál",
};

const schema = z.object({
  title: z.string().min(1),
  description: z.string().nullable(),
  horizon: z.enum(["life", "5y", "1y", "quarter"]),
  target_date: z.string().nullable(),
});

type Values = z.infer<typeof schema>;

const emptyValues: Values = { title: "", description: "", horizon: "1y", target_date: null };

type Props = {
  open: boolean;
  vision?: Vision | null;
  onClose: () => void;
};

export function VisionDialog({ open, vision = null, onClose }: Props) {
  const create = useCreateVision();
  const update = useUpdateVision();
  const mode = vision ? "edit" : "create";
  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: emptyValues });

  useEffect(() => {
    if (!open) return;
    if (vision) {
      form.reset({
        title: vision.title,
        description: vision.description ?? "",
        horizon: vision.horizon,
        target_date: vision.target_date,
      });
    } else {
      form.reset(emptyValues);
    }
  }, [open, vision, form]);

  async function submit(values: Values) {
    const payload = {
      ...values,
      description: values.description || null,
      target_date: values.target_date || null,
    };
    if (vision) {
      await update.mutateAsync({ id: vision.id, payload });
    } else {
      await create.mutateAsync(payload);
    }
    onClose();
  }

  const pending = create.isPending || update.isPending;

  return (
    <Dialog.Root open={open} onOpenChange={(next) => { if (!next) onClose(); }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/30" />
        <Dialog.Content className="fixed inset-x-0 bottom-0 z-50 flex h-[96dvh] max-h-[96dvh] flex-col overflow-hidden rounded-t-[var(--radius-xl)] border border-[var(--border)] bg-[var(--surface)] shadow-2xl sm:inset-y-0 sm:left-auto sm:right-0 sm:h-dvh sm:w-full sm:max-w-xl sm:rounded-none sm:border-l">
          <div className="flex items-start justify-between gap-4 border-b border-[var(--border)] p-4 sm:p-6">
            <div>
              <Dialog.Title className="text-lg font-semibold">{mode === "edit" ? "Upravit vizi" : "Nová vize"}</Dialog.Title>
              <Dialog.Description className="text-sm text-[var(--muted)]">Sny → cíle → milníky → konkrétní kroky.</Dialog.Description>
            </div>
            <Dialog.Close asChild><Button variant="ghost" size="sm" aria-label="Zavřít"><X size={18} /></Button></Dialog.Close>
          </div>
          <form className="flex min-h-0 flex-1 flex-col" onSubmit={form.handleSubmit(submit)}>
            <div className="grid min-h-0 flex-1 gap-4 overflow-y-auto p-4 pb-24 sm:p-6">
              <label className="grid gap-1 text-sm font-medium">Název<Input {...form.register("title")} autoFocus /></label>
              <label className="grid gap-1 text-sm font-medium">Popis Markdown<Textarea rows={5} {...form.register("description")} /></label>
              <div className="grid gap-3 sm:grid-cols-2">
                <Select label="Horizont" {...form.register("horizon")}>
                  {Object.entries(horizonLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </Select>
                <label className="grid gap-1 text-sm font-medium">Cílové datum<Input type="date" {...form.register("target_date")} /></label>
              </div>
            </div>
            <div className="relative z-10 flex shrink-0 justify-end gap-2 border-t border-[var(--border)] bg-[var(--surface)] p-4 pb-[calc(3.5rem+env(safe-area-inset-bottom))] sm:p-6">
              <Button type="button" variant="ghost" onClick={onClose}>Zrušit</Button>
              <Button disabled={pending}>{mode === "edit" ? "Uložit vizi" : "Založit vizi"}</Button>
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
