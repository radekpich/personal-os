export type UUID = string;

export type User = {
  id: UUID;
  email: string;
  display_name: string;
  timezone: string;
  calendar_token: string;
  is_active: boolean;
  created_at: string;
};

export type TaskStatus = "inbox" | "todo" | "in_progress" | "blocked" | "done" | "cancelled";
export type TaskPriority = "none" | "low" | "medium" | "high";
export type TaskSource = "web" | "quick_capture" | "telegram" | "agent" | "calendar" | "email" | "journal";
export type TaskView = "today" | "this_week" | "overdue" | "inbox" | "tomorrow" | "unscheduled";
export type RecurrenceMode = "fixed" | "after_completion";
export type VisionHorizon = "life" | "5y" | "1y" | "quarter";
export type VisionStatus = "active" | "paused" | "achieved" | "abandoned";
export type ChallengeType = "daily_action" | "abstinence";
export type AttachmentProcessingStatus = "pending" | "ready" | "failed";

export type Attachment = {
  id: UUID;
  owner_id: UUID;
  storage_path: string;
  thumbnail_path: string | null;
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  width: number | null;
  height: number | null;
  checksum_sha256: string;
  captured_at: string | null;
  gps_lat: number | null;
  gps_lon: number | null;
  caption: string | null;
  processing_status: AttachmentProcessingStatus;
  created_at: string;
  deleted_at: string | null;
};

export type AttachmentUpdate = {
  caption?: string | null;
};

export type TaskAttachment = {
  task_id: UUID;
  attachment_id: UUID;
  position: number;
};

export type NoteKind = "note" | "diary" | "meeting" | "idea";

export type MutationOrigin = "user" | "agent";

export type AgentActionType =
  | "create_task"
  | "update_task"
  | "complete_task"
  | "add_note"
  | "update_note"
  | "checkin"
  | "attach_file"
  | "schedule_task"
  | "revert_action"
  | "revert_batch"
  | string;

export type AgentAction = {
  id: UUID;
  owner_id: UUID;
  api_key_id: UUID | null;
  action: AgentActionType;
  entity_type: string;
  entity_id: UUID | null;
  payload_json: unknown;
  before_json: Record<string, unknown> | null;
  result_json: unknown;
  reasoning: string;
  source: string;
  source_system: string | null;
  batch_id: string | null;
  reverted_at: string | null;
  latency_ms: number | null;
  created_at: string;
};

export type AgentActionList = {
  items: AgentAction[];
  total: number;
  page: number;
  page_size: number;
};

export type AgentActionFilters = {
  action?: string;
  source?: string;
  source_system?: string;
  entity_type?: string;
  entity_id?: UUID;
  created_from?: string;
  created_to?: string;
  only_unreverted?: boolean;
  page?: number;
  page_size?: number;
};

export type RevertResult = {
  reverted_action_ids: UUID[];
};

export type AgentInstance = {
  id: UUID;
  name: string;
  version: string | null;
  host: string;
  started_at: string | null;
  last_heartbeat_at: string | null;
  status: "running" | "stale" | "unknown" | string;
  last_error: string | null;
  config_hash: string | null;
};

export type AgentOverview = {
  agent: AgentInstance | null;
  active_job_count: number;
  active_integration_count: number;
  run_count_24h: number;
  cost_estimate_month: number;
  unacknowledged_change_count: number;
  warnings: string[];
};

export type AgentJob = {
  id: UUID;
  agent_id: UUID;
  name: string;
  description: string | null;
  schedule: string | null;
  schedule_description: string | null;
  is_enabled: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
  last_status: string | null;
  last_duration_ms: number | null;
  consecutive_failures: number;
  run_count: number;
  tags: string[];
};

export type AgentIntegration = {
  id: UUID;
  agent_id: UUID;
  name: string;
  kind: string;
  scopes: string[];
  status: string;
  last_used_at: string | null;
  error_count: number;
  added_at: string;
  notes: string | null;
};

export type AgentWatch = {
  id: UUID;
  agent_id: UUID;
  name: string;
  description: string | null;
  kind: string;
  config_json: Record<string, unknown>;
  schedule: string | null;
  is_active: boolean;
  last_checked_at: string | null;
  last_triggered_at: string | null;
  trigger_count: number;
  last_result: string | null;
};

