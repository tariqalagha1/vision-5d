"""Debug NVIDIA vision response format."""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from packages.computer_use.vision import NVIDIAVisionAnalyzer

analyzer = NVIDIAVisionAnalyzer()

# Check what call_vision actually returns
from packages.ai.provider_client import ProviderAdapter

adapter = ProviderAdapter(analyzer.config)

test_path = "evidence/V5D-LOCAL-EXTERNAL-SERVICES-READINESS-001/computer_use/screenshots/nvidia_test_screenshot.png"
if not os.path.exists(test_path):
    from PIL import ImageGrab
    os.makedirs(os.path.dirname(test_path), exist_ok=True)
    img = ImageGrab.grab(bbox=(0, 0, 800, 600))
    img.save(test_path, "PNG")

t0 = time.time()
response = adapter.call_vision(
    image_path=test_path,
    prompt="Describe this screenshot in one sentence.",
)
latency = (time.time() - t0) * 1000

print(f"Latency: {latency:.0f}ms")
print(f"Response keys: {list(response.keys())}")
print(f"Response type: {type(response)}")
print(f"\nFull response:")
for k, v in response.items():
    if isinstance(v, str) and len(v) > 500:
        print(f"  {k}: {v[:500]}...")
    else:
        print(f"  {k}: {v}")
