#!/usr/bin/env python3
"""Direct DeepSeek provider test."""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["AI_PROVIDER"] = "deepseek"
os.environ["DEEPSEEK_API_KEY"] = "sk-78ee667e3faf4fb4902d69fa7fb7d3e1"
os.environ["AI_MODEL"] = "deepseek-chat"
os.environ["AI_SIMULATION_ALLOWED"] = "false"

from packages.ai.provider_client import ProviderConfig, ProviderAdapter, build_ai_system_prompt, build_ai_user_prompt

config = ProviderConfig.from_env()
print(f"Provider: {config.provider}, Model: {config.model}")
print(f"API key loaded: {'YES' if config.api_key else 'NO'}")

adapter = ProviderAdapter(config)

system_prompt = build_ai_system_prompt()
user_prompt = build_ai_user_prompt(
    analysis={
        "rooms": [{
            "label": "Living Room",
            "function": "living_room",
            "area_m2": 32.0,
            "dimensions": {"width_mm": 6000, "depth_mm": 5300, "height_mm": 2500},
            "door_count": 1,
            "window_count": 1,
            "current_furniture": [{"label": "TV Stand", "position": [2500, 0, 4500]}],
            "constraints": ["Protect doorway", "Protect TV stand"],
        }]
    },
    requirements={
        "style": "modern",
        "seating_capacity": 6,
        "budget": "standard",
        "permitted_categories": ["furniture", "finishes", "lighting"],
        "protected_objects": ["doorway", "TV Stand"],
        "furniture_additions_allowed": True,
        "furniture_removals_allowed": False,
        "finishes_allowed": True,
        "lighting_allowed": True,
    },
    furniture_library=[
        {"name": "Sofa 3-Seater", "category": "living_room", "dimensions": [2200, 850, 900]},
        {"name": "Armchair", "category": "living_room", "dimensions": [900, 900, 850]},
        {"name": "Coffee Table", "category": "living_room", "dimensions": [1200, 450, 600]},
    ],
)

print(f"\nCalling DeepSeek API ({config.base_url})...")
t0 = time.time()
try:
    result = adapter.call(system_prompt, user_prompt)
    latency = (time.time() - t0) * 1000
    cost = adapter.estimate_cost(result)

    print(f"\n=== PROVIDER CALL SUCCESS ===")
    print(f"Request ID: {result.get('provider_request_id', 'N/A')}")
    print(f"Input tokens: {result.get('input_tokens', 0)}")
    print(f"Output tokens: {result.get('output_tokens', 0)}")
    print(f"Total tokens: {result.get('total_tokens', 0)}")
    print(f"Latency: {latency:.0f}ms")
    print(f"Estimated cost: ${cost:.6f}")
    print(f"Finish reason: {result.get('finish_reason', 'N/A')}")

    parsed = result.get("parsed", {})
    if isinstance(parsed, dict):
        options = parsed.get("options", [])
        print(f"\nOptions generated: {len(options)}")
        for i, opt in enumerate(options):
            print(f"  Option {i+1}: {opt.get('name', '?')}")
            print(f"    Strategy: {opt.get('strategy', '?')}")
            adds = opt.get('furniture_additions', [])
            print(f"    Furniture additions: {len(adds)}")
            for a in adds[:3]:
                print(f"      - {a.get('label', '?')}: pos={a.get('position')}, color={a.get('color')}")
            finishes = opt.get('finish_changes', [])
            print(f"    Finish changes: {len(finishes)}")
            for f in finishes[:2]:
                print(f"      - floor={f.get('floor_color')}, wall={f.get('wall_color')}")
            advantages = opt.get('advantages', [])
            print(f"    Advantages: {advantages[:2]}")
    else:
        print(f"\nRaw response (first 1000 chars): {str(parsed)[:1000]}")

except Exception as e:
    print(f"\n=== PROVIDER CALL FAILED ===")
    print(f"Error: {str(e)[:500]}")
    import traceback
    traceback.print_exc()
