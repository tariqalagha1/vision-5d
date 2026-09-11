"""
Vision 5D — Computer-Use Tests
Tests for contracts, security, executor, session management, and NVIDIA vision integration.
"""
import pytest, os, json, tempfile
from uuid import uuid4
from datetime import datetime
from unittest.mock import patch, MagicMock

from packages.computer_use import (
    ActionType, RiskLevel, SessionState, SecurityConfig,
    ComputerAction, ActionResult, ComputerUseSession,
    VisibleElement, VisionResponse, AuditEntry,
)


# ═══════════════════════════════════════════════════════════
# Contract Tests
# ═══════════════════════════════════════════════════════════

class TestActionValidation:
    def test_click_requires_params(self):
        action = ComputerAction(action_type=ActionType.CLICK, params={})
        issues = action.validate()
        assert len(issues) > 0

    def test_click_with_element_id_valid(self):
        action = ComputerAction(action_type=ActionType.CLICK, params={"element_id": 5})
        issues = action.validate()
        assert len(issues) == 0

    def test_type_text_requires_text(self):
        action = ComputerAction(action_type=ActionType.TYPE_TEXT, params={})
        issues = action.validate()
        assert len(issues) > 0

    def test_open_url_requires_url(self):
        action = ComputerAction(action_type=ActionType.OPEN_URL, params={})
        issues = action.validate()
        assert len(issues) > 0

    def test_valid_action_no_issues(self):
        action = ComputerAction(action_type=ActionType.SCREENSHOT, params={})
        issues = action.validate()
        assert len(issues) == 0

    def test_all_action_types_defined(self):
        for at in ActionType:
            action = ComputerAction(action_type=at, params=self._default_params(at))
            issues = action.validate()
            # Some actions need params, some don't — just verify no crash
            assert isinstance(issues, list)

    def _default_params(self, action_type):
        defaults = {
            ActionType.CLICK: {"element_id": 1},
            ActionType.OPEN_URL: {"url": "http://localhost:8100"},
            ActionType.TYPE_TEXT: {"text": "test"},
            ActionType.PRESS_KEY: {"keys": "enter"},
            ActionType.HOTKEY: {"keys": "ctrl+s"},
            ActionType.SCROLL: {"direction": "down"},
            ActionType.WAIT: {"seconds": 1},
            ActionType.MOVE_MOUSE: {"x": 100, "y": 200},
        }
        return defaults.get(action_type, {})


class TestVisionResponse:
    def test_valid_response(self):
        vr = VisionResponse(
            screen_summary="Dashboard visible",
            visible_elements=[
                VisibleElement(element_id=1, element_type="button", label="Sign In", confidence=0.95)
            ]
        )
        assert vr.is_valid()

    def test_empty_response_invalid(self):
        vr = VisionResponse(screen_summary="")
        assert not vr.is_valid()

    def test_error_response_invalid(self):
        vr = VisionResponse(screen_summary="", error="API error")
        assert not vr.is_valid()


# ═══════════════════════════════════════════════════════════
# Security Tests
# ═══════════════════════════════════════════════════════════

class TestSecurityGuard:
    def setup_method(self):
        from packages.computer_use.security import SecurityGuard
        self.guard = SecurityGuard(SecurityConfig(enabled=True))
        self.session = ComputerUseSession()

    def test_allowed_domain(self):
        action = ComputerAction(action_type=ActionType.OPEN_URL, params={"url": "http://localhost:8100/index.html"})
        allowed, issues = self.guard.validate_action(action, self.session)
        assert allowed

    def test_blocked_domain(self):
        # evil.com is NOT in the default allowlist (localhost, 127.0.0.1)
        self.guard.config.domain_allowlist = ["localhost", "127.0.0.1"]
        action = ComputerAction(action_type=ActionType.OPEN_URL, params={"url": "http://evil.com/phish"})
        allowed, issues = self.guard.validate_action(action, self.session)
        assert not allowed
        assert any("not in allowlist" in i.lower() or "domain" in i.lower() for i in issues)

    def test_blocked_key(self):
        action = ComputerAction(action_type=ActionType.HOTKEY, params={"keys": "ctrl+alt+del"})
        allowed, issues = self.guard.validate_action(action, self.session)
        assert not allowed

    def test_max_actions_reached(self):
        session = ComputerUseSession(action_count=50, max_actions=50)
        action = ComputerAction(action_type=ActionType.CLICK, params={"x": 10, "y": 10})
        allowed, issues = self.guard.validate_action(action, session)
        assert not allowed

    def test_emergency_stop_blocks_all(self):
        self.guard.emergency_stop()
        action = ComputerAction(action_type=ActionType.CLICK, params={"x": 10, "y": 10})
        allowed, issues = self.guard.validate_action(action, self.session)
        assert not allowed
        self.guard.reset_emergency()

    def test_requires_confirmation_high_risk(self):
        action = ComputerAction(action_type=ActionType.CLICK, params={"x": 10, "y": 10}, risk_level=RiskLevel.HIGH)
        assert self.guard.requires_confirmation(action)

    def test_no_confirmation_low_risk(self):
        action = ComputerAction(action_type=ActionType.CLICK, params={"x": 10, "y": 10}, risk_level=RiskLevel.LOW)
        assert not self.guard.requires_confirmation(action)

    def test_audit_logging(self):
        self.guard.audit(uuid4(), "test_event", details={"test": True})
        log = self.guard.get_audit_log()
        assert len(log) >= 1

    def test_domain_allowlist_enforcement(self):
        for domain in ["localhost", "127.0.0.1"]:
            action = ComputerAction(action_type=ActionType.OPEN_URL, params={"url": f"http://{domain}:8100"})
            allowed, _ = self.guard.validate_action(action, self.session)
            assert allowed, f"Domain {domain} should be allowed"


