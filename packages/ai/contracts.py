"""
Vision 5D — Phase 6 AI Intelligence Contracts
Structured AI design requests, proposals, options, recommendations, audit trail.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum


# ── Enums ──

class AIObjective(str, Enum):
    FURNISH_ROOM = "furnish_room"
    IMPROVE_LAYOUT = "improve_layout"
    IMPROVE_CIRCULATION = "improve_circulation"
    MODERN_INTERIOR = "modern_interior"
    MINIMAL_INTERIOR = "minimal_interior"
    FAMILY_FRIENDLY = "family_friendly"
    OFFICE_LAYOUT = "office_layout"
    HEALTHCARE_ROOM = "healthcare_room"
    IMPROVE_LIGHTING = "improve_lighting"
    RECOMMEND_FLOOR_FINISHES = "recommend_floor_finishes"
    RECOMMEND_WALL_FINISHES = "recommend_wall_finishes"
    CREATE_CAMERA_VIEWS = "create_camera_views"
    CREATE_WALKTHROUGH = "create_walkthrough"
    REDUCE_COLLISIONS = "reduce_collisions"
    BUDGET_FIT = "budget_fit"
    CUSTOM = "custom"


class AICostBand(str, Enum):
    ECONOMY = "economy"
    STANDARD = "standard"
    PREMIUM = "premium"
    LUXURY = "luxury"
    UNSPECIFIED = "unspecified"


class AIApprovalState(str, Enum):
    PENDING = "pending"
    PARTIALLY_APPROVED = "partially_approved"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    COMMITTED = "committed"


class AIProviderType(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    GEMINI = "gemini"
    NVIDIA = "nvidia"
    SIMULATION = "simulation"
    CUSTOM = "custom"


# ── Request ──

class AIDesignRequest(BaseModel):
    request_id: UUID = Field(default_factory=uuid4)
    tenant_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    source_scene_id: Optional[UUID] = None
    source_scene_version: int = 1
    source_studio_version: Optional[UUID] = None
    objective: AIObjective = AIObjective.CUSTOM
    user_text: str = ""
    target_room_ids: list[UUID] = Field(default_factory=list)
    permitted_categories: list[str] = Field(default_factory=lambda: [
        "furniture", "finishes", "lighting", "cameras"
    ])
    protected_object_ids: list[UUID] = Field(default_factory=list)
    budget_band: AICostBand = AICostBand.UNSPECIFIED
    seating_capacity: Optional[int] = None
    style_preference: str = ""
    option_count: int = 2
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── Analysis ──

class AIRoomAnalysis(BaseModel):
    room_id: UUID
    label: str = ""
    function: str = ""
    area_m2: float = 0.0
    volume_m3: float = 0.0
    dimensions: dict = Field(default_factory=dict)
    door_count: int = 0
    window_count: int = 0
    wall_availability: list[dict] = Field(default_factory=list)
    current_furniture: list[dict] = Field(default_factory=list)
    current_finishes: dict = Field(default_factory=dict)
    circulation_clearance_mm: int = 900
    focal_points: list[dict] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)


class AISceneAnalysis(BaseModel):
    analysis_id: UUID = Field(default_factory=uuid4)
    request_id: Optional[UUID] = None
    rooms: list[AIRoomAnalysis] = Field(default_factory=list)
    total_floor_area_m2: float = 0.0
    furniture_count: int = 0
    validation_issues: list[dict] = Field(default_factory=list)
    style_notes: str = ""
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ── Requirements ──

class AIInterpretedRequirement(BaseModel):
    req_id: UUID = Field(default_factory=uuid4)
    objective: AIObjective
    rooms: list[str] = Field(default_factory=list)  # room labels
    style: str = ""
    seating: Optional[int] = None
    budget: AICostBand = AICostBand.UNSPECIFIED
    furniture_additions_allowed: bool = True
    furniture_removals_allowed: bool = True
    finishes_allowed: bool = True
    lighting_allowed: bool = True
    cameras_allowed: bool = True
    protected_objects: list[str] = Field(default_factory=list)
    constraints: list[dict] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    confidence: float = 0.8


# ── Recommendations ──

class AIRecommendation(BaseModel):
    rec_id: UUID = Field(default_factory=uuid4)
    category: str = ""  # furniture, finish, lighting, camera
    action: str = ""     # add, remove, move, change, create
    target: str = ""     # object label or type
    details: dict = Field(default_factory=dict)
    rationale: str = ""
    confidence: float = 0.8
    cost_band: AICostBand = AICostBand.STANDARD
    is_blocked_by_validation: bool = False
    validation_message: str = ""


class AIProposedEdit(BaseModel):
    """A single AI-proposed edit that compiles to a StudioEditOperation."""
    edit_id: UUID = Field(default_factory=uuid4)
    operation_type: str  # StudioEditType value
    target_object_id: Optional[UUID] = None
    object_type: str = ""
    label: str = ""
    before_state: dict = Field(default_factory=dict)
    after_state: dict = Field(default_factory=dict)
    rationale: str = ""
    confidence: float = 0.8
    is_valid: bool = True
    validation_issues: list[str] = Field(default_factory=list)


# ── Proposal Options ──

class AIProposalOption(BaseModel):
    option_id: UUID = Field(default_factory=uuid4)
    name: str = ""
    summary: str = ""
    strategy: str = ""   # minimal, balanced, transformative
    affected_rooms: list[str] = Field(default_factory=list)
    furniture_additions: list[dict] = Field(default_factory=list)
    furniture_removals: list[str] = Field(default_factory=list)
    furniture_transforms: list[dict] = Field(default_factory=list)
    finish_changes: list[dict] = Field(default_factory=list)
    lighting_changes: list[dict] = Field(default_factory=list)
    camera_changes: list[dict] = Field(default_factory=list)
    advantages: list[str] = Field(default_factory=list)
    compromises: list[str] = Field(default_factory=list)
    estimated_cost_band: AICostBand = AICostBand.STANDARD
    confidence: float = 0.8
    validation_issues: list[dict] = Field(default_factory=list)
    proposed_edits: list[AIProposedEdit] = Field(default_factory=list)


class AIDesignProposal(BaseModel):
    proposal_id: UUID = Field(default_factory=uuid4)
    request_id: Optional[UUID] = None
    analysis_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    source_scene_id: Optional[UUID] = None
    source_studio_version: Optional[UUID] = None
    interpreted_requirements: Optional[AIInterpretedRequirement] = None
    options: list[AIProposalOption] = Field(default_factory=list)
    provider: str = "simulation"
    model: str = ""
    prompt_version: str = "6.0.0"
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    approval_state: AIApprovalState = AIApprovalState.PENDING
    approved_option_index: Optional[int] = None
    approved_edit_ids: list[UUID] = Field(default_factory=list)
    rejected_edit_ids: list[UUID] = Field(default_factory=list)
    ai_branch_draft_id: Optional[UUID] = None
    ai_branch_version_id: Optional[UUID] = None
    error_message: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── Provider ──

class AIProviderRun(BaseModel):
    run_id: UUID = Field(default_factory=uuid4)
    job_id: Optional[UUID] = None
    provider: AIProviderType = AIProviderType.SIMULATION
    model: str = ""
    prompt_template: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost: float = 0.0
    latency_ms: float = 0.0
    retry_count: int = 0
    error_message: str = ""
    response_data: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AIUsageRecord(BaseModel):
    record_id: UUID = Field(default_factory=uuid4)
    tenant_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    provider: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost: float = 0.0
    job_id: Optional[UUID] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── API Models ──

class AIRequestSubmit(BaseModel):
    project_id: UUID
    objective: str = "custom"
    user_text: str = ""
    source_studio_version: Optional[UUID] = None
    target_room_ids: list[UUID] = Field(default_factory=list)
    permitted_categories: list[str] = Field(default_factory=lambda: ["furniture", "finishes", "lighting", "cameras"])
    protected_object_ids: list[UUID] = Field(default_factory=list)
    budget_band: str = "unspecified"
    seating_capacity: Optional[int] = None
    style_preference: str = ""


class AIApprovalRequest(BaseModel):
    proposal_id: UUID
    approved_edit_ids: list[UUID] = Field(default_factory=list)
    rejected_edit_ids: list[UUID] = Field(default_factory=list)
    option_index: int = 0


class AIConflictResult(BaseModel):
    conflict_id: UUID = Field(default_factory=uuid4)
    proposal_id: UUID
    edit_id: Optional[UUID] = None
    severity: str = "warning"
    code: str = ""
    message: str = ""
    source_state: dict = Field(default_factory=dict)
    proposal_state: dict = Field(default_factory=dict)
    is_stale: bool = False
