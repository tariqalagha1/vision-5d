"""NVIDIA Vision runtime test — real screenshot analysis."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from PIL import ImageGrab

# Capture screenshot
evidence_dir = "evidence/V5D-LOCAL-EXTERNAL-SERVICES-READINESS-001/computer_use/screenshots"
os.makedirs(evidence_dir, exist_ok=True)

img = ImageGrab.grab(bbox=(0, 0, 800, 600))
test_path = os.path.join(evidence_dir, "nvidia_test_screenshot.png")
img.save(test_path, "PNG")
print(f"Screenshot saved: {test_path} ({os.path.getsize(test_path)} bytes)")

# Analyze
from packages.computer_use.vision import NVIDIAVisionAnalyzer
analyzer = NVIDIAVisionAnalyzer()
print(f"Provider: {analyzer.config.provider}")
print(f"Model: {analyzer.config.model}")

t0 = time.time()
result = analyzer.analyze_screenshot(test_path)
latency = (time.time() - t0) * 1000

print(f"\n=== ANALYSIS RESULT ===")
print(f"Latency: {latency:.0f}ms")
print(f"Error: {result.error}")
summary = result.screen_summary[:300]
print(f"Summary: {summary}")
print(f"Elements detected: {len(result.visible_elements)}")
for el in result.visible_elements[:8]:
    print(f"  [{el.element_id}] {el.element_type}: '{el.label}' (conf={el.confidence:.2f})")
print(f"Valid: {result.is_valid()}")
print(f"Model used: {result.model}")

# Check no key leaked
text = result.screen_summary + str(result.visible_elements)
if 'nvapi' in text:
    print("\nCREDENTIAL LEAK DETECTED!")
else:
    print("\nNo credential leak")
