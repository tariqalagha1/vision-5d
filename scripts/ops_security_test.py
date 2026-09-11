#!/usr/bin/env python3
"""Vision 5D — Operational Security + API Tests"""
import urllib.request, json, sys

BASE = "http://127.0.0.1:8000"

def req(method, path, data=None, headers=None):
    h = headers or {}
    if data:
        h["Content-Type"] = "application/json"
        body = json.dumps(data).encode()
    else:
        body = None
    r = urllib.request.Request(f"{BASE}{path}", data=body, headers=h, method=method)
    try:
        resp = urllib.request.urlopen(r, timeout=5)
        return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")
    except Exception as e:
        return 0, {"error": str(e)}

# 1. Health
s, d = req("GET", "/health")
print(f"HEALTH: {s} — version={d.get('version')}, phase={d.get('phase')}")
assert s == 200, "Health check failed"

# 2. Login
s, d = req("POST", "/api/v1/auth/login", {"provider":"google","oauth_token":"demo"})
token = d.get("session_token", "")
print(f"LOGIN: {s} — user={d.get('user_id','')[:12]}... token={token[:12]}...")
assert s == 200 and token, "Login failed"

# 3. Auth required (no token) — try POST without auth
s, d = req("POST", "/api/v1/workspaces", {"name":"unauthorized","description":"test"})
print(f"WORKSPACES (no auth): {s} — {d.get('message','blocked')[:60]}")
assert s in (401, 403, 405), f"Expected auth block, got {s}"
print("  Auth enforcement: PASSED")

# 4. Authenticated request — create workspace
s, d = req("POST", "/api/v1/workspaces",
           {"name": "Ops Test", "description": "Cert"},
           {"Authorization": f"Bearer {token}"})
print(f"CREATE WS (auth): {s} — id={d.get('workspace_id','')[:12]}...")
assert s == 200, f"Auth WS create failed: {s}"

# 5. Cross-tenant AI access
s, d = req("GET", "/api/v6/ai/projects/00000000-0000-0000-0000-000000000001/proposals",
           headers={"Authorization": f"Bearer {token}"})
print(f"CROSS-TENANT AI: {s}")
assert s in (401, 403, 404), f"Cross-tenant not blocked: {s}"

# 6. Metrics (plaintext, not JSON)
s = urllib.request.urlopen(urllib.request.Request(f"{BASE}/metrics")).status
print(f"METRICS: {s} — prometheus_endpoint={'OK' if s==200 else 'FAIL'}")
assert s == 200, "Metrics endpoint failed"

# 7. Create workspace + project
s, d = req("POST", "/api/v1/workspaces",
           {"name": "Ops Test WS", "description": "Cert"},
           {"Authorization": f"Bearer {token}"})
ws_id = d.get("workspace_id", "")
print(f"CREATE WS: {s} — id={ws_id[:12]}...")
assert s == 200 and ws_id, "WS create failed"

s, d = req("POST", f"/api/v1/workspaces/{ws_id}/projects",
           {"workspace_id": ws_id, "name": "Ops Test Project", "project_type": "residential"},
           {"Authorization": f"Bearer {token}"})
proj_id = d.get("project_id", "")
print(f"CREATE PROJ: {s} — id={proj_id[:12]}...")
assert s == 200 and proj_id, "Project create failed"

print(f"\n=== ALL SECURITY + API TESTS PASSED ===")
print(f"Project ID for further tests: {proj_id}")
