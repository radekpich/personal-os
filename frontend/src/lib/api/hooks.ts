"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";
import type { Task, TaskFilters, TaskStatus, TaskUpdate, VisionCreate, VisionUpdate } from "./types";

export const queryKeys = {
  me: ["me"] as const,
  categories: ["categories"] as const,
  contexts: ["contexts"] as const,
  tags: ["tags"] as const,
  tasks: (filters: TaskFilters = {}) => ["tasks", filters] as const,
  task: (id: string | null) => ["task", id] as const,
  visions: ["visions"] as const,
  visionTree: ["visions", "tree"] as const,
  visionProgress: (id: string | null) => ["visions", id, "progress"] as const,
  stagnatingVisions: (days: number) => ["visions", "stagnating", days] as const,
};

export function useMe() {
  return useQuery({ queryKey: queryKeys.me, queryFn: api.me });
}

export function useTaxonomy() {
  const categories = useQuery({ queryKey: queryKeys.categories, queryFn: api.categories });
  const contexts = useQuery({ queryKey: queryKeys.contexts, queryFn: api.contexts });
  const tags = useQuery({ queryKey: queryKeys.tags, queryFn: api.tags });
  return { categories, contexts, tags };
}

export function useTasks(filters: TaskFilters = {}) {
  return useQuery({ queryKey: queryKeys.tasks(filters), queryFn: () => api.tasks(filters) });
}

export function useQuickTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.quickTask,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tasks"] }),
  });
}

export function useCreateTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.createTask,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tasks"] }),
  });
}

export function useUpdateTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: TaskUpdate }) => api.updateTask(id, payload),
    onSuccess: (task) => {
      queryClient.setQueryData(queryKeys.task(task.id), task);
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      queryClient.invalidateQueries({ queryKey: ["visions"] });
    },
  });
}

export function useToggleTaskDone() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ task, status }: { task: Task; status: TaskStatus }) =>
      api.updateTask(task.id, {
        status,
        completed_at: status === "done" ? new Date().toISOString() : null,
      }),
    onMutate: async ({ task, status }) => {
      await queryClient.cancelQueries({ queryKey: ["tasks"] });
      const snapshots = queryClient.getQueriesData<{ items: Task[]; total: number }>({ queryKey: ["tasks"] });
      for (const [key, value] of snapshots) {
        if (!value) continue;
        queryClient.setQueryData(key, {
          ...value,
          items: value.items.map((item) => (item.id === task.id ? { ...item, status, completed_at: status === "done" ? new Date().toISOString() : null } : item)),
        });
      }
      return { snapshots };
    },
    onError: (_error, _variables, context) => {
      for (const [key, value] of context?.snapshots ?? []) queryClient.setQueryData(key, value);
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["tasks"] }),
  });
}

export function useDeleteTask() {
  const queryClient = useQueryClient();
  return useMutation({ mutationFn: api.deleteTask, onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tasks"] }) });
}

export function useVisions() {
  return useQuery({ queryKey: queryKeys.visions, queryFn: api.visions });
}

export function useVisionTree() {
  return useQuery({ queryKey: queryKeys.visionTree, queryFn: api.visionTree });
}

export function useVisionProgress(id: string | null) {
  return useQuery({
    queryKey: queryKeys.visionProgress(id),
    queryFn: () => api.visionProgress(id!),
    enabled: Boolean(id),
  });
}

export function useStagnatingVisions(days = 14) {
  return useQuery({ queryKey: queryKeys.stagnatingVisions(days), queryFn: () => api.stagnatingVisions(days) });
}

function invalidateVisions(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: ["visions"] });
  queryClient.invalidateQueries({ queryKey: ["tasks"] });
}

export function useCreateVision() {
  const queryClient = useQueryClient();
  return useMutation({ mutationFn: (payload: VisionCreate) => api.createVision(payload), onSuccess: () => invalidateVisions(queryClient) });
}

export function useUpdateVision() {
  const queryClient = useQueryClient();
  return useMutation({ mutationFn: ({ id, payload }: { id: string; payload: VisionUpdate }) => api.updateVision(id, payload), onSuccess: () => invalidateVisions(queryClient) });
}

export function useDeleteVision() {
  const queryClient = useQueryClient();
  return useMutation({ mutationFn: api.deleteVision, onSuccess: () => invalidateVisions(queryClient) });
}
