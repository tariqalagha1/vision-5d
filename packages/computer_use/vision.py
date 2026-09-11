"""
Vision 5D — Computer-Use NVIDIA Vision Integration
Sends screenshots to NVIDIA vision model for UI element detection.
Uses the configured NVIDIA provider from Vision 5D AI settings.
API key NEVER leaves the server.
"""
import os, json, base64, time, structlog
from typing import Optional
from uuid import uuid4

from packages.ai.provider_client import ProviderAdapter, ProviderConfig
from packages.computer_use import (
    VisionResponse, VisibleElement, RiskLevel,
    ActionType, ComputerAction,
)

logger = structlog.get_logger()


class NVIDIAVisionAnalyzer:
    """Analyzes screenshots using NVIDIA multimodal vision API for UI understanding."""

    SCREEN_ANALYSIS_PROMPT = """You are a computer-use vision agent for Vision 5D. Analyze this screenshot of a computer desktop or browser window.

Return ONLY a JSON object with this EXACT schema:
{
  "screen_summary": "Brief description of what is visible on screen",
  "visible_elements": [
    {
      "element_id": 1,
      "element_type": "button|text_field|link|dropdown|checkbox|image|label|menu|tab|dialog|spinner|skeleton|error|other",
      "label": "Human-readable label or text content",
      "bounding_box": {"x": 0, "y": 0, "w": 100, "h": 40},
      "confidence": 0.95,
      "state": "enabled|disabled|selected|highlighted|loading",
      "text_content": "Any visible text on the element"
    }
  ],
  "proposed_action": null,
  "expected_result": "",
  "risk_level": "none|low|medium|high|critical",
  "requires_confirmation": false
}

RULES:
1. Number elements from 1, left-to-right, top-to-bottom.
2. bounding_box uses pixel coordinates relative to the screenshot (x=left, y=top, w=width, h=height).
3. confidence: 0.0-1.0 based on how clearly the element is identifiable.
4. If the screen shows skeleton loaders, spinners, or loading states, note this in screen_summary and mark those elements with state "loading".
5. If the screen shows errors, dialogs, or blank states, describe them accurately.
6. If there are navigation elements (sidebar, tabs, menus), list them.
7. If there is a login/sign-in prompt, identify the button.
8. Do NOT propose actions — just describe what you see.
9. Begin your response with { and end with }. No other text."""

    def __init__(self, config: Optional[ProviderConfig] = None):
        if config is None:
            config = self._resolve_nvidia_config()
        self.config = config
        self.adapter = ProviderAdapter(config)
        logger.info("nvidia_vision_initialized",
                    provider=self.config.provider,
                    model=self.config.model)

    def _resolve_nvidia_config(self) -> ProviderConfig:
        """Resolve NVIDIA config from environment or Vision 5D settings.
        NVIDIA_API_KEY is required for vision analysis."""
        nvidia_key = os.getenv("NVIDIA_API_KEY", "")
        if nvidia_key:
            return ProviderConfig(
                provider="nvidia",
                model=os.getenv("AI_VISION_MODEL", os.getenv("AI_MODEL", "meta/llama-3.2-11b-vision-instruct")),
                api_key=nvidia_key,
                base_url=os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
                timeout=60,
                max_retries=2,
            )

        # Fallback: try other vision-capable providers
        openai_key = os.getenv("OPENAI_API_KEY", "")
        if openai_key:
            logger.warning("nvidia_key_missing_falling_back_to_openai")
            return ProviderConfig(
                provider="openai",
                model=os.getenv("AI_VISION_MODEL", "gpt-4o"),
                api_key=openai_key,
                base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                timeout=60,
                max_retries=2,
            )

        raise RuntimeError(
            "No vision provider configured. Set NVIDIA_API_KEY for computer-use vision analysis."
        )

    def analyze_screenshot(self, image_path: str) -> VisionResponse:
        """Send a screenshot to NVIDIA vision API and return structured analysis."""
        t0 = time.time()

        try:
            # Read and encode image
            with open(image_path, "rb") as f:
                image_bytes = f.read()

            # Detect image format from extension
            ext = os.path.splitext(image_path)[1].lower()
            mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
            mime_type = mime_map.get(ext, "image/png")

            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            data_url = f"data:{mime_type};base64,{image_b64}"

            # Build vision request
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self.SCREEN_ANALYSIS_PROMPT},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ]

            response = self.adapter.call_vision(
                image_path=image_path,
                prompt=self.SCREEN_ANALYSIS_PROMPT,
            )

            latency_ms = (time.time() - t0) * 1000

            # Extract content from response (varies by provider adapter)
            parsed = response.get("parsed", {})
            if isinstance(parsed, dict):
                content = parsed.get("analysis", parsed.get("content", "")) or json.dumps(parsed)
            elif isinstance(parsed, str):
                content = parsed
            else:
                content = str(parsed)
            result = self._parse_vision_response(content)

            result.model = self.config.model
            result.latency_ms = latency_ms
            result.raw_response = response

            logger.info("nvidia_vision_analysis_complete",
                        elements=len(result.visible_elements),
                        latency_ms=latency_ms,
                        model=self.config.model)

            return result

        except Exception as e:
            latency_ms = (time.time() - t0) * 1000
            logger.error("nvidia_vision_analysis_failed", error=str(e))
            return VisionResponse(
                screen_summary=f"Vision analysis failed: {str(e)}",
                error=str(e),
                latency_ms=latency_ms,
                model=self.config.model,
            )

    def _parse_vision_response(self, content: str) -> VisionResponse:
        """Parse the JSON response from NVIDIA vision model."""
        try:
            # Extract JSON from response (may have markdown fences)
            json_str = content.strip()
            if json_str.startswith("```"):
                lines = json_str.split("\n")
                json_str = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
                json_str = json_str.strip()

            # Try direct parse first
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError:
                # NVIDIA model may return escaped JSON: {\"key\": \"value\"}
                # Try unescaping backslash-escaped quotes and backslashes
                unescaped = json_str.replace('\\"', '"').replace('\\\\', '\\')
                data = json.loads(unescaped)

            elements = []
            for el_data in data.get("visible_elements", []):
                elements.append(VisibleElement(
                    element_id=el_data.get("element_id", 0),
                    element_type=el_data.get("element_type", "other"),
                    label=el_data.get("label", ""),
                    bounding_box=el_data.get("bounding_box", {"x": 0, "y": 0, "w": 0, "h": 0}),
                    confidence=float(el_data.get("confidence", 0.0)),
                    state=el_data.get("state", ""),
                    text_content=el_data.get("text_content", ""),
                ))

            risk = data.get("risk_level", "low")
            try:
                risk_level = RiskLevel(risk)
            except ValueError:
                risk_level = RiskLevel.LOW

            return VisionResponse(
                screen_summary=data.get("screen_summary", ""),
                visible_elements=elements,
                proposed_action=data.get("proposed_action"),
                expected_result=data.get("expected_result", ""),
                risk_level=risk_level,
                requires_confirmation=data.get("requires_confirmation", False),
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning("vision_response_parse_failed", error=str(e), content=content[:200])
            return VisionResponse(
                screen_summary=f"Failed to parse vision response: {str(e)}",
                error=f"Parse error: {str(e)}",
            )

    def analyze_for_action(self, image_path: str, objective: str) -> VisionResponse:
        """Analyze screenshot with objective context to determine next action."""
        # For action-oriented analysis, use a different prompt
        action_prompt = f"""You are a computer-use agent. Your objective is: {objective}

Analyze this screenshot and determine the NEXT action to take. Return ONLY a JSON object:

{{
  "screen_summary": "What is visible",
  "visible_elements": [...same format as before...],
  "proposed_action": {{
    "action_type": "click|double_click|right_click|type_text|press_key|hotkey|scroll|wait|open_url|stop",
    "target_element_id": 1,
    "params": {{}}
  }},
  "expected_result": "What should happen after this action",
  "risk_level": "none|low|medium|high|critical",
  "requires_confirmation": false
}}

Begin with {{ and end with }}. No other text."""

        t0 = time.time()
        try:
            with open(image_path, "rb") as f:
                image_bytes = f.read()

            ext = os.path.splitext(image_path)[1].lower()
            mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
            mime_type = mime_map.get(ext, "image/png")

            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            data_url = f"data:{mime_type};base64,{image_b64}"

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": action_prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ]

            response = self.adapter.call_vision(
                image_path=image_path,
                prompt=action_prompt,
            )

            latency_ms = (time.time() - t0) * 1000
            parsed = response.get("parsed", {})
            if isinstance(parsed, dict):
                content = parsed.get("analysis", parsed.get("content", "")) or json.dumps(parsed)
            elif isinstance(parsed, str):
                content = parsed
            else:
                content = str(parsed)
            result = self._parse_vision_response(content)
            result.model = self.config.model
            result.latency_ms = latency_ms
            result.raw_response = response

            return result

        except Exception as e:
            latency_ms = (time.time() - t0) * 1000
            return VisionResponse(
                screen_summary=f"Action analysis failed: {str(e)}",
                error=str(e),
                latency_ms=latency_ms,
            )


# Singleton — lazy initialization, only resolves config when first used
_vision_analyzer = None

def get_vision_analyzer() -> NVIDIAVisionAnalyzer:
    global _vision_analyzer
    if _vision_analyzer is None:
        _vision_analyzer = NVIDIAVisionAnalyzer()
    return _vision_analyzer
