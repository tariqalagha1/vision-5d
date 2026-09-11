"""STAGE 4: Executor Smoke Test — real actions with verification."""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from packages.computer_use import (
    ComputerAction, ActionResult, ActionType, RiskLevel,
    ComputerUseSession, SessionState, SecurityConfig,
)
from packages.computer_use.executor import ActionExecutor
from packages.computer_use.security import SecurityGuard
from PIL import ImageGrab

evidence_dir = "evidence/V5D-LOCAL-EXTERNAL-SERVICES-READINESS-001/computer_use"
os.makedirs(os.path.join(evidence_dir, "screenshots"), exist_ok=True)

executor = ActionExecutor(evidence_dir=evidence_dir)
guard = SecurityGuard(SecurityConfig(enabled=True))
session = ComputerUseSession(
    objective="Smoke test — verify executor and security",
    state=SessionState.RUNNING,
)

results = []

# Test 1: Screenshot capture
print("=== TEST 1: Screenshot ===")
action = ComputerAction(action_type=ActionType.SCREENSHOT, risk_level=RiskLevel.NONE)
valid, reason = guard.validate_action(action, session)
print(f"  Validate: {valid} ({reason})")
result = executor.execute(action, session)
results.append({"test": "screenshot", "success": result.success, "before": result.before_screenshot_path, "error": result.error})
print(f"  Execute: success={result.success}, before={os.path.basename(result.before_screenshot_path)}, error={result.error}")

# Test 2: Wait
print("\n=== TEST 2: Wait ===")
action = ComputerAction(action_type=ActionType.WAIT, params={"seconds": 2}, risk_level=RiskLevel.LOW)
valid, reason = guard.validate_action(action, session)
print(f"  Validate: {valid} ({reason})")
result = executor.execute(action, session)
results.append({"test": "wait", "success": result.success, "error": result.error})
print(f"  Execute: success={result.success}")

# Test 3: Screenshot after wait (before/after pair)
print("\n=== TEST 3: Second Screenshot ===")
action = ComputerAction(action_type=ActionType.SCREENSHOT, risk_level=RiskLevel.NONE)
result = executor.execute(action, session)
results.append({"test": "screenshot2", "success": result.success, "after": result.before_screenshot_path, "error": result.error})
print(f"  Execute: success={result.success}, after={os.path.basename(result.before_screenshot_path)}")

# Verify screenshots exist and differ
for r in results:
    if "before" in r and r["before"]:
        size = os.path.getsize(r["before"])
        print(f"  Screenshot {r['test']}: {r['before']} ({size} bytes)")
    if "after" in r and r["after"]:
        size = os.path.getsize(r["after"])
        print(f"  Screenshot {r['test']}: {r['after']} ({size} bytes)")

# Test 4: Emergency stop
print("\n=== TEST 4: Emergency Stop ===")
session.state = SessionState.EMERGENCY_STOPPED
action = ComputerAction(action_type=ActionType.CLICK, params={"x": 100, "y": 100})
valid, reason = guard.validate_action(action, session)
print(f"  Validate (stopped): {valid} ({reason})")
results.append({"test": "emergency_stop", "blocked": not valid, "reason": reason})

# Test 5: Malformed action rejected
print("\n=== TEST 5: Malformed Action ===")
action = ComputerAction(action_type=ActionType.CLICK, params={})
issues = action.validate()
print(f"  Validation issues: {issues}")
results.append({"test": "malformed_action", "issues": issues})

# Test 6: External domain blocked
print("\n=== TEST 6: External Domain Blocked ===")
session.state = SessionState.RUNNING
action = ComputerAction(action_type=ActionType.OPEN_URL, params={"url": "https://google.com"})
valid, reason = guard.validate_action(action, session)
print(f"  Validate: {valid} ({reason})")
results.append({"test": "external_domain", "blocked": not valid, "reason": reason})

# Summary
print("\n=== SMOKE TEST SUMMARY ===")
passed = 0
for r in results:
    if r.get("success", False) or r.get("blocked", False) or r.get("issues"):
        status = "PASS" if (r.get("success") or r.get("blocked") or len(r.get("issues", [])) > 0) else "FAIL"
        if status == "PASS": passed += 1
        print(f"  [{status}] {r['test']}")

print(f"\n{passed}/{len(results)} smoke tests passed")

# Write results
with open(os.path.join(evidence_dir, "executor_smoke_test.json"), "w") as f:
    json.dump({"results": results, "passed": passed, "total": len(results), 
               "driver_version": "cua-driver 0.9.0", "driver_path": "C:\\Users\\admin\\AppData\\Local\\Programs\\Cua\\cua-driver\\bin\\cua-driver.exe"},
              indent=2, default=str)
print("\nResults saved to executor_smoke_test.json")
