"""Debug NVIDIA vision response with the actual screen analysis prompt."""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from packages.computer_use.vision import NVIDIAVisionAnalyzer, _vision_analyzer
# Force fresh init with the vision module's own analyzer
analyzer = NVIDIAVisionAnalyzer()

test_path = "evidence/V5D-LOCAL-EXTERNAL-SERVICES-READINESS-001/computer_use/screenshots/nvidia_test_screenshot.png"

# Call the full analyze_screenshot and inspect raw_response
import base64
with open(test_path, "rb") as f:
    image_bytes = f.read()

ext = os.path.splitext(test_path)[1].lower()
mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
mime_type = mime_map.get(ext, "image/png")
image_b64 = base64.b64encode(image_bytes).decode("utf-8")

from packages.ai.provider_client import ProviderAdapter
adapter = ProviderAdapter(analyzer.config)

t0 = time.time()
response = adapter.call_vision(
    image_path=test_path,
    prompt=analyzer.SCREEN_ANALYSIS_PROMPT,
)
latency = (time.time() - t0) * 1000

print(f"Latency: {latency:.0f}ms")
print(f"Tokens: {response.get('total_tokens')}")
print(f"\nRaw 'parsed' field:")
parsed = response.get("parsed", {})
print(json.dumps(parsed, indent=2, default=str)[:2000])
print(f"\nType of parsed: {type(parsed)}")

# Now figure out what content should be extracted
if isinstance(parsed, dict):
    print(f"Parsed keys: {list(parsed.keys())}")
    # Try to find the JSON content
    for k, v in parsed.items():
        if isinstance(v, str) and len(v) > 50:
            print(f"\nContent from key '{k}':")
            print(v[:1000])
