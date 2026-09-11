"""
Vision 5D — Real AI Provider Adapter
LLM API client for OpenAI, Anthropic, DeepSeek with structured output.
Loads credentials from environment, supports timeout/retry/token tracking.
"""
import os, json, time, structlog, hashlib
from uuid import uuid4
from typing import Optional
from dataclasses import dataclass, field

logger = structlog.get_logger()


@dataclass
class ProviderConfig:
    """Provider configuration from environment."""
    provider: str = "simulation"      # openai, anthropic, deepseek, gemini, simulation
    model: str = ""
    api_key: str = ""
    base_url: str = ""
    timeout: int = 60
    max_retries: int = 2
    temperature: float = 0.7
    max_tokens: int = 4096
    simulation_allowed: bool = True  # False in production

    @classmethod
    def from_env(cls) -> "ProviderConfig":
        provider = os.getenv("AI_PROVIDER", "simulation").lower()
        config = cls(provider=provider)

        if provider == "openai":
            config.api_key = os.getenv("OPENAI_API_KEY", "")
            config.model = os.getenv("AI_MODEL", "gpt-4o")
            config.base_url = os.getenv("AI_BASE_URL", "https://api.openai.com/v1")
        elif provider == "anthropic":
            config.api_key = os.getenv("ANTHROPIC_API_KEY", "")
            config.model = os.getenv("AI_MODEL", "claude-sonnet-4-20250514")
            config.base_url = os.getenv("AI_BASE_URL", "https://api.anthropic.com/v1")
        elif provider == "deepseek":
            config.api_key = os.getenv("DEEPSEEK_API_KEY", "")
            config.model = os.getenv("AI_MODEL", "deepseek-chat")
            config.base_url = os.getenv("AI_BASE_URL", "https://api.deepseek.com/v1")
        elif provider == "gemini":
            config.api_key = os.getenv("GEMINI_API_KEY", "")
            config.model = os.getenv("AI_MODEL", "gemini-2.0-flash")
            config.base_url = os.getenv("AI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")
        elif provider == "nvidia":
            config.api_key = os.getenv("NVIDIA_API_KEY", "")
            config.model = os.getenv("AI_MODEL", "deepseek-ai/deepseek-v4-pro")
            config.base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
        elif provider == "simulation":
            config.model = "v5d-simulation-6.0"
        else:
            config.model = ""

        config.timeout = int(os.getenv("AI_REQUEST_TIMEOUT", "60"))
        config.max_retries = int(os.getenv("AI_MAX_RETRIES", "2"))
        config.simulation_allowed = os.getenv("AI_SIMULATION_ALLOWED", "true").lower() != "false"
        return config

    def validate(self) -> list[str]:
        """Validate configuration. Returns list of issues."""
        issues = []
        if self.provider == "simulation":
            if not self.simulation_allowed:
                issues.append("Simulation provider disabled in production")
            return issues

        if not self.api_key:
            issues.append(f"No API key for provider '{self.provider}'. Set {self.provider.upper()}_API_KEY")
        if not self.model:
            issues.append(f"No model configured for provider '{self.provider}'")

        known = {"openai", "anthropic", "deepseek", "gemini", "nvidia", "simulation"}
        if self.provider not in known:
            issues.append(f"Unknown provider: '{self.provider}'. Known: {', '.join(sorted(known))}")
        return issues

    def is_configured(self) -> bool:
        return self.provider != "simulation" and bool(self.api_key) and bool(self.model)