export type AgentChannel = {
  id: UUID;
  agent_id: UUID;
  channel_type: string;
  identifier: string;
  is_active: boolean;
  last_message_at: string | null;
  message_count_24h: number;
  message_count_month: number;
};

export type AgentRun = {
  id: UUID;
  agent_id: UUID;
  job_id: UUID | null;
  trigger: string;
  summary: string;
  detail: string | null;
  status: string;
  started_at: string;
  finished_at: string | null;
  duration_ms: number | null;
  tokens_used: number | null;
  cost_estimate: number | null;
  error: string | null;
  tags: string[];
};

export type AgentConfigChange = {
  id: UUID;
  agent_id: UUID;
  timestamp: string;
  change_type: string;
  target_type: string;
  target_name: string;
  diff_json: Record<string, unknown>;
  acknowledged_at: string | null;
};

export type AgentKey = {
  id: UUID;
  name: string;
  key_prefix: string;
  scopes: string[];
  last_used_at: string | null;
  expires_at: string | null;
  revoked_at: string | null;
  created_at: string;
};

export type AgentList<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};

export type VersionedAuditFields = {
  version: number;
  created_by: MutationOrigin;
  updated_by: MutationOrigin;
  api_key_id: UUID | null;
};

export type Note = VersionedAuditFields & {
  id: UUID;
  owner_id: UUID;
  title: string;
  body: string | null;
  kind: NoteKind;
  entry_date: string | null;
  entry_time: string | null;
  mood: string | null;
  category_id: UUID | null;
  vision_id: UUID | null;
  task_id: UUID | null;
  created_at: string;
  updated_at: string;
};

export type NoteList = {
  items: Note[];
  total: number;
  page: number;
  page_size: number;
};

export type NoteFilters = {
  kind?: NoteKind | "all";
  entry_date?: string;
  date_from?: string;
  date_to?: string;
  q?: string;
  category_id?: UUID | "all";
  vision_id?: UUID | "all";
  task_id?: UUID | "all";
  page?: number;
  page_size?: number;
};

export type NoteCreate = {
  title: string;
  body?: string | null;
  kind?: NoteKind;
  entry_date?: string | null;
  entry_time?: string | null;
  mood?: string | null;
  category_id?: UUID | null;
  vision_id?: UUID | null;
  task_id?: UUID | null;
};

export type NoteUpdate = Partial<NoteCreate>;

export type NoteAttachment = {
  note_id: UUID;
  attachment_id: UUID;
  position: number;
};

export type StorageUsage = {
  file_count: number;
  used_bytes: number;
  max_bytes: number;
  remaining_bytes: number;
  used_percent: number;
};

export type Challenge = {
  id: UUID;
  owner_id: UUID;
  title: string;
  description: string | null;
  type: ChallengeType;
  category_id: UUID | null;
  vision_id: UUID | null;
  started_at: string;
  target_days: number | null;
  allowed_gap_days: number;
  schedule_rrule: string;
  is_active: boolean;
  color: string;
  icon: string;
  current_streak: number;
  longest_streak: number;
  created_at: string;
  updated_at: string;
};

export type ChallengeCreate = {
  title: string;
  description?: string | null;
  type?: ChallengeType;
  category_id?: UUID | null;
  vision_id?: UUID | null;
  started_at?: string | null;
  target_days?: number | null;
  allowed_gap_days?: number;
  schedule_rrule?: string;
  is_active?: boolean;
  color?: string;
  icon?: string;
};

export type ChallengeUpdate = Partial<ChallengeCreate>;

export type CheckInCreate = {
  date?: string | null;
  value?: number | null;
  note?: string | null;
  is_relapse?: boolean;
};

export type CheckIn = {
  id: UUID;
  owner_id: UUID;
  challenge_id: UUID;
  date: string;
  value: number | null;
  note: string | null;
  is_relapse: boolean;
  created_at: string;
  updated_at: string;
};

export type CheckInResult = {
  check_in: CheckIn;
  current_streak: number;
  longest_streak: number;
};

export type ChallengeStats = {
  current_streak: number;
  longest_streak: number;
  total_count: number;
  success_rate_30: number;
  success_rate_90: number;
  active_days_30: number;
  active_days_90: number;
};

