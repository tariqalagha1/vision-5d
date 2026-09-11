"""
Vision 5D — Shared Contracts Package
All certified Phase 1 contract types as Pydantic models.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any, Literal
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum


# ═══════════════════════════════════════════════════════════
# Base Types
# ═══════════════════════════════════════════════════════════

class Severity(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    FATAL = "FATAL"


class JobState(str, Enum):
    CREATED = "CREATED"
    AUTHORIZED = "AUTHORIZED"
    QUEUED = "QUEUED"
    DISPATCHED = "DISPATCHED"
    CLAIMED = "CLAIMED"
    RUNNING = "RUNNING"
    CHECKPOINTED = "CHECKPOINTED"
    VALIDATING = "VALIDATING"
    PAUSE_REQUESTED = "PAUSE_REQUESTED"
    PAUSED = "PAUSED"
    RESUME_REQUESTED = "RESUME_REQUESTED"
    RETRY_SCHEDULED = "RETRY_SCHEDULED"
    COMPLETED = "COMPLETED"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    FAILED_TERMINAL = "FAILED_TERMINAL"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    INTERRUPTED = "INTERRUPTED"
    RESUMING = "RESUMING"


class ProjectState(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"


class WorkspaceState(str, Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class PermissionLevel(str, Enum):
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


class ProviderType(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    DEEPSEEK = "deepseek"
    NVIDIA = "nvidia"
    CUSTOM = "custom"


class ConnectionStatus(str, Enum):
    UNTESTED = "UNTESTED"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


class ValidationDecision(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"


class ArtifactState(str, Enum):
    CREATED = "CREATED"
    REGISTERED = "REGISTERED"
    STORED = "STORED"
    VALIDATED = "VALIDATED"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"


class ProviderResultCode(str, Enum):
    SUCCESS = "SUCCESS"
    INVALID_CREDENTIAL = "INVALID_CREDENTIAL"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    MODEL_UNSUPPORTED = "MODEL_UNSUPPORTED"
    RATE_LIMITED = "RATE_LIMITED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    NETWORK_TIMEOUT = "NETWORK_TIMEOUT"
    INVALID_BASE_URL = "INVALID_BASE_URL"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"
    POLICY_REJECTED = "POLICY_REJECTED"


class ScreeningResult(str, Enum):
    CLEAN = "CLEAN"
    SUSPICIOUS = "SUSPICIOUS"
    MALICIOUS = "MALICIOUS"
    ERROR = "ERROR"


# ═══════════════════════════════════════════════════════════
# Tenant & Identity
# ═══════════════════════════════════════════════════════════

class TenantRef(BaseModel):
    tenant_id: UUID
    model_config = ConfigDict(frozen=True)


class UserRef(BaseModel):
    user_id: UUID
    tenant_id: UUID
    email: str
    display_name: str
    model_config = ConfigDict(frozen=True)


class Session(BaseModel):
    session_token: str
    user_id: UUID
    tenant_id: UUID
    expires_at: datetime


class AuthRequest(BaseModel):
    provider: Literal["google", "github"] = "google"
    oauth_token: str


class AuthResponse(BaseModel):
    authenticated: bool = True
    user_id: UUID
    tenant_id: UUID
    session_token: str
    session_expires_at: datetime
    is_new_user: bool = False


class AuthorizeRequest(BaseModel):
    session_token: str
    resource_type: Literal["workspace", "project", "provider_config", "artifact", "job"]
    resource_id: UUID
    required_permission: PermissionLevel


class AuthorizeResponse(BaseModel):
    authorized: bool
    user_id: UUID
    tenant_id: UUID
    permission_level: PermissionLevel
    decision_id: UUID = Field(default_factory=uuid4)


# ═══════════════════════════════════════════════════════════
# Workspace & Project
# ═══════════════════════════════════════════════════════════

class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    settings: Optional[dict] = None


class Workspace(BaseModel):
    workspace_id: UUID = Field(default_factory=uuid4)
    name: str
    tenant_id: UUID
    owner_user_id: UUID
    state: WorkspaceState = WorkspaceState.ACTIVE
    created_at: datetime = Field(default_factory=datetime.utcnow)
    settings: dict = Field(default_factory=dict)
    model_config = ConfigDict(from_attributes=True)


class ProjectCreate(BaseModel):
    workspace_id: UUID
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    project_type: Optional[str] = "other"
    settings: Optional[dict] = None


class Project(BaseModel):
    project_id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    name: str
    state: ProjectState = ProjectState.DRAFT
    project_type: str = "other"
    owner_user_id: UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    settings: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
    version: int = 1
    model_config = ConfigDict(from_attributes=True)


class ProjectConfigure(BaseModel):
    name: Optional[str] = None
    settings: Optional[dict] = None


class MetadataUpdate(BaseModel):
    metadata: dict


class StatusTransition(BaseModel):
    target_state: ProjectState


class PermissionGrant(BaseModel):
    project_id: UUID
    grantee_user_id: UUID
    permission_level: PermissionLevel


class PermissionRevoke(BaseModel):
    permission_id: UUID


class ProjectListParams(BaseModel):
    workspace_id: UUID
    state_filter: Optional[list[ProjectState]] = None
    search_query: Optional[str] = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class ProjectListResponse(BaseModel):
    projects: list[Project]
    total_count: int
    limit: int
    offset: int


# ═══════════════════════════════════════════════════════════
# LLM Provider Configuration
# ═══════════════════════════════════════════════════════════

class ProviderCreate(BaseModel):
    workspace_id: UUID
    provider_type: ProviderType
    display_name: str = Field(min_length=1, max_length=100)
    base_url: Optional[str] = None
    default_model_id: Optional[str] = None


class ProviderConfig(BaseModel):
    provider_id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    tenant_id: UUID
    provider_type: ProviderType
    display_name: str
    base_url: Optional[str] = None
    default_model_id: Optional[str] = None
    capability_flags: dict = Field(default_factory=dict)
    enabled: bool = True
    is_default: bool = False
    connection_status: ConnectionStatus = ConnectionStatus.UNTESTED
    last_tested_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    model_config = ConfigDict(from_attributes=True)


class ApiKeySubmit(BaseModel):
    provider_id: UUID
    api_key: str  # Transmitted over HTTPS only
    key_label: Optional[str] = None


class SecretRef(BaseModel):
    secret_ref_id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    provider_id: UUID
    secret_version: int = 1
    key_label: Optional[str] = None
    status: Literal["active", "rotated", "deleted"] = "active"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    model_config = ConfigDict(from_attributes=True)


class ProviderTestRequest(BaseModel):
    provider_id: UUID
    model_id: Optional[str] = None
    capability_to_test: Literal["chat", "vision", "structured_output"] = "chat"
    timeout_seconds: int = Field(default=15, ge=1, le=30)


class ProviderTestResult(BaseModel):
    status: Literal["SUCCESS", "FAILURE"] = "FAILURE"
    result_code: ProviderResultCode
    model_tested: Optional[str] = None
    capability_confirmed: dict = Field(default_factory=dict)
    latency_ms: Optional[int] = None
    tested_at: datetime = Field(default_factory=datetime.utcnow)
    provider_id: UUID


class ModelInfo(BaseModel):
    model_id: str
    display_name: str
    capabilities: dict
    context_window: Optional[int] = None


class ModelListResponse(BaseModel):
    provider_id: UUID
    models: list[ModelInfo]
    discovered_at: datetime = Field(default_factory=datetime.utcnow)


class DefaultModelSelect(BaseModel):
    provider_id: UUID
    model_id: str


class TenantIsolationResult(BaseModel):
    tenant_id: UUID
    isolation_valid: bool
    checks_performed: list[str]
    validation_timestamp: datetime = Field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════
# Asset Intake
# ═══════════════════════════════════════════════════════════

class UploadInitRequest(BaseModel):
    project_id: UUID
    filename: str = Field(min_length=1, max_length=255)
    file_size_bytes: int = Field(ge=1, le=524288000)  # Max 500MB
    content_type: str
    idempotency_key: Optional[str] = None


class UploadSession(BaseModel):
    upload_session_id: UUID = Field(default_factory=uuid4)
    state: Literal["RECEIVING", "COMPLETE", "EXPIRED"] = "RECEIVING"
    project_id: UUID
    tenant_id: UUID
    filename: str
    file_size_bytes: int
    content_type: str
    max_chunk_size: int = 10485760
    total_chunks: int = 0
    chunks_received: int = 0
    content_hash: Optional[str] = None
    storage_locator: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    model_config = ConfigDict(from_attributes=True)


class AssetRegister(BaseModel):
    upload_session_id: UUID
    project_id: UUID
    metadata: Optional[dict] = None


class SourceAsset(BaseModel):
    asset_id: UUID = Field(default_factory=uuid4)
    artifact_id: Optional[UUID] = None
    project_id: UUID
    tenant_id: UUID
    state: str = "REGISTERED"
    filename: str
    file_size_bytes: int
    content_hash: str
    mime_type: str
    storage_locator: str
    registered_at: datetime = Field(default_factory=datetime.utcnow)
    model_config = ConfigDict(from_attributes=True)


class IntegrityReport(BaseModel):
    asset_id: UUID
    integrity_verified: bool
    expected_hash: str
    computed_hash: str
    hash_match: bool
    verified_at: datetime = Field(default_factory=datetime.utcnow)


class MalwareReport(BaseModel):
    asset_id: UUID
    screening_result: ScreeningResult
    scanner_version: str = "1.0.0"
    details: Optional[str] = None
    screened_at: datetime = Field(default_factory=datetime.utcnow)


class FormatReport(BaseModel):
    asset_id: UUID
    detected_format: str
    detected_extension: str
    claimed_extension: str
    extension_mismatch: bool = False
    identified_at: datetime = Field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════
# Durable Jobs
# ═══════════════════════════════════════════════════════════

class JobCreate(BaseModel):
    tenant_id: UUID
    workspace_id: UUID
    project_id: UUID
    job_type: str
    params: dict
    idempotency_key: str
    parent_job_id: Optional[UUID] = None


class DurableJob(BaseModel):
    job_id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    workspace_id: UUID
    project_id: UUID
    job_type: str
    job_version: str = "1.0.0"
    idempotency_key: str
    correlation_id: UUID = Field(default_factory=uuid4)
    state: JobState = JobState.CREATED
    params: dict
    param_hash: str = ""
    initiated_by: str = "user"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class JobAttempt(BaseModel):
    attempt_id: UUID = Field(default_factory=uuid4)
    job_id: UUID
    attempt_number: int = 1
    worker_id: Optional[str] = None
    state: str = "RUNNING"
    failure_category: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class Checkpoint(BaseModel):
    checkpoint_id: UUID = Field(default_factory=uuid4)
    job_id: UUID
    attempt_id: UUID
    sequence: int
    serialized_state: bytes = b""
    content_hash: str = ""
    state_version: int = 1
    resume_compatible: bool = True
    pipeline_type: Optional[str] = None
    current_stage: Optional[str] = None
    completed_stages: list[str] = Field(default_factory=list)
    input_version_ref: Optional[str] = None
    artifact_refs: dict = Field(default_factory=dict)
    tenant_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    params: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    model_config = ConfigDict(from_attributes=True)


class JobSubmitRequest(BaseModel):
    """Request to create and submit a durable job from an API route."""
    job_type: str
    params: dict
    idempotency_key: Optional[str] = None
    source_asset_id: Optional[UUID] = None


class JobSubmitResponse(BaseModel):
    """Response returned immediately after job creation, before worker execution."""
    job_id: UUID
    state: JobState
    idempotency_key: str
    created_at: datetime
    # Link to poll for progress
    status_endpoint: str


class DurableArtifactRef(BaseModel):
    """Persisted reference to a durable artifact stored in object storage."""
    artifact_id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    project_id: UUID
    job_id: UUID
    artifact_type: str
    storage_provider: str = "s3"
    storage_key: str
    content_hash: str
    size_bytes: int = 0
    mime_type: str = "application/octet-stream"
    producing_stage: Optional[str] = None
    producing_version: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    model_config = ConfigDict(from_attributes=True)


class ProgressEvent(BaseModel):
    job_id: UUID
    attempt_id: UUID
    status: str
    progress_pct: float = Field(ge=0.0, le=100.0)
    message: Optional[str] = None
    current_stage: Optional[str] = None
    estimated_remaining_seconds: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class JobStatus(BaseModel):
    job_id: UUID
    state: JobState
    progress_pct: float = 0.0
    current_stage: Optional[str] = None
    message: Optional[str] = None
    attempt: int = 1
    started_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    recent_events: list[ProgressEvent] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════
# Validation
# ═══════════════════════════════════════════════════════════

class ValidationErrorDetail(BaseModel):
    field: Optional[str] = None
    code: str
    message: str
    received: Optional[Any] = None


class ValidationResult(BaseModel):
    validation_id: UUID = Field(default_factory=uuid4)
    valid: bool
    schema_id: Optional[str] = None
    schema_version: Optional[str] = None
    skill_id: Optional[str] = None
    target_artifact_id: Optional[UUID] = None
    decision: ValidationDecision = ValidationDecision.PASS
    errors: list[ValidationErrorDetail] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    evidence_refs: list[UUID] = Field(default_factory=list)
    validated_at: datetime = Field(default_factory=datetime.utcnow)
    human_review_required: bool = False


# ═══════════════════════════════════════════════════════════
# Observability
# ═══════════════════════════════════════════════════════════

class LogEvent(BaseModel):
    severity: Severity
    component: str
    event_code: str
    message: str
    skill_id: Optional[str] = None
    skill_version: Optional[str] = None
    job_id: Optional[UUID] = None
    attempt_id: Optional[UUID] = None
    workspace_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    details: Optional[dict] = None
    correlation_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HashResult(BaseModel):
    hash: str
    algorithm: str = "sha256"
    content_type: str = "bytes"
    canonicalization: str = "none"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════
# Artifacts
# ═══════════════════════════════════════════════════════════

class ArtifactCreate(BaseModel):
    artifact_type: str
    tenant_id: UUID
    workspace_id: UUID
    project_id: UUID
    parent_artifact_id: Optional[UUID] = None
    content_hash: Optional[str] = None
    metadata: Optional[dict] = None
    idempotency_key: Optional[str] = None


class Artifact(BaseModel):
    artifact_id: UUID = Field(default_factory=uuid4)
    artifact_type: str
    state: ArtifactState = ArtifactState.CREATED
    tenant_id: UUID
    workspace_id: UUID
    project_id: UUID
    parent_artifact_id: Optional[UUID] = None
    content_hash: Optional[str] = None
    storage_locator: Optional[str] = None
    content_size_bytes: Optional[int] = None
    version: int = 1
    provenance: Optional[dict] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    model_config = ConfigDict(from_attributes=True)


class ArtifactRegister(BaseModel):
    artifact_id: UUID
    content_hash: str
    storage_locator: str
    provenance: Optional[dict] = None
    validator_result_ref: Optional[UUID] = None


# ═══════════════════════════════════════════════════════════
# Error Contracts
# ═══════════════════════════════════════════════════════════

class ErrorCode(str, Enum):
    # Auth
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    INSUFFICIENT_PERMISSION = "INSUFFICIENT_PERMISSION"
    ACCESS_DENIED = "ACCESS_DENIED"
    CROSS_TENANT_ACCESS = "CROSS_TENANT_ACCESS"
    # Validation
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    CONTRACT_VIOLATION = "CONTRACT_VIOLATION"
    # Resource
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    CONFLICT = "CONFLICT"
    # Provider
    INVALID_CREDENTIAL = "INVALID_CREDENTIAL"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    RATE_LIMITED = "RATE_LIMITED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    # Intake
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    UNSUPPORTED_TYPE = "UNSUPPORTED_TYPE"
    HASH_MISMATCH = "HASH_MISMATCH"
    MALWARE_DETECTED = "MALWARE_DETECTED"
    # Job
    INVALID_TRANSITION = "INVALID_TRANSITION"
    JOB_EXPIRED = "JOB_EXPIRED"
    DUPLICATE_IDEMPOTENCY_KEY = "DUPLICATE_IDEMPOTENCY_KEY"
    # Internal
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SECRET_DETECTED = "SECRET_DETECTED"


class ApiError(BaseModel):
    error: ErrorCode
    message: str
    details: Optional[dict] = None
    correlation_id: Optional[UUID] = None


# ═══════════════════════════════════════════════════════════
# Job State Transition Rules
# ═══════════════════════════════════════════════════════════

VALID_TRANSITIONS: dict[JobState, set[JobState]] = {
    JobState.CREATED: {JobState.AUTHORIZED},
    JobState.AUTHORIZED: {JobState.QUEUED},
    JobState.QUEUED: {JobState.DISPATCHED, JobState.CLAIMED},
    JobState.DISPATCHED: {JobState.RUNNING, JobState.CLAIMED},
    JobState.CLAIMED: {JobState.RUNNING, JobState.INTERRUPTED, JobState.FAILED_TERMINAL},
    JobState.RUNNING: {JobState.CHECKPOINTED, JobState.VALIDATING, JobState.PAUSE_REQUESTED,
                       JobState.FAILED_RETRYABLE, JobState.FAILED_TERMINAL, JobState.CANCEL_REQUESTED,
                       JobState.INTERRUPTED},
    JobState.CHECKPOINTED: {JobState.RUNNING, JobState.INTERRUPTED},
    JobState.INTERRUPTED: {JobState.QUEUED, JobState.FAILED_TERMINAL, JobState.CANCELLED},
    JobState.RESUMING: {JobState.RUNNING, JobState.FAILED_TERMINAL},
    JobState.VALIDATING: {JobState.COMPLETED, JobState.FAILED_RETRYABLE, JobState.FAILED_TERMINAL},
    JobState.PAUSE_REQUESTED: {JobState.PAUSED},
    JobState.PAUSED: {JobState.RESUME_REQUESTED},
    JobState.RESUME_REQUESTED: {JobState.QUEUED, JobState.RESUMING},
    JobState.RETRY_SCHEDULED: {JobState.QUEUED},
    JobState.FAILED_RETRYABLE: {JobState.RETRY_SCHEDULED},
}

TERMINAL_STATES: set[JobState] = {
    JobState.COMPLETED, JobState.FAILED_TERMINAL,
    JobState.CANCELLED, JobState.EXPIRED
}


def is_valid_transition(from_state: JobState, to_state: JobState) -> bool:
    """Validate a job state transition against the certified state machine."""
    if from_state in TERMINAL_STATES:
        return False
    return to_state in VALID_TRANSITIONS.get(from_state, set())
