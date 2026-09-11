#!/usr/bin/env python3
"""Re-run the production chain with the corrected FEET scale."""
import json, time, urllib.request, http.cookiejar, struct, os

BASE="http://localhost:8000"; PID="1164369e-20ae-4557-bfe9-991e8b91f910"
cj=http.cookiejar.CookieJar(); op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
def post(p,b=None):
    d=json.dumps(b).encode() if b is not None else None
    r=urllib.request.Request(BASE+p,data=d,method="POST")
    if b is not None: r.add_header("Content-Type","application/json")
    return json.loads(op.open(r,timeout=300).read().decode())
def get(p): return json.loads(op.open(BASE+p,timeout=300).read().decode())
def poll(jid,t=600):
    t0=time.time()
    while time.time()-t0<t:
        d=get(f"/api/v1/jobs/{jid}"); s=d.get("state","")
        if s in ("COMPLETED","FAILED","FAILED_TERMINAL","FAILED_RETRYABLE"): return d
        time.sleep(4)
    return {"state":"TIMEOUT"}

print("login...", end=" ")
post("/api/v1/auth/login", {"provider":"google","oauth_token":"demo"}); print("ok")

print("cad/understand...")
r=post(f"/api/v1/projects/{PID}/cad/understand"); cjob=r.get("job_id"); print("  job", cjob)
c=poll(cjob); print("  state", c.get("state"))
gid=c.get("params",{}).get("graph_id") or c.get("graph_id")
print("  graph_id", gid)

print("geometry/reconstruct...")
r=post(f"/api/v3/projects/{PID}/geometry/reconstruct?source_graph_id={gid}"); gjob=r.get("job_id")
g=poll(gjob); print("  job", gjob, "state", g.get("state"))

print("scene3d reconstruct...")
r=post(f"/api/v4/projects/{PID}/scene/reconstruct"); sjob=r.get("job_id")
s=poll(sjob); print("  job", sjob, "state", s.get("state"))

# find the newest GLB
import glob
glbs=sorted(glob.glob(".exports/*.glb"), key=os.path.getmtime, reverse=True)
newest=glbs[0]
print("NEWEST GLB:", newest, os.path.getsize(newest), "bytes")

d=open(newest,'rb').read()
jl=struct.unpack('<I', d[12:16])[0]
g2=json.loads(d[20:20+jl].rstrip(b' ').decode('utf-8'))
mins=[a['min'] for a in g2['accessors'] if a.get('type')=='VEC3' and 'min' in a]
maxs=[a['max'] for a in g2['accessors'] if a.get('type')=='VEC3' and 'max' in a]
mn=[min(v[i] for v in mins) for i in range(3)]; mx=[max(v[i] for v in maxs) for i in range(3)]
ext=[mx[i]-mn[i] for i in range(3)]
print(f"GLB bounds min={[round(v) for v in mn]} max={[round(v) for v in mx]}")
print(f"EXTENT mm={[round(v) for v in ext]} = X {ext[0]/1000:.1f}m Y {ext[1]/1000:.1f}m Z {ext[2]/1000:.1f}m")
print(f"meshes={len(g2.get('meshes',[]))} sha256 will be computed separately")
print("GLB_PATH=", os.path.abspath(newest))
