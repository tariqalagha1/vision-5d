"""
Vision 5D — Gemini Vision Analysis Module
Architectural image analysis using Google Gemini multimodal API.

Capabilities:
- Floor plan recognition (rooms, walls, doors, windows)
- Furniture detection and classification
- Architectural element identification
- Room function inference
- Scale and dimension estimation
- Drawing quality assessment
- Spanish/English bilingual label support
"""
import os, json, base64, time
from typing import Optional
from dataclasses import dataclass, field

from packages.ai.provider_client import ProviderAdapter, ProviderConfig, ProviderError


@dataclass
class VisionAnalysisResult:
    """Structured result from Gemini vision analysis of an architectural image."""
    success: bool = False
    provider: str = "gemini"
    model: str = ""
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0

    # Architectural analysis
    drawing_type: str = ""          # floor_plan, elevation, section, site_plan, unknown
    views_detected: list[str] = field(default_factory=list)
    rooms: list[dict] = field(default_factory=list)
    walls_visible: bool = False
    doors_visible: bool = False
    windows_visible: bool = False
    furniture_detected: list[dict] = field(default_factory=list)
    dimensions_visible: bool = False
    annotations_visible: bool = False
    language: str = ""              # en, es, mixed, unknown

    # Quality assessment
    is_blank: bool = False
    is_clipped: bool = False
    is_collapsed: bool = False
    proportions_plausible: bool = False
    suitable_for_review: bool = False
    quality_notes: list[str] = field(default_factory=list)

    # Raw response
    raw_analysis: str = ""
    error: str = ""