class ProviderAdapter:
    """LLM API client with structured request/response handling."""

    def __init__(self, config: Optional[ProviderConfig] = None):
        self.config = config or ProviderConfig.from_env()
        self._client = None  # Lazy httpx client

    def call(self, system_prompt: str, user_prompt: str,
             response_schema: dict = None) -> dict:
        """Call the configured provider and return structured result."""
        if self.config.provider == "simulation":
            return self._simulate(system_prompt, user_prompt)

        if not self.config.is_configured():
            raise ProviderError(
                f"Provider '{self.config.provider}' not configured",
                provider=self.config.provider,
                code="PROVIDER_NOT_CONFIGURED",
            )

        try:
            import httpx
            result = None
            last_error = None
            attempt = 0

            for attempt in range(self.config.max_retries + 1):
                try:
                    t0 = time.time()
                    if self.config.provider in ("openai", "deepseek", "nvidia"):
                        result = self._call_openai_compatible(system_prompt, user_prompt, response_schema)
                    elif self.config.provider == "anthropic":
                        result = self._call_anthropic(system_prompt, user_prompt, response_schema)
                    elif self.config.provider == "gemini":
                        result = self._call_gemini(system_prompt, user_prompt, response_schema)

                    latency = (time.time() - t0) * 1000
                    result["latency_ms"] = latency
                    result["attempt"] = attempt + 1
                    result["provider"] = self.config.provider
                    result["model"] = self.config.model
                    break
                except Exception as e:
                    last_error = e
                    if attempt < self.config.max_retries:
                        wait = 2 ** attempt
                        logger.warn("provider_retry", attempt=attempt+1, wait=wait, error=str(e)[:100])
                        time.sleep(wait)

            if result is None and last_error:
                raise last_error

            return result or {}

        except ImportError:
            raise ProviderError(
                "httpx not installed. Install with: pip install httpx",
                provider=self.config.provider, code="DEPENDENCY_MISSING",
            )

    def _call_openai_compatible(self, system: str, user: str, schema: dict = None) -> dict:
        """Call OpenAI or DeepSeek (compatible API)."""
        import httpx
        url = f"{self.config.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
        if schema:
            body["response_format"] = {"type": "json_object"}

        with httpx.Client(timeout=self.config.timeout) as client:
            resp = client.post(url, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        return self._parse_openai_response(data)

    def _call_anthropic(self, system: str, user: str, schema: dict = None) -> dict:
        """Call Anthropic Claude API."""
        import httpx
        url = f"{self.config.base_url.rstrip('/')}/messages"
        headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        if schema:
            user = user + "\n\nRespond with valid JSON matching this schema. Output ONLY the JSON object, no other text:\n" + json.dumps(schema, indent=2)
            body["messages"][0]["content"] = user

        with httpx.Client(timeout=self.config.timeout) as client:
            resp = client.post(url, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        return self._parse_anthropic_response(data)

    def _parse_openai_response(self, data: dict) -> dict:
        """Parse OpenAI-compatible response."""
        choice = data.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        usage = data.get("usage", {})

        parsed = {}
        try:
            parsed = json.loads(content) if isinstance(content, str) else content
        except json.JSONDecodeError:
            parsed = {"raw_response": str(content)[:1000]}

        return {
            "provider_request_id": data.get("id", ""),
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "finish_reason": choice.get("finish_reason", ""),
            "parsed": parsed,
            "raw_size": len(json.dumps(data)),
        }

    def _parse_anthropic_response(self, data: dict) -> dict:
        """Parse Anthropic response."""
        content_block = data.get("content", [{}])[0]
        text = content_block.get("text", "")
        usage = data.get("usage", {})

        parsed = {}
        try:
            # Extract JSON from text (Claude may wrap in markdown)
            if "```json" in text:
                start = text.index("```json") + 7
                end = text.index("```", start)
                parsed = json.loads(text[start:end])
            elif "{" in text:
                start = text.index("{")
                end = text.rindex("}") + 1
                parsed = json.loads(text[start:end])
            else:
                parsed = {"raw_response": text[:1000]}
        except (json.JSONDecodeError, ValueError):
            parsed = {"raw_response": str(text)[:1000]}

        return {
            "provider_request_id": data.get("id", ""),
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "total_tokens": (usage.get("input_tokens", 0) + usage.get("output_tokens", 0)),
            "finish_reason": data.get("stop_reason", ""),
            "parsed": parsed,
            "raw_size": len(json.dumps(data)),
        }

    def _simulate(self, system: str, user: str) -> dict:
        """Simulation provider (deterministic, no network)."""
        return {
            "provider_request_id": "sim-" + uuid4().hex[:12],
            "input_tokens": len(user.split()) * 2,
            "output_tokens": 500,
            "total_tokens": len(user.split()) * 2 + 500,
            "finish_reason": "stop",
            "parsed": {"simulated": True, "note": "Simulation provider — no LLM call made"},
            "raw_size": 0,
            "latency_ms": 10,
            "attempt": 1,
            "provider": "simulation",
            "model": "v5d-simulation-6.0",
        }

    def _call_gemini(self, system: str, user: str, schema: dict = None) -> dict:
        """Call Google Gemini API (OpenAI-compatible via vertex or direct)."""
        import httpx, base64
        url = f"{self.config.base_url.rstrip('/')}/models/{self.config.model}:generateContent?key={self.config.api_key}"
        headers = {"Content-Type": "application/json"}
        
        # Build contents with system instruction as first user message
        parts = []
        if system:
            parts.append({"text": f"[System Instruction]: {system}"})
        parts.append({"text": user})
        
        body = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "temperature": self.config.temperature,
                "maxOutputTokens": self.config.max_tokens,
            }
        }
        
        with httpx.Client(timeout=self.config.timeout) as client:
            resp = client.post(url, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        
        # Parse Gemini response
        candidates = data.get("candidates", [])
        if not candidates:
            raise ProviderError("Gemini returned no candidates", provider="gemini", code="EMPTY_RESPONSE")
        
        content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        usage = data.get("usageMetadata", {})
        
        parsed = {}
        try:
            # Extract JSON from response
            if "```json" in content:
                start = content.index("```json") + 7
                end = content.index("```", start)
                parsed = json.loads(content[start:end])
            elif "{" in content:
                start = content.index("{")
                end = content.rindex("}") + 1
                parsed = json.loads(content[start:end])
            else:
                parsed = {"raw_response": content[:1000]}
        except (json.JSONDecodeError, ValueError):
            parsed = {"raw_response": str(content)[:1000]}
        
        return {
            "provider_request_id": data.get("responseId", ""),
            "input_tokens": usage.get("promptTokenCount", 0),
            "output_tokens": usage.get("candidatesTokenCount", 0),
            "total_tokens": usage.get("totalTokenCount", 0),
            "finish_reason": candidates[0].get("finishReason", ""),
            "parsed": parsed,
            "raw_size": len(json.dumps(data)),
        }

    def call_vision(self, image_path: str, prompt: str,
                    system_prompt: str = "",
                    response_schema: dict = None) -> dict:
        """Call a vision-capable model with an image for architectural analysis.
        
        Supports: Gemini (native API), NVIDIA/OpenAI/DeepSeek (OpenAI-compatible API).
        
        Args:
            image_path: Path to an image file (PNG, JPG, WebP, etc.)
            prompt: The text prompt to send with the image
            system_prompt: Optional system instruction
            response_schema: Optional JSON schema for structured output
        
        Returns:
            dict with parsed response, tokens, latency
        """
        import httpx, base64
        
        if self.config.provider == "simulation":
            return {
                "provider_request_id": "sim-vision-" + uuid4().hex[:12],
                "input_tokens": 500, "output_tokens": 300, "total_tokens": 800,
                "finish_reason": "stop",
                "parsed": {"simulated": True, "note": "Simulation — no vision call made"},
                "raw_size": 0, "latency_ms": 10, "attempt": 1,
                "provider": "simulation", "model": "v5d-simulation-6.0",
            }
        
        if not self.config.is_configured():
            raise ProviderError(
                f"Provider '{self.config.provider}' not configured for vision",
                provider=self.config.provider, code="PROVIDER_NOT_CONFIGURED",
            )
        
        # Read and encode image
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        mime_type = "image/png"
        if image_path.lower().endswith(('.jpg', '.jpeg')):
            mime_type = "image/jpeg"
        elif image_path.lower().endswith('.webp'):
            mime_type = "image/webp"
        
        encoded_image = base64.b64encode(image_data).decode('utf-8')
        data_url = f"data:{mime_type};base64,{encoded_image}"
        
        t0 = time.time()
        last_error = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                if self.config.provider in ("openai", "deepseek", "nvidia"):
                    # ── OpenAI-compatible vision API ──
                    url = f"{self.config.base_url.rstrip('/')}/chat/completions"
                    headers = {
                        "Authorization": f"Bearer {self.config.api_key}",
                        "Content-Type": "application/json",
                    }
                    
                    messages = []
                    if system_prompt:
                        # Some vision models (llama-3.2) don't support system role.
                        # Merge system prompt into user content for reliability.
                        user_text = f"{system_prompt}\n\n---\n\n{prompt}"
                    else:
                        user_text = prompt
                    
                    user_content = [
                        {"type": "text", "text": user_text},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ]
                    messages.append({"role": "user", "content": user_content})
                    
                    body = {
                        "model": self.config.model,
                        "messages": messages,
                        "temperature": 0.4,
                        "max_tokens": min(self.config.max_tokens, 4096),
                    }
                    if response_schema:
                        body["response_format"] = {"type": "json_object"}
                    
                    with httpx.Client(timeout=self.config.timeout) as client:
                        resp = client.post(url, json=body, headers=headers)
                        resp.raise_for_status()
                        data = resp.json()
                    
                    latency = (time.time() - t0) * 1000
                    
                    choices = data.get("choices", [])
                    if not choices:
                        raise ProviderError("No choices in response", provider=self.config.provider, code="EMPTY_RESPONSE")
                    
                    content = choices[0].get("message", {}).get("content", "")
                    usage = data.get("usage", {})
                    
                    # Parse JSON from content
                    parsed = {}
                    if response_schema:
                        try:
                            # Try JSON first
                            if "```json" in content:
                                s = content.index("```json") + 7
                                e = content.index("```", s)
                                parsed = json.loads(content[s:e])
                            elif "{" in content:
                                s = content.index("{")
                                e = content.rindex("}") + 1
                                try:
                                    parsed = json.loads(content[s:e])
                                except json.JSONDecodeError:
                                    # Fallback: Python dict syntax (common with llama models)
                                    import ast
                                    parsed = ast.literal_eval(content[s:e])
                            else:
                                parsed = {"raw_response": content}
                        except (json.JSONDecodeError, ValueError, SyntaxError):
                            parsed = {"raw_response": content[:2000]}
                    else:
                        parsed = {"analysis": content}
                    
                    return {
                        "provider_request_id": data.get("id", ""),
                        "input_tokens": usage.get("prompt_tokens", 0),
                        "output_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                        "finish_reason": choices[0].get("finish_reason", ""),
                        "parsed": parsed,
                        "raw_size": len(json.dumps(data)),
                        "latency_ms": latency,
                        "attempt": attempt + 1,
                        "provider": self.config.provider,
                        "model": self.config.model,
                    }
                
                elif self.config.provider == "gemini":
                    # ── Gemini native API ──
                    url = f"{self.config.base_url.rstrip('/')}/models/{self.config.model}:generateContent?key={self.config.api_key}"
                    headers = {"Content-Type": "application/json"}
                    
                    parts = []
                    if system_prompt:
                        parts.append({"text": f"[System Instruction]: {system_prompt}"})
                    parts.append({"text": prompt})
                    parts.append({
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": encoded_image
                        }
                    })
                    
                    body = {
                        "contents": [{"role": "user", "parts": parts}],
                        "generationConfig": {
                            "temperature": 0.4,
                            "maxOutputTokens": min(self.config.max_tokens, 4096),
                        }
                    }
                    
                    with httpx.Client(timeout=self.config.timeout) as client:
                        resp = client.post(url, json=body, headers=headers)
                        resp.raise_for_status()
                        data = resp.json()
                    
                    latency = (time.time() - t0) * 1000
                    
                    candidates = data.get("candidates", [])
                    if not candidates:
                        raise ProviderError("Gemini returned no candidates", provider="gemini", code="EMPTY_RESPONSE")
                    
                    content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    usage = data.get("usageMetadata", {})
                    
                    parsed = {}
                    if response_schema:
                        try:
                            if "```json" in content:
                                s = content.index("```json") + 7
                                e = content.index("```", s)
                                parsed = json.loads(content[s:e])
                            elif "{" in content:
                                s = content.index("{")
                                e = content.rindex("}") + 1
                                parsed = json.loads(content[s:e])
                            else:
                                parsed = {"raw_response": content}
                        except (json.JSONDecodeError, ValueError):
                            parsed = {"raw_response": content[:2000]}
                    else:
                        parsed = {"analysis": content}
                    
                    return {
                        "provider_request_id": data.get("responseId", ""),
                        "input_tokens": usage.get("promptTokenCount", 0),
                        "output_tokens": usage.get("candidatesTokenCount", 0),
                        "total_tokens": usage.get("totalTokenCount", 0),
                        "finish_reason": candidates[0].get("finishReason", ""),
                        "parsed": parsed,
                        "raw_size": len(json.dumps(data)),
                        "latency_ms": latency,
                        "attempt": attempt + 1,
                        "provider": self.config.provider,
                        "model": self.config.model,
                    }
                    
            except Exception as e:
                last_error = e
                if attempt < self.config.max_retries:
                    time.sleep(2 ** attempt)
        
        raise last_error

    def estimate_cost(self, result: dict) -> float:
        """Estimate API cost from token usage."""
        input_tokens = result.get("input_tokens", 0)
        output_tokens = result.get("output_tokens", 0)
        provider = result.get("provider", self.config.provider)

        # Rough per-1K-token pricing (USD)
        rates = {
            "openai": {"input": 0.0025, "output": 0.010},    # GPT-4o approx
            "anthropic": {"input": 0.003, "output": 0.015},   # Claude Sonnet approx
            "deepseek": {"input": 0.00014, "output": 0.00028}, # DeepSeek approx
            "simulation": {"input": 0, "output": 0},
        }
        rate = rates.get(provider, rates["openai"])
        return (input_tokens / 1000) * rate["input"] + (output_tokens / 1000) * rate["output"]


