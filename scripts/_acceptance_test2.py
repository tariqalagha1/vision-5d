#!/usr/bin/env python3
"""Acceptance test part 2: geometry -> scene3d -> GLB from the vector graph."""
import sys, os, json, time, urllib.request, http.cookiejar

BASE = "http://localhost:8000"
PID = "1164369e-20ae-4557-bfe9-991e8b91f910"
GRAPH_ID = "3d38fb34-d586-449c-a6b5-37647562253f"

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def post(path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method="POST")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    r = opener.open(req, timeout=300)
    return json.loads(r.read().decode())

def get(path):
    r = opener.open(BASE + path, timeout=300)
    return json.loads(r.read().decode())

def poll(job_id, timeout=600):
    t0 = time.time()
    while time.time() - t0 < timeout:
        d = get(f"/api/v1/jobs/{job_id}")
        st = d.get("state", "")
        if st in ("COMPLETED", "FAILED_TERMINAL", "FAILED_RETRYABLE", "FAILED"):
            return d
        time.sleep(4)
    return {"state": "TIMEOUT"}

print("=== login ===")
post("/api/v1/auth/login", {"provider": "google", "oauth_token": "demo"})

print("=== geometry/reconstruct (source_graph_id) ===")
gr = post(f"/api/v3/projects/{PID}/geometry/reconstruct?source_graph_id={GRAPH_ID}")
gjob = gr.get("job_id")
print("  geometry job:", gjob)
r = poll(gjob)
print("  state:", r.get("state"))

print("=== scene3d reconstruct (auto-find geometry model) ===")
sr = post(f"/api/v4/projects/{PID}/scene/reconstruct")
sjob = sr.get("job_id")
print("  scene3d job:", sjob)
r2 = poll(sjob)
print("  state:", r2.get("state"))

print("=== check GLB / scene output ===")
try:
    # scene versions / stats
    sc = get(f"/api/v4/projects/{PID}/scene")
    print("  scene stats:", json.dumps({k: sc.get(k) for k in ('version','state','statistics','vertex_count','triangle_count') if k in sc}, default=str)[:300])
except Exception as e:
    print("  scene err:", e)

print("=== check .exports for the scene GLB ===")
import glob
glbs = glob.glob(f".exports/scene_{PID}*.glb") + glob.glob(".exports/scene_*.glb")
for g in sorted(glbs, key=os.path.getmtime, reverse=True)[:5]:
    print("  ", g, os.path.getsize(g), "bytes", time.strftime('%H:%M:%S', time.localtime(os.path.getmtime(g))))

print("=== DONE ===")
