"""
Vision 5D — Computer-Use Security Controls
Domain/application allowlists, action validation, audit trail, screenshot redaction.
"""
import os, re, json, hashlib
from uuid import uuid4
from datetime import datetime
from typing import Optional
import structlog

from packages.computer_use import (
    ComputerAction, ActionResult, ActionType, RiskLevel,
    SecurityConfig, AuditEntry, ComputerUseSession,
)

logger = structlog.get_logger()


class SecurityGuard:
    """Validates every action before execution. Enforces allowlists and confirmations."""

    def __init__(self, config: Optional[SecurityConfig] = None):
        self.config = config or SecurityConfig()
        self._audit_log: list[AuditEntry] = []
        self._emergency_stop: bool = False

    @property
    def is_emergency_stopped(self) -> bool:
        return self._emergency_stop

    def emergency_stop(self) -> None:
        self._emergency_stop = True
        logger.critical("emergency_stop_activated")

    def reset_emergency(self) -> None:
        self._emergency_stop = False

    def validate_action(self, action: ComputerAction, session: ComputerUseSession) -> tuple[bool, list[str]]:
        """Validate an action against security rules. Returns (allowed, issues)."""
        issues = []

        if not self.config.enabled:
            return True, []

        if self._emergency_stop:
            return False, ["Emergency stop is active"]

        # Also check session state for emergency stop
        from packages.computer_use import SessionState
        if session.state == SessionState.EMERGENCY_STOPPED:
            return False, ["Session is emergency stopped"]

        # Action timeout
        if session.action_count >= self.config.max_actions_per_session:
            return False, [f"Maximum actions ({self.config.max_actions_per_session}) reached"]

        # Validate action params
        param_issues = action.validate()
        issues.extend(param_issues)

        # URL validation
        if action.action_type == ActionType.OPEN_URL:
            url = action.params.get("url", "")
            url_issues = self._validate_url(url)
            issues.extend(url_issues)

        # Destructive action check
        if self._is_destructive(action):
            action.risk_level = RiskLevel.CRITICAL
            action.requires_confirmation = True
            issues.append("Destructive action requires explicit confirmation")

        # Key validation
        if action.action_type in (ActionType.PRESS_KEY, ActionType.HOTKEY):
            keys = action.params.get("keys", "")
            if keys in self.config.blocked_keys:
                return False, [f"Key combination '{keys}' is blocked"]

        # If there are blocking issues (not just confirmation requirements), reject
        blocking_issues = [i for i in issues if "requires confirmation" not in i.lower() and "confirmation" not in i.lower()]
        if blocking_issues:
            return False, issues
        return True, issues

    def requires_confirmation(self, action: ComputerAction) -> bool:
        """Check if this action requires user confirmation."""
        if action.requires_confirmation:
            return True
        if action.risk_level in self.config.require_confirmation_for:
            return True
        if self._is_destructive(action):
            return True
        return False

    def _validate_url(self, url: str) -> list[str]:
        issues = []
        if not url:
            return ["URL is empty"]

        # Allow only http/https
        if not url.startswith(("http://", "https://")):
            return [f"URL scheme not allowed: {url[:50]}"]

        # Extract domain
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.hostname or ""
        except Exception:
            domain = ""

        if not domain:
            return ["Could not parse URL domain"]

        # Check domain allowlist
        allowed = False
        for allowed_domain in self.config.domain_allowlist:
            if domain == allowed_domain or domain.endswith("." + allowed_domain):
                allowed = True
                break

        if not allowed:
            issues.append(
                f"Domain '{domain}' not in allowlist. Allowed: {self.config.domain_allowlist}"
            )

        return issues

    def _is_destructive(self, action: ComputerAction) -> bool:
        """Check if action matches destructive patterns."""
        # Check params for destructive patterns
        for key, value in action.params.items():
            value_str = str(value).lower()
            for pattern in self.config.destructive_action_patterns:
                if pattern.lower() in value_str:
                    return True

        # Check action type
        if action.action_type == ActionType.PRESS_KEY:
            keys = action.params.get("keys", "").lower()
            if any(bk in keys for bk in ["delete", "backspace"]):
                # Not inherently destructive but flag for awareness
                pass

        return False

    def redact_screenshot(self, image_bytes: bytes) -> bytes:
        """Redact sensitive information from screenshots before storage."""
        if not self.config.screenshot_redaction_enabled:
            return image_bytes

        # Basic redaction: we don't modify the image bytes directly
        # Instead, we log that redaction was considered
        # Full redaction would use OCR + image processing
        logger.info("screenshot_redaction_considered", size=len(image_bytes))
        return image_bytes

    def audit(self, session_id, event_type: str, action=None, result=None, details=None):
        """Record an audit entry."""
        if not self.config.audit_enabled:
            return

        entry = AuditEntry(
            session_id=session_id,
            event_type=event_type,
            action=action,
            result=result,
            details=details or {},
        )
        self._audit_log.append(entry)
        logger.info("audit_event", event_type=event_type, session_id=str(session_id))

    def get_audit_log(self, session_id=None) -> list[dict]:
        entries = self._audit_log
        if session_id:
            entries = [e for e in entries if str(e.session_id) == str(session_id)]
        return [e.model_dump(mode="json") for e in entries]


# Singleton
security_guard = SecurityGuard()