class ProviderError(Exception):
    def __init__(self, message: str, provider: str = "", code: str = ""):
        super().__init__(message)
        self.provider = provider
        self.code = code
        self.timestamp = time.time()


# ── Prompt Templates ──

def build_ai_system_prompt() -> str:
    return """You are an architectural and interior design AI for Vision 5D.
Your task is to generate structured, executable design proposals.

RULES:
1. Output ONLY valid JSON matching the schema exactly.
2. Every edit must reference real scene dimensions, room layouts, and furniture.
3. Generate 2-3 genuinely different options (not just color changes).
4. Each option must specify: furniture additions/removals/transforms, finish changes, lighting changes, camera views.
5. Include rationale for each edit.
6. Mark confidence (0.0-1.0) and estimated cost band.
7. Do NOT propose operations on protected objects.
8. Respect permitted change categories.
9. Validate furniture fits within room dimensions.
10. Consider doorway and window positions. Keep circulation clear."""


def build_ai_user_prompt(
    analysis: dict,
    requirements: dict,
    furniture_library: list,
) -> str:
    """Build a structured user prompt from scene analysis + requirements."""
    return json.dumps({
        "task": "Generate interior design proposals",
        "scene_context": {
            "rooms": [
                {
                    "label": r.get("label", ""),
                    "function": r.get("function", ""),
                    "area_m2": r.get("area_m2", 0),
                    "dimensions": r.get("dimensions", {}),
                    "door_count": r.get("door_count", 0),
                    "window_count": r.get("window_count", 0),
                    "current_furniture": r.get("current_furniture", []),
                    "wall_availability": r.get("wall_availability", []),
                    "focal_points": r.get("focal_points", []),
                    "circulation_clearance_mm": r.get("circulation_clearance_mm", 900),
                    "constraints": r.get("constraints", []),
                }
                for r in analysis.get("rooms", [])
            ],
        },
        "requirements": {
            "style": requirements.get("style", "modern"),
            "seating_capacity": requirements.get("seating"),
            "budget_band": requirements.get("budget", "unspecified"),
            "permitted_categories": requirements.get("permitted_categories", []),
            "protected_objects": requirements.get("protected_objects", []),
            "furniture_additions_allowed": requirements.get("furniture_additions_allowed", True),
            "furniture_removals_allowed": requirements.get("furniture_removals_allowed", True),
            "finishes_allowed": requirements.get("finishes_allowed", True),
            "lighting_allowed": requirements.get("lighting_allowed", True),
            "cameras_allowed": requirements.get("cameras_allowed", True),
            "assumptions": requirements.get("assumptions", []),
            "constraints": requirements.get("constraints", []),
        },
        "available_furniture": furniture_library[:30],
        "response_schema": {
            "options": [
                {
                    "name": "Option Name",
                    "summary": "One-line description",
                    "strategy": "minimal|balanced|transformative",
                    "affected_rooms": ["room labels"],
                    "furniture_additions": [{"label": "", "position": [0,0,0], "dimensions": [0,0,0], "color": "#hex"}],
                    "furniture_removals": ["furniture labels to remove"],
                    "furniture_transforms": [{"label": "", "position": [0,0,0], "rotation_y_deg": 0}],
                    "finish_changes": [{"floor_color": "#hex", "wall_color": "#hex", "ceiling_color": "#hex", "floor_type": "wood"}],
                    "lighting_changes": [{"color": "#hex", "intensity": 1.0, "temperature": 4000}],
                    "camera_changes": [{"name": "View Name"}],
                    "advantages": [],
                    "compromises": [],
                    "estimated_cost_band": "standard",
                    "confidence": 0.8,
                }
            ]
        }
    }, indent=2)
