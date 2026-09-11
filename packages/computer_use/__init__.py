"""
Vision 5D — Computer-Use Contracts
Pydantic models for computer-use actions, vision responses, sessions.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum


# ═══════════════════════════════════════════════════════════
# Action Types
# ═══════════════════════════════════════════════════════════

class ActionType(str, Enum):
    SCREENSHOT = "screenshot"
    OPEN_URL = "open_url"
    MOVE_MOUSE = "move_mouse"
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    TYPE_TEXT = "type_text"
    PRESS_KEY = "press_key"
    HOTKEY = "hotkey"
    SCROLL = "scroll"
    WAIT = "wait"
    INSPECT_SCREEN = "inspect_screen"
    VERIFY_ELEMENT = "verify_element"
    VERIFY_PAGE_CHANGE = "verify_page_change"
    STOP = "stop"


class RiskLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ═══════════════════════════════════════════════════════════
# Vision Response Contract
# ═══════════════════════════════════════════════════════════

class VisibleElement(BaseModel):
    element_id: int
    element_type: str  # button, text_field, link, dropdown, checkbox, image, label, etc.
    label: str = ""
    bounding_box: dict = Field(default_factory=lambda: {"x": 0, "y": 0, "w": 0, "h": 0})
    confidence: float = 0.0
    state: str = ""  # enabled, disabled, selected, highlighted
    text_content: str = ""


class VisionResponse(BaseModel):
    """Strict structured contract for NVIDIA vision responses."""
    screen_summary: str = ""
    visible_elements: list[VisibleElement] = Field(default_factory=list)
    proposed_action: Optional[dict] = None
    expected_result: str = ""
    risk_level: RiskLevel = RiskLevel.LOW
    requires_confirmation: bool = False
    raw_response: dict = Field(default_factory=dict)
    model: str = ""
    latency_ms: float = 0.0
    error: str = ""

    def is_valid(self) -> bool:
        return len(self.visible_elements) > 0 and not self.error


# ═══════════════════════════════════════════════════════════
# Action Models
# ═══════════════════════════════════════════════════════════

class ComputerAction(BaseModel):
    """A validated, executable computer-use action."""
    action_id: UUID = Field(default_factory=uuid4)
    action_type: ActionType
    params: dict = Field(default_factory=dict)
    proposed_by_model: bool = False
    risk_level: RiskLevel = RiskLevel.LOW
    requires_confirmation: bool = False
    expected_result: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    def validate(self) -> list[str]:
        """Validate action params. Returns list of issues."""
        issues = []
        t = self.action_type
        p = self.params

        if t == ActionType.OPEN_URL:
            url = p.get("url", "")
            if not url:
                issues.append("open_url requires 'url' param")
        elif t in (ActionType.CLICK, ActionType.DOUBLE_CLICK, ActionType.RIGHT_CLICK):
            if "element_id" not in p and "x" not in p:
                issues.append("click requires 'element_id' or 'x','y' params")
        elif t == ActionType.MOVE_MOUSE:
            if "x" not in p or "y" not in p:
                issues.append("move_mouse requires 'x','y' params")
        elif t == ActionType.TYPE_TEXT:
            if "text" not in p:
                issues.append("type_text requires 'text' param")
        elif t in (ActionType.PRESS_KEY, ActionType.HOTKEY):
            if "keys" not in p:
                issues.append(f"{t.value} requires 'keys' param")
        elif t == ActionType.SCROLL:
            if "direction" not in p:
                issues.append("scroll requires 'direction' param")
        elif t == ActionType.WAIT:
            if "seconds" not in p:
                issues.append("wait requires 'seconds' param")

        return issues


class ActionResult(BaseModel):
    """Result of executing a computer-use action."""
    action_id: UUID
    success: bool
    before_screenshot_path: str = ""
    after_screenshot_path: str = ""
    visual_confirmation: bool = False
    error: str = ""
    duration_ms: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: dict = Field(default_factory=dict)


# ═══════════════════════════════════════════════════════════
# Session
# ═══════════════════════════════════════════════════════════

class SessionState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    STOPPED = "stopped"
    EMERGENCY_STOPPED = "emergency_stopped"
    ERROR = "error"


class ComputerUseSession(BaseModel):
    session_id: UUID = Field(default_factory=uuid4)
    state: SessionState = SessionState.IDLE
    objective: str = ""
    action_history: list[ActionResult] = Field(default_factory=list)
    action_count: int = 0
    max_actions: int = 50
    action_timeout_seconds: int = 30
    current_screenshot: str = ""
    last_vision_response: Optional[VisionResponse] = None
    pending_confirmation: Optional[ComputerAction] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    error: str = ""


# ═══════════════════════════════════════════════════════════
# Security Configuration
# ═══════════════════════════════════════════════════════════

class SecurityConfig(BaseModel):
    enabled: bool = False
    domain_allowlist: list[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1"])
    app_allowlist: list[str] = Field(default_factory=lambda: ["chrome", "firefox", "msedge"])
    max_actions_per_session: int = 50
    action_timeout_seconds: int = 30
    require_confirmation_for: list[RiskLevel] = Field(default_factory=lambda: [RiskLevel.HIGH, RiskLevel.CRITICAL])
    destructive_action_patterns: list[str] = Field(default_factory=lambda: [
        "delete", "remove", "uninstall", "format", "drop",
        "rm -rf", "shutdown", "restart", "logout"
    ])
    blocked_keys: list[str] = Field(default_factory=lambda: [
        "ctrl+alt+del", "win+l", "cmd+opt+esc"
    ])
    audit_enabled: bool = True
    screenshot_redaction_enabled: bool = True


class AuditEntry(BaseModel):
    entry_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    event_type: str
    action: Optional[ComputerAction] = None
    result: Optional[ActionResult] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: dict = Field(default_factory=dict)
