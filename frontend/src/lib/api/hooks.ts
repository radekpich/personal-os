"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";
import type {
  AgentActionFilters,
  ChallengeCreate,
  ChallengeUpdate,
  CheckInCreate,
  Note,
  NoteCreate,
  NoteFilters,
  NoteUpdate,
  Tag,
  Task,
  TaskFilters,
  TaskStatus,
  TaskUpdate,
  VisionCreate,
  VisionUpdate,
} from "./types";

export const queryKeys = {
  me: ["me"] as const,
  agentActions: (filters: AgentActionFilters = {}) => ["agent-actions", filters] as const,
  agentOverview: ["agent-overview"] as const,
  agentJobs: ["agent-jobs"] as const,
  agentIntegrations: ["agent-integrations"] as const,
  agentWatches: ["agent-watches"] as const,
  agentChannels: ["agent-channels"] as const,
  agentRuns: (filters: { job_id?: string; trigger?: string; status?: string; q?: string; page?: number; page_size?: number } = {}) => ["agent-runs", filters] as const,
  agentConfigChanges: (filters: { acknowledged?: boolean } = {}) => ["agent-config-changes", filters] as const,
  agentKeys: ["agent-keys"] as const,
  categories: ["categories"] as const,
  contexts: ["contexts"] as const,
  tags: ["tags"] as const,
  challenges: ["challenges"] as const,
  challenge: (id: string | null) => ["challenges", id] as const,
  challengeStats: (id: string | null) => ["challenges", id, "stats"] as const,
  challengeHeatmap: (id: string | null, year: number) => ["challenges", id, "heatmap", year] as const,
  tasks: (filters: TaskFilters = {}) => ["tasks", filters] as const,
  task: (id: string | null) => ["task", id] as const,
  taskAttachments: (id: string | null) => ["task", id, "attachments"] as const,
  notes: (filters: NoteFilters = {}) => ["notes", filters] as const,
  note: (id: string | null) => ["note", id] as const,
  noteAttachments: (id: string | null) => ["note", id, "attachments"] as const,
  visions: ["visions"] as const,
  visionTree: ["visions", "tree"] as const,
  visionProgress: (id: string | null) => ["visions", id, "progress"] as const,
  stagnatingVisions: (days: number) => ["visions", "stagnating", days] as const,
};

export function useMe() {
  return useQuery({ queryKey: queryKeys.me, queryFn: api.me });
}

export function useAgentActions(filters: AgentActionFilters = {}) {
  return useQuery({
    queryKey: queryKeys.agentActions(filters),
    queryFn: () => api.agentActions(filters),
    refetchInterval: 30_000,
    refetchOnWindowFocus: true,
  });
}

export function useAgentOverview() {
  return useQuery({ queryKey: queryKeys.agentOverview, queryFn: api.agentOverview, refetchInterval: 30_000 });
}

export function useAgentJobs() {
  return useQuery({ queryKey: queryKeys.agentJobs, queryFn: api.agentJobs, refetchInterval: 30_000 });
}

export function useAgentIntegrations() {
  return useQuery({ queryKey: queryKeys.agentIntegrations, queryFn: api.agentIntegrations, refetchInterval: 30_000 });
}

export function useAgentWatches() {
  return useQuery({ queryKey: queryKeys.agentWatches, queryFn: api.agentWatches, refetchInterval: 30_000 });
}

export function useAgentChannels() {
  return useQuery({ queryKey: queryKeys.agentChannels, queryFn: api.agentChannels, refetchInterval: 30_000 });
}

export function useAgentRuns(filters: { job_id?: string; trigger?: string; status?: string; q?: string; page?: number; page_size?: number } = {}) {
  return useQuery({ queryKey: queryKeys.agentRuns(filters), queryFn: () => api.agentRuns(filters), refetchInterval: 30_000 });
}

export function useAgentConfigChanges(filters: { acknowledged?: boolean } = {}) {
  return useQuery({ queryKey: queryKeys.agentConfigChanges(filters), queryFn: () => api.agentConfigChanges(filters), refetchInterval: 30_000 });
}

export function useAgentKeys() {
  return useQuery({ queryKey: queryKeys.agentKeys, queryFn: api.agentKeys, refetchInterval: 30_000 });
}

export function useAcknowledgeAgentConfigChange() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.acknowledgeAgentConfigChange,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agent-config-changes"] });
      queryClient.invalidateQueries({ queryKey: queryKeys.agentOverview });
    },
  });
}

