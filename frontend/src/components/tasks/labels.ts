import type { TaskPriority, TaskStatus, TaskView } from "@/lib/api/types";

export const statusLabels: Record<TaskStatus, string> = {
  inbox: "Inbox",
  todo: "Čeká",
  doing: "Rozpracováno",
  done: "Hotovo",
  cancelled: "Zrušeno",
};

export const priorityLabels: Record<TaskPriority, string> = {
  none: "Bez priority",
  low: "Nízká",
  medium: "Střední",
  high: "Vysoká",
};

export const viewLabels: Record<TaskView, string> = {
  today: "Dnes",
  this_week: "Tento týden",
  overdue: "Po termínu",
  inbox: "Inbox",
  tomorrow: "Zítra",
};