class GeminiVisionAnalyzer:
    """Analyzes architectural images using Gemini's multimodal vision API."""

    ARCHITECTURAL_SYSTEM_PROMPT = """You are an expert architectural drawing analyzer for Vision 5D.
Analyze the provided architectural image with extreme precision.

RULES:
1. Identify the drawing type: floor_plan, elevation, section, site_plan, or mixed
2. List ALL rooms/spaces visible with their labels (Spanish or English)
3. Detect walls, doors, windows, and furniture
4. Note if dimensions or annotations are present
5. Assess drawing quality: is it blank, clipped, collapsed, or suitable for review?
6. Identify the language of labels (en, es, mixed)
7. Be specific about what you CAN and CANNOT see

Respond ONLY with a JSON object matching this exact schema:
{
  "drawing_type": "floor_plan|elevation|section|site_plan|mixed|unknown",
  "views_detected": ["view name 1", "view name 2"],
  "rooms": [{"label": "Room Name", "approx_area_m2": 0, "has_furniture": false}],
  "walls_visible": true,
  "doors_visible": true,
  "windows_visible": true,
  "furniture_detected": [{"type": "sofa|bed|table|chair|cabinet|other", "count": 1, "room": "Room Name"}],
  "dimensions_visible": true,
  "annotations_visible": true,
  "language": "en|es|mixed|unknown",
  "is_blank": false,
  "is_clipped": false,
  "is_collapsed": false,
  "proportions_plausible": true,
  "suitable_for_review": true,
  "quality_notes": ["note 1", "note 2"]
}"""

    # Concise prompt for OpenAI-compatible vision models (NVIDIA)
    NVIDIA_VISION_PROMPT = """Analyze this architectural image. Output ONLY a JSON object with these fields:
{
  "drawing_type": "floor_plan|elevation|section|site_plan|unknown",
  "views_detected": ["view name"],
  "rooms": [{"label": "Room Name", "approx_area_m2": 0, "has_furniture": false}],
  "walls_visible": false, "doors_visible": false, "windows_visible": false,
  "furniture_detected": [{"type": "sofa|bed|table|chair|cabinet|other", "count": 1, "room": "Room Name"}],
  "dimensions_visible": false, "annotations_visible": false,
  "language": "en|es|mixed",
  "is_blank": false, "is_clipped": false, "is_collapsed": false,
  "proportions_plausible": false, "suitable_for_review": false,
  "quality_notes": [""]
}
Begin your response with { and end with }. No other text."""

    def __init__(self, config: Optional[ProviderConfig] = None):
        if config is None:
            config = ProviderConfig.from_env()
        # Support gemini OR nvidia for vision
        if config.provider not in ("gemini", "nvidia"):
            # Default to nvidia if NVIDIA_API_KEY is set, else gemini
            nvidia_key = os.getenv("NVIDIA_API_KEY", "")
            if nvidia_key:
                config = ProviderConfig(
                    provider="nvidia",
                    model=os.getenv("AI_VISION_MODEL", os.getenv("AI_MODEL", "meta/llama-3.2-11b-vision-instruct")),
                    api_key=nvidia_key,
                    base_url="https://integrate.api.nvidia.com/v1",
                    timeout=60,
                    max_retries=2,
                )
            else:
                config = ProviderConfig(
                    provider="gemini",
                    model=os.getenv("AI_MODEL", "gemini-2.0-flash"),
                    api_key=os.getenv("GEMINI_API_KEY", ""),
                    base_url="https://generativelanguage.googleapis.com/v1beta",
                    timeout=60,
                    max_retries=2,
                )
        self.config = config
        self.adapter = ProviderAdapter(config)

    def analyze_image(self, image_path: str, custom_prompt: str = "") -> VisionAnalysisResult:
        """Analyze an architectural image and return structured results.

        Args:
            image_path: Path to PNG, JPG, or WebP image
            custom_prompt: Optional additional instructions for the analyzer

        Returns:
            VisionAnalysisResult with structured architectural analysis
        """
        result = VisionAnalysisResult(provider=self.config.provider, model=self.config.model)

        if not self.config.is_configured():
            result.error = f"Provider not configured. Set {self.config.provider.upper()}_API_KEY"
            return result

        # Use concise prompt for NVIDIA, full architectural prompt for Gemini
        if self.config.provider == "nvidia":
            system = ""
            prompt = self.NVIDIA_VISION_PROMPT
            if custom_prompt:
                prompt = custom_prompt + "\n\n" + self.NVIDIA_VISION_PROMPT
        else:
            system = self.ARCHITECTURAL_SYSTEM_PROMPT
            prompt = custom_prompt if custom_prompt else "Analyze this architectural drawing in detail."

        try:
            response = self.adapter.call_vision(
                image_path=image_path,
                prompt=prompt,
                system_prompt=system,
                response_schema={"type": "json_object"},
            )

            result.success = True
            result.latency_ms = response.get("latency_ms", 0)
            result.input_tokens = response.get("input_tokens", 0)
            result.output_tokens = response.get("output_tokens", 0)
            result.model = response.get("model", self.config.model)

            parsed = response.get("parsed", {})
            result.raw_analysis = json.dumps(parsed, indent=2)

            # Populate structured fields from parsed response
            result.drawing_type = parsed.get("drawing_type", "unknown")
            result.views_detected = parsed.get("views_detected", [])
            result.rooms = parsed.get("rooms", [])
            result.walls_visible = parsed.get("walls_visible", False)
            result.doors_visible = parsed.get("doors_visible", False)
            result.windows_visible = parsed.get("windows_visible", False)
            result.furniture_detected = parsed.get("furniture_detected", [])
            result.dimensions_visible = parsed.get("dimensions_visible", False)
            result.annotations_visible = parsed.get("annotations_visible", False)
            result.language = parsed.get("language", "unknown")
            result.is_blank = parsed.get("is_blank", False)
            result.is_clipped = parsed.get("is_clipped", False)
            result.is_collapsed = parsed.get("is_collapsed", False)
            result.proportions_plausible = parsed.get("proportions_plausible", False)
            result.suitable_for_review = parsed.get("suitable_for_review", False)
            result.quality_notes = parsed.get("quality_notes", [])

        except ProviderError as e:
            result.error = f"Provider error: {e}"
        except Exception as e:
            result.error = f"Vision analysis failed: {e}"

        return result

    def analyze_floor_plan(self, image_path: str) -> VisionAnalysisResult:
        """Specialized analysis for floor plans with room detection focus."""
        prompt = """Analyze this floor plan in detail. Focus on:
1. Room count and each room's name/label
2. Room functions (living, bedroom, kitchen, bathroom, etc.)
3. Furniture placement within rooms
4. Door and window positions
5. Circulation paths
6. Overall layout quality"""
        return self.analyze_image(image_path, custom_prompt=prompt)

    def analyze_elevation(self, image_path: str) -> VisionAnalysisResult:
        """Specialized analysis for building elevations."""
        prompt = """Analyze this building elevation. Focus on:
1. Building height and width proportions
2. Window and door placement on facade
3. Material or finish indications
4. Roof type and style
5. Architectural style classification"""
        return self.analyze_image(image_path, custom_prompt=prompt)

    def quick_scan(self, image_path: str) -> dict:
        """Fast scan: is this a valid architectural drawing? Returns simple dict."""
        result = self.analyze_image(
            image_path,
            custom_prompt="Is this a valid architectural drawing? Respond with JSON: {\"is_architectural\": true/false, \"type\": \"floor_plan|elevation|other|not_architectural\", \"confidence\": 0.0-1.0}"
        )
        if result.success and result.raw_analysis:
            try:
                return json.loads(result.raw_analysis)
            except:
                pass
        return {"is_architectural": False, "type": "unknown", "confidence": 0.0, "error": result.error}


# Singleton
gemini_vision = GeminiVisionAnalyzer()