export function useRevokeAllAgentKeys() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.revokeAllAgentKeys,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["agent-keys"] }),
  });
}

export function useRevertAgentAction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.revertAgentAction,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agent-actions"] });
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      queryClient.invalidateQueries({ queryKey: ["notes"] });
    },
  });
}

export function useRevertAgentActionBatch() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.revertAgentActionBatch,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agent-actions"] });
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      queryClient.invalidateQueries({ queryKey: ["notes"] });
    },
  });
}

export function useTaxonomy() {
  const categories = useQuery({ queryKey: queryKeys.categories, queryFn: api.categories });
  const contexts = useQuery({ queryKey: queryKeys.contexts, queryFn: api.contexts });
  const tags = useQuery({ queryKey: queryKeys.tags, queryFn: api.tags });
  return { categories, contexts, tags };
}

export function useCreateTag() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { name: string }) => api.createTag(payload),
    onSuccess: (tag: Tag) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.tags });
      queryClient.setQueryData(queryKeys.tags, (current: { items: Tag[] } | undefined) =>
        current ? { ...current, items: [...current.items.filter((item) => item.id !== tag.id), tag] } : current,
      );
    },
  });
}

export function useTasks(filters: TaskFilters = {}) {
  return useQuery({
    queryKey: queryKeys.tasks(filters),
    queryFn: () => api.tasks(filters),
    refetchInterval: 30_000,
    refetchOnWindowFocus: true,
  });
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
    mutationFn: ({ task, payload }: { task: Task; payload: TaskUpdate }) =>
      api.updateTask(task.id, payload, task.version),
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
      api.updateTask(
        task.id,
        {
          status,
          completed_at: status === "done" ? new Date().toISOString() : null,
        },
        task.version,
      ),
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
  return useMutation({
    mutationFn: (task: Task) => api.deleteTask(task.id, task.version),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tasks"] }),
  });
}

function invalidateTaskAttachments(queryClient: ReturnType<typeof useQueryClient>, taskId: string) {
  queryClient.invalidateQueries({ queryKey: queryKeys.taskAttachments(taskId) });
  queryClient.invalidateQueries({ queryKey: queryKeys.task(taskId) });
}

export function useTaskAttachments(taskId: string | null) {
  return useQuery({
    queryKey: queryKeys.taskAttachments(taskId),
    queryFn: () => api.taskAttachments(taskId!),
    enabled: Boolean(taskId),
  });
}

export function useUploadTaskAttachment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ taskId, file, caption }: { taskId: string; file: File; caption?: string | null }) => {
      const attachment = await api.uploadAttachment(file, caption);
      await api.attachToTask(taskId, attachment.id);
      return attachment;
    },
    onSuccess: (_attachment, variables) => invalidateTaskAttachments(queryClient, variables.taskId),
  });
}

export function useUpdateAttachment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: { caption?: string | null } }) => api.updateAttachment(id, payload),
    onSuccess: (attachment) => {
      queryClient.invalidateQueries({ queryKey: ["task"] });
      queryClient.setQueryData(["attachment", attachment.id], attachment);
    },
  });
}

export function useDeleteTaskAttachment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ attachmentId }: { taskId: string; attachmentId: string }) => api.deleteAttachment(attachmentId),
    onSuccess: (_result, variables) => invalidateTaskAttachments(queryClient, variables.taskId),
  });
}

export function useUnlinkTaskAttachment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, attachmentId }: { taskId: string; attachmentId: string }) => api.unlinkTaskAttachment(taskId, attachmentId),
    onSuccess: (_result, variables) => invalidateTaskAttachments(queryClient, variables.taskId),
  });
}

export function useStorageUsage() {
  return useQuery({ queryKey: ["storage", "usage"], queryFn: api.storageUsage });
}

export function useNotes(filters: NoteFilters = {}) {
  return useQuery({
    queryKey: queryKeys.notes(filters),
    queryFn: () => api.notes(filters),
    refetchInterval: 30_000,
    refetchOnWindowFocus: true,
  });
}

export function useNote(id: string | null) {
  return useQuery({ queryKey: queryKeys.note(id), queryFn: () => api.note(id!), enabled: Boolean(id) });
}

