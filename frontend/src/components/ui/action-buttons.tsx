import { CheckCircle2, Circle, Pencil, RotateCcw, Trash2 } from "lucide-react";
import type { ButtonHTMLAttributes } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type ActionButtonProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children"> & {
  label: string;
  icon: "edit" | "delete" | "process" | "restore";
  showLabel?: boolean;
  danger?: boolean;
};

const icons = {
  edit: Pencil,
  process: Pencil,
  delete: Trash2,
  restore: RotateCcw,
};

export function ActionButton({ label, icon, showLabel = false, danger = false, className, ...props }: ActionButtonProps) {
  const Icon = icons[icon];
  return (
    <Button
      type="button"
      variant={danger ? "danger" : "ghost"}
      size="sm"
      aria-label={label}
      title={label}
      className={cn(!showLabel && "size-9 px-0", className)}
      {...props}
    >
      <Icon size={15} />
      {showLabel ? label : <span className="sr-only">{label}</span>}
    </Button>
  );
}

type CompleteToggleButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  checked: boolean;
  checkedLabel: string;
  uncheckedLabel: string;
  size?: "sm" | "md" | "lg";
};

export function CompleteToggleButton({ checked, checkedLabel, uncheckedLabel, size = "md", className, ...props }: CompleteToggleButtonProps) {
  const Icon = checked ? CheckCircle2 : Circle;
  const sizeClass = size === "lg" ? "size-14 rounded-2xl" : size === "sm" ? "size-9 rounded-full" : "size-10 rounded-full";
  const iconSize = size === "lg" ? 30 : size === "sm" ? 18 : 22;
  const label = checked ? checkedLabel : uncheckedLabel;
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      className={cn(
        "focus-ring grid shrink-0 place-items-center border-2 transition disabled:pointer-events-none disabled:opacity-50",
        sizeClass,
        checked ? "border-[var(--success)] bg-[var(--success)] text-white" : "border-[var(--border-strong)] bg-[var(--surface)] text-[var(--muted)] hover:bg-[var(--surface-muted)]",
        className,
      )}
      {...props}
    >
      <Icon size={iconSize} />
    </button>
  );
}
