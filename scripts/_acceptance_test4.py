#!/usr/bin/env python3
"""Full customer flow: upload DXF -> cad/understand -> geometry -> scene3d -> GLB (feet scale)."""
import json, time, urllib.request, http.cookiejar, struct, os, uuid, glob

BASE="http://localhost:8000"
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

print("login..."); post("/api/v1/auth/login", {"provider":"google","oauth_token":"demo"}); print("  ok")

# multipart upload
DXF=r"C:/Users/admin/workspaces/vision-5d/output/RE-SingDetch-FH_AS/geometry/converted.dxf"
print("upload-cad...")
boundary="----v5d"+uuid.uuid4().hex
data=open(DXF,'rb').read()
body=(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"RE-SingDetch-FH_AS.dxf\"\r\n"
      f"Content-Type: application/octet-stream\r\n\r\n").encode()+data+f"\r\n--{boundary}--\r\n".encode()
r=urllib.request.Request(BASE+"/api/v1/assets/upload-cad",data=body,method="POST")
r.add_header("Content-Type",f"multipart/form-data; boundary={boundary}")
up=json.loads(op.open(r,timeout=300).read().decode())
PID=up.get("project_id") or up.get("project",{}).get("id")
print("  project_id", PID)

print("cad/understand...")
r=post(f"/api/v1/projects/{PID}/cad/understand"); cjob=r.get("job_id"); print("  job", cjob)
c=poll(cjob); print("  state", c.get("state"))
gid=(c.get("params") or {}).get("graph_id") or c.get("graph_id")
print("  graph_id", gid, "vector_walls", (c.get("params") or {}).get("vector_walls"))

print("geometry/reconstruct...")
r=post(f"/api/v3/projects/{PID}/geometry/reconstruct?source_graph_id={gid}"); gjob=r.get("job_id")
g=poll(gjob); print("  job", gjob, "state", g.get("state"))

print("scene3d reconstruct...")
r=post(f"/api/v4/projects/{PID}/scene/reconstruct"); sjob=r.get("job_id")
s=poll(sjob); print("  job", sjob, "state", s.get("state"))

# newest GLB
glbs=sorted(glob.glob(".exports/*.glb"), key=os.path.getmtime, reverse=True)
newest=glbs[0]
d=open(newest,'rb').read()
jl=struct.unpack('<I', d[12:16])[0]
g2=json.loads(d[20:20+jl].rstrip(b' ').decode('utf-8'))
mins=[a['min'] for a in g2['accessors'] if a.get('type')=='VEC3' and 'min' in a]
maxs=[a['max'] for a in g2['accessors'] if a.get('type')=='VEC3' and 'max' in a]
mn=[min(v[i] for v in mins) for i in range(3)]; mx=[max(v[i] for v in maxs) for i in range(3)]
ext=[mx[i]-mn[i] for i in range(3)]
print(f"GLB bounds min={[round(v) for v in mn]} max={[round(v) for v in mx]}")
print(f"EXTENT mm={[round(v) for v in ext]} = X {ext[0]/1000:.1f}m Y {ext[1]/1000:.1f}m Z {ext[2]/1000:.1f}m")
print(f"meshes={len(g2.get('meshes',[]))} size={os.path.getsize(newest)}")
print("GLB_PATH=", os.path.abspath(newest))
print("PROJECT_ID=", PID)