function invalidateNotes(queryClient: ReturnType<typeof useQueryClient>, noteId?: string) {
  queryClient.invalidateQueries({ queryKey: ["notes"] });
  if (noteId) {
    queryClient.invalidateQueries({ queryKey: queryKeys.note(noteId) });
    queryClient.invalidateQueries({ queryKey: queryKeys.noteAttachments(noteId) });
  }
}

export function useCreateNote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: NoteCreate) => api.createNote(payload),
    onSuccess: (note) => invalidateNotes(queryClient, note.id),
  });
}

export function useUpdateNote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ note, payload }: { note: Note; payload: NoteUpdate }) =>
      api.updateNote(note.id, payload, note.version),
    onSuccess: (note) => {
      queryClient.setQueryData(queryKeys.note(note.id), note);
      invalidateNotes(queryClient, note.id);
    },
  });
}

export function useDeleteNote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (note: Note) => api.deleteNote(note.id, note.version),
    onSuccess: () => invalidateNotes(queryClient),
  });
}

export function useNoteAttachments(noteId: string | null) {
  return useQuery({
    queryKey: queryKeys.noteAttachments(noteId),
    queryFn: () => api.noteAttachments(noteId!),
    enabled: Boolean(noteId),
  });
}

export function useUploadNoteAttachment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ noteId, file, caption }: { noteId: string; file: File; caption?: string | null }) => {
      const attachment = await api.uploadAttachment(file, caption);
      await api.attachToNote(noteId, attachment.id);
      return attachment;
    },
    onSuccess: (_attachment, variables) => invalidateNotes(queryClient, variables.noteId),
  });
}

export function useDeleteNoteAttachment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ attachmentId }: { noteId: string; attachmentId: string }) => api.deleteAttachment(attachmentId),
    onSuccess: (_result, variables) => invalidateNotes(queryClient, variables.noteId),
  });
}

export function useUnlinkNoteAttachment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ noteId, attachmentId }: { noteId: string; attachmentId: string }) => api.unlinkNoteAttachment(noteId, attachmentId),
    onSuccess: (_result, variables) => invalidateNotes(queryClient, variables.noteId),
  });
}

export function useChallenges() {
  return useQuery({ queryKey: queryKeys.challenges, queryFn: api.challenges });
}

export function useChallenge(id: string | null) {
  return useQuery({ queryKey: queryKeys.challenge(id), queryFn: () => api.challenge(id!), enabled: Boolean(id) });
}

export function useChallengeStats(id: string | null) {
  return useQuery({
    queryKey: queryKeys.challengeStats(id),
    queryFn: () => api.challengeStats(id!),
    enabled: Boolean(id),
  });
}

export function useChallengeHeatmap(id: string | null, year: number) {
  return useQuery({
    queryKey: queryKeys.challengeHeatmap(id, year),
    queryFn: () => api.challengeHeatmap(id!, year),
    enabled: Boolean(id),
  });
}

function invalidateChallenges(queryClient: ReturnType<typeof useQueryClient>, id?: string) {
  queryClient.invalidateQueries({ queryKey: ["challenges"] });
  if (id) {
    queryClient.invalidateQueries({ queryKey: queryKeys.challenge(id) });
    queryClient.invalidateQueries({ queryKey: queryKeys.challengeStats(id) });
  }
}

export function useCreateChallenge() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ChallengeCreate) => api.createChallenge(payload),
    onSuccess: () => invalidateChallenges(queryClient),
  });
}

export function useUpdateChallenge() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: ChallengeUpdate }) => api.updateChallenge(id, payload),
    onSuccess: (challenge) => invalidateChallenges(queryClient, challenge.id),
  });
}

export function useDeleteChallenge() {
  const queryClient = useQueryClient();
  return useMutation({ mutationFn: api.deleteChallenge, onSuccess: () => invalidateChallenges(queryClient) });
}

export function useCheckInChallenge() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: CheckInCreate }) => api.checkInChallenge(id, payload),
    onSuccess: (_result, variables) => {
      invalidateChallenges(queryClient, variables.id);
      queryClient.invalidateQueries({ queryKey: ["challenges", variables.id, "heatmap"] });
    },
  });
}

export function useCreateChallengePause() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string;
      payload: { start_date: string; end_date?: string | null; note?: string | null };
    }) => api.createChallengePause(id, payload),
    onSuccess: (_result, variables) => {
      invalidateChallenges(queryClient, variables.id);
      queryClient.invalidateQueries({ queryKey: ["challenges", variables.id, "heatmap"] });
    },
  });
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