export type ChallengeHeatmapDay = {
  date: string;
  has_check_in: boolean;
  value: number | null;
  note: string | null;
  is_relapse: boolean;
  is_paused: boolean;
  is_scheduled: boolean;
  intensity: 0 | 1 | 2 | 3 | 4;
};

export type ChallengeHeatmap = {
  year: number;
  days: ChallengeHeatmapDay[];
};

export type Category = {
  id: UUID;
  owner_id: UUID;
  name: string;
  color: string;
  icon: string;
  parent_id: UUID | null;
  position: number;
  is_archived: boolean;
  task_count: number;
  created_at: string;
  updated_at: string;
};

export type Context = {
  id: UUID;
  owner_id: UUID;
  name: string;
  color: string;
  icon: string;
  position: number;
  is_archived: boolean;
  task_count: number;
  created_at: string;
  updated_at: string;
};

export type Tag = {
  id: UUID;
  owner_id: UUID;
  name: string;
  color: string;
  icon: string;
  position: number;
  is_archived: boolean;
  task_count: number;
  created_at: string;
  updated_at: string;
};

export type Vision = {
  id: UUID;
  owner_id: UUID;
  title: string;
  description: string | null;
  parent_id: UUID | null;
  horizon: VisionHorizon;
  status: VisionStatus;
  target_date: string | null;
  category_id: UUID | null;
  position: number;
  created_at: string;
  updated_at: string;
};

export type VisionTreeNode = Vision & {
  children: VisionTreeNode[];
};

export type VisionProgress = {
  vision_id: UUID;
  total_tasks: number;
  done_tasks: number;
  last_activity_at: string | null;
  stagnation_days: number | null;
};

export type StagnatingVision = {
  vision: Vision;
  progress: VisionProgress;
};

export type VisionCreate = {
  title: string;
  description?: string | null;
  parent_id?: UUID | null;
  horizon?: VisionHorizon;
  status?: VisionStatus;
  target_date?: string | null;
  category_id?: UUID | null;
  position?: number;
};

export type VisionUpdate = Partial<VisionCreate>;

export type VisionDeleteImpact = {
  child_count: number;
  task_count: number;
};

export type Task = VersionedAuditFields & {
  id: UUID;
  owner_id: UUID;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  due_date: string | null;
  due_time: string | null;
  estimate_minutes: number | null;
  completed_at: string | null;
  completed_by: "user" | "agent" | null;
  category_id: UUID | null;
  context_id: UUID | null;
  vision_id: UUID | null;
  parent_task_id: UUID | null;
  recurrence_template_id: UUID | null;
  source: TaskSource;
  source_detail: string | null;
  recurrence_rule: string | null;
  recurrence_mode: RecurrenceMode | null;
  position: number;
  tags: Tag[];
  created_at: string;
  updated_at: string;
};

export type TaskList = {
  items: Task[];
  total: number;
  page: number;
  page_size: number;
};

export type ListResponse<T> = { items: T[] };

export type TaskFilters = {
  status?: TaskStatus | "all";
  priority?: TaskPriority | "all";
  category_id?: UUID | "all";
  context_id?: UUID | "all";
  vision_id?: UUID | "all";
  tag_ids?: UUID[];
  due_from?: string;
  due_to?: string;
  created_from?: string;
  created_to?: string;
  source?: TaskSource | "all";
  q?: string;
  view?: TaskView;
  page?: number;
  page_size?: number;
};

export type TaskCreate = {
  title: string;
  description?: string | null;
  status?: TaskStatus;
  priority?: TaskPriority;
  due_date?: string | null;
  due_time?: string | null;
  estimate_minutes?: number | null;
  category_id?: UUID | null;
  context_id?: UUID | null;
  vision_id?: UUID | null;
  parent_task_id?: UUID | null;
  source?: TaskSource;
  source_detail?: string | null;
  recurrence_rule?: string | null;
  recurrence_mode?: RecurrenceMode | null;
  position?: number;
  tag_ids?: UUID[];
};

export type TaskUpdate = Partial<TaskCreate> & {
  completed_at?: string | null;
  completed_by?: "user" | "agent" | null;
};
