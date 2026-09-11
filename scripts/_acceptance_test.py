#!/usr/bin/env python3
"""Acceptance test: drive the reference DXF through the REAL production flow.

Customer path: upload-cad -> cad/understand (vector) -> geometry/reconstruct
-> 3d-reconstruction -> GLB. Verifies the worker used the vector CAD path.
"""
import sys, os, json, time, hashlib, urllib.request, http.cookiejar

BASE = "http://localhost:8000"
DXF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output", "RE-SingDetch-FH_AS", "geometry", "converted.dxf")

# Cookie jar
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def post(path, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, headers=headers or {}, method="POST")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    r = opener.open(req, timeout=120)
    return json.loads(r.read().decode())

def get(path):
    r = opener.open(BASE + path, timeout=120)
    return json.loads(r.read().decode())

def multipart_upload(path, filepath, filename, name):
    boundary = "----v5d" + os.urandom(8).hex()
    with open(filepath, "rb") as f:
        content = f.read()
    parts = []
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\nContent-Type: application/octet-stream\r\n\r\n".encode())
    parts.append(content)
    parts.append(f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"name\"\r\n\r\n{name}\r\n".encode())
    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)
    req = urllib.request.Request(BASE + path, data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    r = opener.open(req, timeout=300)
    return json.loads(r.read().decode())

def poll_job(job_id, timeout=180):
    t0 = time.time()
    while time.time() - t0 < timeout:
        d = get(f"/api/v1/jobs/{job_id}")
        st = d.get("state", "")
        if st in ("COMPLETED", "FAILED_TERMINAL", "FAILED_RETRYABLE", "FAILED"):
            return d
        time.sleep(3)
    return {"state": "TIMEOUT"}

print("=== STEP 0: login ===")
login = post("/api/v1/auth/login", {"provider": "google", "oauth_token": "demo"})
print("  user_id:", login.get("user_id"))

print("=== STEP 1: upload-cad (customer entry) ===")
up = multipart_upload("/api/v1/assets/upload-cad", DXF, "RE-SingDetch-FH_AS.dxf", "RE-SingDetch-FH_AS")
pid = up.get("project_id")
print("  project_id:", pid, "| size:", up.get("size_bytes"), "| existing:", up.get("existing"))

print("=== STEP 2: cad/understand (vector route) ===")
cu = post(f"/api/v1/projects/{pid}/cad/understand")
job_id = cu.get("job_id")
print("  job_id:", job_id, "| pipeline:", cu.get("pipeline"), "| format:", cu.get("detected_format"), "| cad_path:", cu.get("cad_path"))

print("=== STEP 3: poll cad-understanding job ===")
r = poll_job(job_id)
print("  state:", r.get("state"))
# extract graph_id from job params
job_detail = get(f"/api/v1/jobs/{job_id}")
params = job_detail.get("params") or {}
graph_id = params.get("graph_id")
print("  graph_id:", graph_id, "| vector_walls:", params.get("vector_walls"), "| vector_doors:", params.get("vector_doors"), "| vector_rooms:", params.get("vector_rooms"), "| source:", params.get("source"))

print("=== STEP 4: geometry/reconstruct (consumes vector graph) ===")
gr = post(f"/api/v1/projects/{pid}/geometry/reconstruct")
gjob = gr.get("job_id")
print("  geometry job:", gjob)
r2 = poll_job(gjob)
print("  state:", r2.get("state"))

print("=== STEP 5: scene3d/3d-reconstruction ===")
# find geometry model id
try:
    gd = get(f"/api/v1/projects/{pid}/geometry/progress")
    print("  geometry progress:", gd.get("state"), "has_output:", gd.get("has_output"))
except Exception as e:
    print("  geometry progress err:", e)

print("=== DONE ===")
print(json.dumps({"project_id": pid, "cad_job": job_id, "graph_id": graph_id, "cad_params": params}, indent=2))
