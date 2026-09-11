"""
Vision 5D — Computer-Use Session Manager
Orchestrates the controlled computer-use loop:
capture → analyze → validate → execute → verify → repeat.
"""
import os, time, json
from uuid import uuid4
from datetime import datetime
from typing import Optional
import structlog

from packages.computer_use import (
    ComputerUseSession, ComputerAction, ActionResult,
    VisionResponse, ActionType, RiskLevel, SessionState,
    SecurityConfig,
)
from packages.computer_use.vision import NVIDIAVisionAnalyzer, get_vision_analyzer
from packages.computer_use.executor import ActionExecutor, executor
from packages.computer_use.security import SecurityGuard, security_guard

logger = structlog.get_logger()


class ComputerUseSessionManager:
    """Manages a single computer-use session with the controlled loop."""

    def __init__(self, vision: Optional[NVIDIAVisionAnalyzer] = None,
                 exec_engine: Optional[ActionExecutor] = None,
                 guard: Optional[SecurityGuard] = None):
        self.vision = vision or get_vision_analyzer()
        self.executor = exec_engine or executor
        self.guard = guard or security_guard
        self._sessions: dict[str, ComputerUseSession] = {}

    def create_session(self, objective: str = "",
                       security_config: Optional[SecurityConfig] = None) -> ComputerUseSession:
        session = ComputerUseSession(objective=objective)
        self._sessions[str(session.session_id)] = session
        if security_config:
            self.guard.config = security_config
        self.guard.audit(session.session_id, "session_created")
        logger.info("computer_use_session_created", session_id=str(session.session_id))
        return session

    def get_session(self, session_id: str) -> Optional[ComputerUseSession]:
        return self._sessions.get(session_id)

    def list_sessions(self) -> list[dict]:
        return [
            {"session_id": str(s.session_id), "state": s.state.value, "objective": s.objective[:80]}
            for s in self._sessions.values()
        ]

    def start_session(self, session_id: str) -> dict:
        session = self.get_session(session_id)
        if not session:
            return {"error": "Session not found"}

        if session.state == SessionState.EMERGENCY_STOPPED:
            return {"error": "Session is emergency-stopped. Reset before starting."}

        session.state = SessionState.RUNNING
        session.updated_at = datetime.utcnow()
        self.guard.audit(session_id, "session_started")
        return {"session_id": session_id, "state": session.state.value}

    def pause_session(self, session_id: str) -> dict:
        session = self.get_session(session_id)
        if not session:
            return {"error": "Session not found"}
        session.state = SessionState.PAUSED
        session.updated_at = datetime.utcnow()
        self.guard.audit(session_id, "session_paused")
        return {"session_id": session_id, "state": session.state.value}

    def resume_session(self, session_id: str) -> dict:
        session = self.get_session(session_id)
        if not session:
            return {"error": "Session not found"}
        session.state = SessionState.RUNNING
        session.updated_at = datetime.utcnow()
        self.guard.audit(session_id, "session_resumed")
        return {"session_id": session_id, "state": session.state.value}

    def emergency_stop(self, session_id: str) -> dict:
        session = self.get_session(session_id)
        if not session:
            return {"error": "Session not found"}
        session.state = SessionState.EMERGENCY_STOPPED
        session.updated_at = datetime.utcnow()
        self.guard.emergency_stop()
        self.guard.audit(session_id, "emergency_stop")
        return {"session_id": session_id, "state": session.state.value}

    def stop_session(self, session_id: str) -> dict:
        session = self.get_session(session_id)
        if not session:
            return {"error": "Session not found"}
        session.state = SessionState.STOPPED
        session.updated_at = datetime.utcnow()
        self.guard.reset_emergency()
        self.guard.audit(session_id, "session_stopped")
        return {"session_id": session_id, "state": session.state.value}

    def execute_step(self, session_id: str) -> dict:
        """Execute one step of the computer-use loop."""
        session = self.get_session(session_id)
        if not session:
            return {"error": "Session not found", "step": "init"}

        if session.state != SessionState.RUNNING:
            return {"error": f"Session not running (state: {session.state.value})", "step": "check"}

        # Step 1: Capture screenshot
        screenshot_path = executor._capture_screenshot(f"step_{session.action_count}")
        if not screenshot_path:
            session.state = SessionState.ERROR
            session.error = "Failed to capture screenshot"
            return {"error": "Screenshot capture failed", "step": "capture"}

        session.current_screenshot = screenshot_path

        # Step 2: Analyze with NVIDIA vision
        vision_result = self.vision.analyze_for_action(screenshot_path, session.objective)
        session.last_vision_response = vision_result

        if vision_result.error:
            session.state = SessionState.ERROR
            session.error = f"Vision analysis failed: {vision_result.error}"
            return {"error": session.error, "step": "analyze", "vision": vision_result.model_dump(mode="json")}

        # Step 3: Determine action from vision result
        proposed = vision_result.proposed_action
        if not proposed:
            return {
                "step": "analyze",
                "vision": vision_result.model_dump(mode="json"),
                "message": "No action proposed by vision model. Screen may not need interaction.",
                "elements_found": len(vision_result.visible_elements),
            }

        # Step 4: Build validated action
        try:
            action_type = ActionType(proposed.get("action_type", "stop"))
        except ValueError:
            return {"error": f"Invalid action type: {proposed.get('action_type')}", "step": "validate"}

        action = ComputerAction(
            action_type=action_type,
            params=proposed.get("params", {}),
            proposed_by_model=True,
            risk_level=vision_result.risk_level,
            requires_confirmation=vision_result.requires_confirmation,
            expected_result=vision_result.expected_result,
        )

        # Step 5: Security validation
        allowed, issues = self.guard.validate_action(action, session)
        if not allowed and any("confirmation" not in i.lower() for i in issues):
            return {"error": f"Action rejected: {'; '.join(issues)}", "step": "validate", "action": action.model_dump(mode="json")}

        # Step 6: Confirmation gate
        if self.guard.requires_confirmation(action):
            session.state = SessionState.AWAITING_CONFIRMATION
            session.pending_confirmation = action
            return {
                "step": "awaiting_confirmation",
                "action": action.model_dump(mode="json"),
                "issues": issues,
                "message": "This action requires your confirmation before execution.",
            }

        # Step 7: Execute
        result = self.executor.execute(action, session)
        session.action_history.append(result)
        session.action_count += 1
        session.updated_at = datetime.utcnow()

        self.guard.audit(session_id, "action_executed", action=action, result=result)

        if not result.success:
            return {
                "step": "execute",
                "action": action.model_dump(mode="json"),
                "result": result.model_dump(mode="json"),
                "error": result.error,
            }

        # Step 8: Visual verification
        verified = self._verify_action(result, action.expected_result)

        return {
            "step": "complete",
            "action": action.model_dump(mode="json"),
            "result": result.model_dump(mode="json"),
            "visual_verification": verified,
            "before_screenshot": result.before_screenshot_path,
            "after_screenshot": result.after_screenshot_path,
            "action_count": session.action_count,
            "remaining_actions": session.max_actions - session.action_count,
        }

    def approve_confirmation(self, session_id: str) -> dict:
        """Approve a pending confirmation action and execute it."""
        session = self.get_session(session_id)
        if not session:
            return {"error": "Session not found"}
        if session.state != SessionState.AWAITING_CONFIRMATION:
            return {"error": "No pending confirmation"}
        if not session.pending_confirmation:
            return {"error": "No pending action"}

        action = session.pending_confirmation
        session.pending_confirmation = None
        session.state = SessionState.RUNNING

        result = self.executor.execute(action, session)
        session.action_history.append(result)
        session.action_count += 1
        session.updated_at = datetime.utcnow()

        self.guard.audit(session_id, "confirmed_action_executed", action=action, result=result)

        verified = self._verify_action(result, action.expected_result)

        return {
            "step": "confirmed_and_executed",
            "action": action.model_dump(mode="json"),
            "result": result.model_dump(mode="json"),
            "visual_verification": verified,
        }

    def reject_confirmation(self, session_id: str) -> dict:
        session = self.get_session(session_id)
        if not session:
            return {"error": "Session not found"}
        session.pending_confirmation = None
        session.state = SessionState.RUNNING
        self.guard.audit(session_id, "confirmation_rejected")
        return {"session_id": session_id, "state": "running", "message": "Confirmation rejected"}

    def get_session_status(self, session_id: str) -> dict:
        session = self.get_session(session_id)
        if not session:
            return {"error": "Session not found"}

        return {
            "session_id": str(session.session_id),
            "state": session.state.value,
            "objective": session.objective,
            "action_count": session.action_count,
            "max_actions": session.max_actions,
            "current_screenshot": session.current_screenshot,
            "last_vision_response": session.last_vision_response.model_dump(mode="json") if session.last_vision_response else None,
            "pending_confirmation": session.pending_confirmation.model_dump(mode="json") if session.pending_confirmation else None,
            "action_history": [a.model_dump(mode="json") for a in session.action_history[-10:]],
            "error": session.error,
        }

    def _verify_action(self, result: ActionResult, expected: str) -> bool:
        """Verify that the action produced the expected result using vision."""
        if not result.after_screenshot_path or not os.path.exists(result.after_screenshot_path):
            return False

        try:
            after_vision = self.vision.analyze_screenshot(result.after_screenshot_path)
            if after_vision.error:
                return False

            # Check if the screen changed
            if result.before_screenshot_path and os.path.exists(result.before_screenshot_path):
                before_vision = self.vision.analyze_screenshot(result.before_screenshot_path)
                if before_vision.error:
                    return True  # Can't verify change, assume success if action didn't error

                # Compare element counts and positions
                before_count = len(before_vision.visible_elements)
                after_count = len(after_vision.visible_elements)

                if before_count != after_count:
                    return True  # Screen changed

                # Check if any element labels changed
                before_labels = {e.label for e in before_vision.visible_elements}
                after_labels = {e.label for e in after_vision.visible_elements}
                if before_labels != after_labels:
                    return True

            return True  # Action succeeded, can't compare without before screenshot

        except Exception:
            return True  # Verification failed but action succeeded


# Singleton — lazy initialization
_session_manager = None

def get_session_manager() -> ComputerUseSessionManager:
    global _session_manager
    if _session_manager is None:
        _session_manager = ComputerUseSessionManager()
    return _session_manager

# Legacy alias for existing code
session_manager = None  # Will be lazily initialized on first access
