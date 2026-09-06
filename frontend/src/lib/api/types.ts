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

export type TaskStatus = "inbox" | "todo" | "doing" | "done" | "cancelled";
export type TaskPriority = "none" | "low" | "medium" | "high";
export type TaskView = "today" | "this_week" | "overdue" | "inbox";
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
};

export type ChallengeHeatmapDay = {
  date: string;
  has_check_in: boolean;
  value: number | null;
  note: string | null;
  is_relapse: boolean;
  is_paused: boolean;
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
  created_at: string;
  updated_at: string;
};

export type Context = {
  id: UUID;
  owner_id: UUID;
  name: string;
  position: number;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
};

export type Tag = {
  id: UUID;
  owner_id: UUID;
  name: string;
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

export type Task = {
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
  category_id: UUID | null;
  context_id: UUID | null;
  vision_id: UUID | null;
  parent_task_id: UUID | null;
  recurrence_template_id: UUID | null;
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
  category_id?: UUID | "all";
  context_id?: UUID | "all";
  tag_ids?: UUID[];
  due_from?: string;
  due_to?: string;
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
  recurrence_rule?: string | null;
  recurrence_mode?: RecurrenceMode | null;
  position?: number;
  tag_ids?: UUID[];
};

export type TaskUpdate = Partial<TaskCreate> & {
  completed_at?: string | null;
};