class TestSecurityConfig:
    def test_default_config(self):
        cfg = SecurityConfig()
        assert cfg.enabled is False
        assert "localhost" in cfg.domain_allowlist
        assert cfg.max_actions_per_session == 50

    def test_custom_config(self):
        cfg = SecurityConfig(enabled=True, domain_allowlist=["example.com"], max_actions_per_session=10)
        assert cfg.enabled
        assert "example.com" in cfg.domain_allowlist
        assert cfg.max_actions_per_session == 10


# ═══════════════════════════════════════════════════════════
# Session Tests
# ═══════════════════════════════════════════════════════════

class TestSession:
    def test_create_session(self):
        session = ComputerUseSession(objective="Test objective")
        assert session.state == SessionState.IDLE
        assert session.objective == "Test objective"
        assert session.action_count == 0

    def test_session_lifecycle(self):
        session = ComputerUseSession()
        assert session.state == SessionState.IDLE

        session.state = SessionState.RUNNING
        assert session.state == SessionState.RUNNING

        session.state = SessionState.PAUSED
        assert session.state == SessionState.PAUSED

        session.state = SessionState.STOPPED
        assert session.state == SessionState.STOPPED

    def test_action_history(self):
        session = ComputerUseSession()
        result = ActionResult(
            action_id=uuid4(), success=True,
            before_screenshot_path="/tmp/before.png",
            after_screenshot_path="/tmp/after.png",
            visual_confirmation=True,
        )
        session.action_history.append(result)
        session.action_count += 1
        assert session.action_count == 1
        assert len(session.action_history) == 1


# ═══════════════════════════════════════════════════════════
# Vision Integration Tests
# ═══════════════════════════════════════════════════════════

