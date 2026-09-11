import type { ReactNode } from "react";

export function FilterBar({ children, hint }: { children: ReactNode; hint?: string }) {
  return (
    <div className="panel flex flex-wrap gap-3 p-3">
      {children}
      {hint ? <p className="text-xs text-[var(--muted)]">{hint}</p> : null}
    </div>
  );
}

export function FilterSelect({
  value,
  onChange,
  options,
  "aria-label": ariaLabel,
}: {
  value: string;
  onChange: (value: string) => void;
  options: Array<{ value: string; label: string }>;
  "aria-label"?: string;
}) {
  return (
    <select
      aria-label={ariaLabel}
      className="focus-ring min-h-10 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-3"
      value={value}
      onChange={(event) => onChange(event.target.value)}
    >
      {options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
    </select>
  );
}
