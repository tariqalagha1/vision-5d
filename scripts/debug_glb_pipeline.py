"""Run full pipeline via API and observe GLB output."""
import requests, json, uuid, hashlib, time

BASE = "http://localhost:8000"
s = requests.Session()

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

# 1. Login
r = s.post(f"{BASE}/api/v1/auth/login", json={"provider": "google", "oauth_token": f"e2e-{uuid.uuid4().hex[:8]}"})
assert r.status_code == 200, f"login failed: {r.text}"
log(f"Login OK, user={r.json()['user_id'][:8]}")

# 2. Workspace
r = s.get(f"{BASE}/api/v1/workspaces")
if r.json()["count"] == 0:
    r = s.post(f"{BASE}/api/v1/workspaces", json={"name": "GLB-Debug WS"})
ws_id = r.json().get("workspace_id") or r.json()["workspaces"][0]["workspace_id"]
log(f"Workspace: {ws_id}")

# 3. Project
r = s.post(f"{BASE}/api/v1/workspaces/{ws_id}/projects", json={
    "workspace_id": ws_id,
    "name": f"GLB-Debug {uuid.uuid4().hex[:6]}",
    "project_type": "residential"
})
proj_id = r.json()["project_id"]
log(f"Project: {proj_id}")

# 4. Understand (photo)
r = s.post(f"{BASE}/api/v1/projects/{proj_id}/understand")
log(f"Understand: {r.status_code}")
if r.status_code != 200:
    log(f"  ERROR: {r.text[:500]}")
else:
    log(f"  state={r.json().get('state')}, provider={r.json().get('provider')}, model={r.json().get('model')}")

# 5. Approve
r = s.post(f"{BASE}/api/v1/projects/{proj_id}/understanding/approve")
log(f"Approve: {r.status_code} → {r.json().get('new_state') if r.status_code==200 else r.text[:200]}")

# 6. Geometry
r = s.post(f"{BASE}/api/v1/projects/{proj_id}/geometry")
log(f"Geometry: {r.status_code}")
geom = {}
if r.status_code == 200:
    geom = r.json().get("geometry", {})
    log(f"  walls={len(geom.get('walls',[]))}, furniture={len(geom.get('furniture',[]))}")
else:
    log(f"  ERROR: {r.text[:300]}")

# 7. Pascal scene
r = s.post(f"{BASE}/api/v1/projects/{proj_id}/pascal")
log(f"Pascal: {r.status_code} → {r.json().get('state') if r.status_code==200 else r.text[:200]}")

# 8. Import correction / revision
r = s.post(f"{BASE}/api/v1/projects/{proj_id}/pascal/import", json={
    "corrections": [{"type": "furniture_placement", "object": "sofa", "position": [2.5, 0.5, 0]}]
})
log(f"Revision: {r.status_code} → {r.json().get('state') if r.status_code==200 else r.text[:200]}")

# 9. Scene3D + GLB
r = s.post(f"{BASE}/api/v1/projects/{proj_id}/scene3d")
log(f"Scene3D: {r.status_code}")
if r.status_code == 200:
    d = r.json()
    log(f"  GLB size={d.get('glb_size_bytes')}, sha256={d.get('glb_sha256','')[:16]}, valid={d.get('glb_valid')}")
    log(f"  validation: {json.dumps(d.get('validation',{}))[:300]}")
    # Check the actual GLB file
    glb_path = d.get("glb_path")
    if glb_path:
        import os
        if os.path.exists(glb_path):
            with open(glb_path, 'rb') as f:
                data = f.read()
            log(f"  GLB file: {glb_path}, size={len(data)} bytes")
        else:
            log(f"  GLB file MISSING: {glb_path}")
else:
    log(f"  ERROR: {r.text[:500]}")

log(f"\n=== PROJECT ID: {proj_id} ===")
