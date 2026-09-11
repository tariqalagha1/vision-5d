"""
Vision 5D — Computer-Use Deterministic Action Executor
Executes validated actions. Does NOT run raw model-generated code.
Uses cua-driver CLI for desktop control (Windows-only for local testing).
"""
import os, time, subprocess, json, hashlib
from datetime import datetime
from typing import Optional
import structlog

from packages.computer_use import (
    ComputerAction, ActionResult, ActionType, RiskLevel,
    ComputerUseSession,
)

logger = structlog.get_logger()


class ActionExecutor:
    """Deterministic executor for computer-use actions.
    All actions are validated BEFORE execution by SecurityGuard.
    Model output is parsed into structured ComputerAction objects.
    No raw model-generated code is ever executed."""

    def __init__(self, evidence_dir: str = ""):
        self.evidence_dir = evidence_dir or os.path.join(
            os.path.dirname(__file__), "..", "..", "evidence",
            "V5D-LOCAL-EXTERNAL-SERVICES-READINESS-001", "computer_use", "screenshots"
        )
        os.makedirs(self.evidence_dir, exist_ok=True)

    def execute(self, action: ComputerAction, session: ComputerUseSession) -> ActionResult:
        """Execute a validated action and return the result."""
        t0 = time.time()
        action_id = action.action_id

        # Capture before screenshot
        before_path = self._capture_screenshot(f"before_{action_id}")

        try:
            result_data = {}

            if action.action_type == ActionType.SCREENSHOT:
                result_data = {"screenshot_path": before_path}

            elif action.action_type == ActionType.OPEN_URL:
                url = action.params["url"]
                result_data = self._execute_open_url(url)

            elif action.action_type == ActionType.CLICK:
                result_data = self._execute_click(action.params)

            elif action.action_type == ActionType.DOUBLE_CLICK:
                result_data = self._execute_double_click(action.params)

            elif action.action_type == ActionType.RIGHT_CLICK:
                result_data = self._execute_right_click(action.params)

            elif action.action_type == ActionType.TYPE_TEXT:
                result_data = self._execute_type_text(action.params)

            elif action.action_type == ActionType.PRESS_KEY:
                result_data = self._execute_press_key(action.params)

            elif action.action_type == ActionType.HOTKEY:
                result_data = self._execute_hotkey(action.params)

            elif action.action_type == ActionType.SCROLL:
                result_data = self._execute_scroll(action.params)

            elif action.action_type == ActionType.WAIT:
                seconds = float(action.params.get("seconds", 1))
                time.sleep(min(seconds, 30))
                result_data = {"waited_seconds": seconds}

            elif action.action_type == ActionType.STOP:
                result_data = {"stopped": True}

            else:
                return ActionResult(
                    action_id=action_id,
                    success=False,
                    before_screenshot_path=before_path,
                    error=f"Unsupported action type: {action.action_type}",
                )

            # Capture after screenshot
            after_path = self._capture_screenshot(f"after_{action_id}")

            duration_ms = (time.time() - t0) * 1000

            return ActionResult(
                action_id=action_id,
                success=True,
                before_screenshot_path=before_path,
                after_screenshot_path=after_path,
                visual_confirmation=False,  # Set to True after vision verification
                duration_ms=duration_ms,
                details=result_data,
            )

        except Exception as e:
            duration_ms = (time.time() - t0) * 1000
            after_path = self._capture_screenshot(f"error_{action_id}")
            logger.error("action_execution_failed", action_id=str(action_id), error=str(e))

            return ActionResult(
                action_id=action_id,
                success=False,
                before_screenshot_path=before_path,
                after_screenshot_path=after_path,
                error=str(e),
                duration_ms=duration_ms,
            )

    def _capture_screenshot(self, label: str) -> str:
        """Capture a screenshot using cua-driver or fallback."""
        filename = f"{label}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}.png"
        filepath = os.path.join(self.evidence_dir, filename)

        try:
            # Use cua-driver if available
            result = subprocess.run(
                ["cua-driver", "screenshot", "--output", filepath],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0 and os.path.exists(filepath):
                return filepath
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Fallback: use Python MSS or PIL
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab()
            img.save(filepath, "PNG")
            return filepath
        except ImportError:
            pass

        logger.warning("screenshot_capture_failed", label=label)
        return ""

    # ── Action Implementations ──

    def _execute_open_url(self, params: dict) -> dict:
        url = params["url"]
        browser = params.get("browser", "chrome")
        try:
            subprocess.run(["cmd", "/c", "start", browser, url],
                         capture_output=True, timeout=10)
            return {"url": url, "browser": browser}
        except Exception as e:
            return {"url": url, "error": str(e)}

    def _execute_click(self, params: dict) -> dict:
        x = params.get("x", 0)
        y = params.get("y", 0)
        element_id = params.get("element_id")

        if element_id:
            try:
                result = subprocess.run(
                    ["cua-driver", "click", "--element", str(element_id)],
                    capture_output=True, text=True, timeout=10,
                )
                return {"element_id": element_id, "output": result.stdout[:200]}
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass

        try:
            subprocess.run(
                ["cua-driver", "click", "--x", str(x), "--y", str(y)],
                capture_output=True, text=True, timeout=10,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        return {"x": x, "y": y, "element_id": element_id}

    def _execute_double_click(self, params: dict) -> dict:
        return self._execute_click({**params, "double": True})

    def _execute_right_click(self, params: dict) -> dict:
        return self._execute_click({**params, "button": "right"})

    def _execute_type_text(self, params: dict) -> dict:
        text = params["text"]
        try:
            subprocess.run(
                ["cua-driver", "type", "--text", text],
                capture_output=True, text=True, timeout=10,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return {"text": text, "length": len(text)}

    def _execute_press_key(self, params: dict) -> dict:
        keys = params["keys"]
        try:
            subprocess.run(
                ["cua-driver", "key", "--keys", keys],
                capture_output=True, text=True, timeout=10,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return {"keys": keys}

    def _execute_hotkey(self, params: dict) -> dict:
        return self._execute_press_key(params)

    def _execute_scroll(self, params: dict) -> dict:
        direction = params.get("direction", "down")
        amount = params.get("amount", 3)
        try:
            subprocess.run(
                ["cua-driver", "scroll", "--direction", str(direction), "--amount", str(amount)],
                capture_output=True, text=True, timeout=10,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return {"direction": direction, "amount": amount}


# Singleton
executor = ActionExecutor()
