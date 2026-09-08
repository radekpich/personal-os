import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

JsonDict = dict[str, Any]


class AgentIdentityIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    version: str | None = Field(default=None, max_length=80)
    host: str = Field(min_length=1, max_length=160)
    started_at: datetime | None = None


class AgentJobIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    schedule: str | None = Field(default=None, max_length=120)
    schedule_description: str | None = Field(default=None, max_length=240)
    is_enabled: bool = True
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    last_status: str | None = Field(default=None, max_length=30)
    last_duration_ms: int | None = Field(default=None, ge=0)
    consecutive_failures: int = Field(default=0, ge=0)
    run_count: int = Field(default=0, ge=0)
    tags: list[str] = Field(default_factory=list)


class AgentIntegrationIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    kind: str = Field(min_length=1, max_length=40)
    scopes: list[str] = Field(default_factory=list)
    status: str = Field(default="active", max_length=30)
    last_used_at: datetime | None = None
    error_count: int = Field(default=0, ge=0)
    added_at: datetime | None = None
    notes: str | None = None


class AgentWatchIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    kind: str = Field(min_length=1, max_length=40)
    config_json: JsonDict = Field(default_factory=dict)
    schedule: str | None = Field(default=None, max_length=120)
    is_active: bool = True
    last_checked_at: datetime | None = None
    last_triggered_at: datetime | None = None
    trigger_count: int = Field(default=0, ge=0)
    last_result: str | None = None


class AgentChannelIn(BaseModel):
    channel_type: str = Field(min_length=1, max_length=40)
    identifier: str = Field(min_length=1, max_length=240)
    is_active: bool = True
    last_message_at: datetime | None = None
    message_count_24h: int = Field(default=0, ge=0)
    message_count_month: int = Field(default=0, ge=0)


class AgentCapabilityIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    is_enabled: bool = True
    metadata_json: JsonDict = Field(default_factory=dict)


class AgentRegistrySyncRequest(BaseModel):
    agent: AgentIdentityIn
    jobs: list[AgentJobIn] = Field(default_factory=list)
    integrations: list[AgentIntegrationIn] = Field(default_factory=list)
    watches: list[AgentWatchIn] = Field(default_factory=list)
    channels: list[AgentChannelIn] = Field(default_factory=list)
    capabilities: list[AgentCapabilityIn] = Field(default_factory=list)
    snapshot_hash: str = Field(min_length=1, max_length=128)


class AgentRegistrySyncResponse(BaseModel):
    agent_id: uuid.UUID
    snapshot_hash: str
    idempotent: bool
    changes_created: int


class AgentInstanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    version: str | None
    host: str
    started_at: datetime | None
    last_heartbeat_at: datetime | None
    status: str
    last_error: str | None
    config_hash: str | None


class AgentJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_id: uuid.UUID
    name: str
    description: str | None
    schedule: str | None
    schedule_description: str | None
    is_enabled: bool
    last_run_at: datetime | None
    next_run_at: datetime | None
    last_status: str | None
    last_duration_ms: int | None
    consecutive_failures: int
    run_count: int
    tags: list[str]


class AgentIntegrationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_id: uuid.UUID
    name: str
    kind: str
    scopes: list[str]
    status: str
    last_used_at: datetime | None
    error_count: int
    added_at: datetime
    notes: str | None


class AgentWatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_id: uuid.UUID
    name: str
    description: str | None
    kind: str
    config_json: JsonDict
    schedule: str | None
    is_active: bool
    last_checked_at: datetime | None
    last_triggered_at: datetime | None
    trigger_count: int
    last_result: str | None


class AgentChannelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_id: uuid.UUID
    channel_type: str
    identifier: str
    is_active: bool
    last_message_at: datetime | None
    message_count_24h: int
    message_count_month: int


class AgentRunIn(BaseModel):
    job_id: uuid.UUID | None = None
    trigger: str = Field(min_length=1, max_length=40)
    summary: str = Field(min_length=1, max_length=500)
    detail: str | None = None
    status: str = Field(min_length=1, max_length=30)
    started_at: datetime
    finished_at: datetime | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    tokens_used: int | None = Field(default=None, ge=0)
    cost_estimate: float | None = Field(default=None, ge=0)
    error: str | None = None
    tags: list[str] = Field(default_factory=list)


class AgentRunsIn(BaseModel):
    runs: list[AgentRunIn] = Field(default_factory=list)


class AgentRunsCreated(BaseModel):
    created: int


class AgentRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_id: uuid.UUID
    job_id: uuid.UUID | None
    trigger: str
    summary: str
    detail: str | None
    status: str
    started_at: datetime
    finished_at: datetime | None
    duration_ms: int | None
    tokens_used: int | None
    cost_estimate: float | None
    error: str | None
    tags: list[str]


class WatchReportIn(BaseModel):
    checked_at: datetime
    triggered: bool = False
    result: str | None = None


class AgentConfigChangeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_id: uuid.UUID
    timestamp: datetime
    change_type: str
    target_type: str
    target_name: str
    diff_json: JsonDict
    acknowledged_at: datetime | None


class AgentKeyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    key_prefix: str
    scopes: list[str]
    last_used_at: datetime | None
    expires_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


class AgentList(BaseModel):
    items: list[JsonDict]
    total: int
    page: int = 1
    page_size: int = 50


class AgentOverview(BaseModel):
    agent: AgentInstanceRead | None
    active_job_count: int
    active_integration_count: int
    run_count_24h: int
    cost_estimate_month: float
    unacknowledged_change_count: int
    warnings: list[str]
