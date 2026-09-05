"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { api } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const loginSchema = z.object({ email: z.string().email("Zadej platný email"), password: z.string().min(1, "Zadej heslo") });
type LoginValues = z.infer<typeof loginSchema>;

export function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const queryClient = useQueryClient();
  const form = useForm<LoginValues>({ resolver: zodResolver(loginSchema), defaultValues: { email: "", password: "" } });
  const login = useMutation({
    mutationFn: api.login,
    onSuccess: (user) => {
      queryClient.setQueryData(["me"], user);
      router.replace(params.get("next") ?? "/dashboard");
    },
  });

  return (
    <form method="post" className="panel mx-auto flex w-full max-w-md flex-col gap-4 p-6" onSubmit={form.handleSubmit((values) => login.mutate(values))}>
      <div>
        <p className="text-sm text-[var(--muted)]">Personal OS</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">Přihlášení</h1>
      </div>
      <label className="grid gap-1 text-sm font-medium">
        Email
        <Input autoComplete="email" type="email" {...form.register("email")} />
        {form.formState.errors.email ? <span className="text-xs text-[var(--danger)]">{form.formState.errors.email.message}</span> : null}
      </label>
      <label className="grid gap-1 text-sm font-medium">
        Heslo
        <Input autoComplete="current-password" type="password" {...form.register("password")} />
        {form.formState.errors.password ? <span className="text-xs text-[var(--danger)]">{form.formState.errors.password.message}</span> : null}
      </label>
      {login.isError ? <p className="rounded-[var(--radius-sm)] bg-[var(--danger-soft)] p-3 text-sm text-[var(--danger)]">Přihlášení se nepovedlo. Zkontroluj email a heslo.</p> : null}
      <Button type="submit" disabled={login.isPending}>{login.isPending ? "Přihlašuji…" : "Přihlásit"}</Button>
    </form>
  );
}
