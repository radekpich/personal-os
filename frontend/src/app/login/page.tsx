import { Suspense } from "react";
import { LoginForm } from "@/components/login-form";

export default function LoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-10">
      <Suspense fallback={<div>Načítám…</div>}>
        <LoginForm />
      </Suspense>
    </main>
  );
}