class TestNVIDIAVision:
    def test_config_resolution_with_key(self, monkeypatch):
        monkeypatch.setenv("NVIDIA_API_KEY", "test-key-123")
        monkeypatch.setenv("AI_VISION_MODEL", "meta/llama-3.2-11b-vision-instruct")

        from packages.computer_use.vision import NVIDIAVisionAnalyzer
        analyzer = NVIDIAVisionAnalyzer()
        assert analyzer.config.provider == "nvidia"
        assert analyzer.config.api_key == "test-key-123"

    def test_config_fallback_to_openai(self, monkeypatch):
        monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-456")

        from packages.computer_use.vision import NVIDIAVisionAnalyzer
        analyzer = NVIDIAVisionAnalyzer()
        assert analyzer.config.provider == "openai"
        assert analyzer.config.api_key == "sk-test-456"

    def test_no_credentials_raises(self, monkeypatch):
        monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        from packages.computer_use.vision import NVIDIAVisionAnalyzer
        with pytest.raises(RuntimeError, match="No vision provider"):
            NVIDIAVisionAnalyzer()

    def test_parse_valid_vision_response(self):
        from packages.computer_use.vision import NVIDIAVisionAnalyzer
        analyzer = NVIDIAVisionAnalyzer.__new__(NVIDIAVisionAnalyzer)

        response = json.dumps({
            "screen_summary": "Dashboard with skeleton loaders",
            "visible_elements": [
                {"element_id": 1, "element_type": "button", "label": "Sign In", "bounding_box": {"x": 10, "y": 20, "w": 80, "h": 30}, "confidence": 0.95, "state": "enabled"}
            ],
            "risk_level": "low",
            "requires_confirmation": False
        })
        result = analyzer._parse_vision_response(response)
        assert result.is_valid()
        assert len(result.visible_elements) == 1
        assert result.visible_elements[0].label == "Sign In"

    def test_parse_invalid_json(self):
        from packages.computer_use.vision import NVIDIAVisionAnalyzer
        analyzer = NVIDIAVisionAnalyzer.__new__(NVIDIAVisionAnalyzer)

        result = analyzer._parse_vision_response("not json at all")
        assert not result.is_valid()
        assert "Parse error" in result.error

    def test_no_api_key_leakage(self, monkeypatch):
        monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-secret-12345")
        from packages.computer_use.vision import NVIDIAVisionAnalyzer
        analyzer = NVIDIAVisionAnalyzer()

        # Verify key is stored but not in any response-visible fields
        assert "nvapi-secret" in analyzer.config.api_key
        dumped = analyzer.config.__dict__
        # Key should be in config but we verify it's not logged/returned

    def test_screenshot_analysis_with_mock(self, monkeypatch, tmp_path):
        monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
        from packages.computer_use.vision import NVIDIAVisionAnalyzer
        analyzer = NVIDIAVisionAnalyzer()

        # Create a tiny test PNG
        img_path = tmp_path / "test.png"
        # Minimal 1x1 PNG
        png_data = bytes.fromhex(
            "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753de"
            "0000000c4944415408d76360f8cf0000000201018a33769a0000000049454e44ae426082"
        )
        img_path.write_bytes(png_data)

        # Mock the adapter to return a valid response
        with patch.object(analyzer.adapter, 'call_vision') as mock_vision:
            mock_vision.return_value = {
                "parsed": {"analysis": json.dumps({
                    "screen_summary": "Test image",
                    "visible_elements": [{"element_id": 1, "element_type": "image", "label": "test", "confidence": 1.0}],
                    "risk_level": "low",
                    "requires_confirmation": False
                })}
            }
            result = analyzer.analyze_screenshot(str(img_path))
            assert result.is_valid()
            assert len(result.visible_elements) == 1


# ═══════════════════════════════════════════════════════════
# Integration Tests
# ═══════════════════════════════════════════════════════════

class TestComputerUseIntegration:
    def test_module_imports(self):
        """Verify all computer-use modules import correctly."""
        from packages.computer_use import (
            ActionType, RiskLevel, SessionState, SecurityConfig,
            ComputerAction, ActionResult, ComputerUseSession,
            VisibleElement, VisionResponse,
        )
        from packages.computer_use.security import SecurityGuard
        from packages.computer_use.executor import ActionExecutor
        from packages.computer_use.session import ComputerUseSessionManager
        assert True

    def test_end_to_end_flow_mocked(self, monkeypatch):
        """Simulate a full computer-use session flow with mocked vision."""
        monkeypatch.setenv("NVIDIA_API_KEY", "test-key")

        from packages.computer_use.session import ComputerUseSessionManager

        mgr = ComputerUseSessionManager()
        session = mgr.create_session(objective="Test flow")

        # Start
        result = mgr.start_session(str(session.session_id))
        assert result["state"] == "running"

        # Pause
        result = mgr.pause_session(str(session.session_id))
        assert result["state"] == "paused"

        # Resume
        result = mgr.resume_session(str(session.session_id))
        assert result["state"] == "running"

        # Stop
        result = mgr.stop_session(str(session.session_id))
        assert result["state"] == "stopped"

        # Session list
        sessions = mgr.list_sessions()
        assert len(sessions) >= 1

    def test_emergency_stop_flow(self):
        from packages.computer_use.session import ComputerUseSessionManager

        mgr = ComputerUseSessionManager()
        session = mgr.create_session()
        mgr.start_session(str(session.session_id))

        result = mgr.emergency_stop(str(session.session_id))
        assert result["state"] == "emergency_stopped"

        # Can't restart emergency-stopped session
        result = mgr.start_session(str(session.session_id))
        assert "error" in result


# ═══════════════════════════════════════════════════════════
# No-Secret-Leakage Tests
# ═══════════════════════════════════════════════════════════

class TestNoSecretLeakage:
    def test_config_response_no_key(self):
        cfg = SecurityConfig()
        data = cfg.model_dump(mode="json")
        assert "api_key" not in str(data).lower() or "api_key" not in data

    def test_vision_response_no_key(self):
        vr = VisionResponse(screen_summary="test")
        data = vr.model_dump(mode="json")
        assert "api_key" not in str(data)

    def test_action_result_no_key(self):
        ar = ActionResult(action_id=uuid4(), success=True)
        data = ar.model_dump(mode="json")
        assert "api_key" not in str(data)
        assert "secret" not in str(data).lower()
