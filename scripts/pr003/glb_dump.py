import json, struct, os

path = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-LOCAL-EXTERNAL-SERVICES-READINESS-001\fixed_api_glb.glb"
data = open(path, "rb").read()
magic, ver, length = struct.unpack("<III", data[:12])
assert magic == 0x46546C67, "not GLB"
off = 12
# JSON chunk
clen, ctype = struct.unpack("<II", data[off:off+8]); off += 8
j = json.loads(data[off:off+clen]); off += clen
# BIN chunk
blen, btype = struct.unpack("<II", data[off:off+8]); off += 8
bindata = data[off:off+blen]

bufviews = j.get("bufferViews", [])
accessors = j.get("accessors", [])
meshes = j.get("meshes", [])
nodes = j.get("nodes", [])
scenes = j.get("scenes", [])
scene0 = scenes[0] if scenes else {}
root_nodes = scene0.get("nodes", [])

COMPONENT = {5120: (1, "b"), 5121: (1, "B"), 5122: (2, "h"), 5123: (2, "H"),
             5125: (4, "I"), 5126: (4, "f")}

def read_accessor(ai):
    acc = accessors[ai]
    bv = bufviews[acc["bufferView"]]
    comp = acc["componentType"]
    n, fmt = COMPONENT[comp]
    count = acc["count"]
    stride = bv.get("byteStride", n * 3) if acc.get("type") == "VEC3" else bv.get("byteStride", n)
    out = []
    base = bv.get("byteOffset", 0)
    for i in range(count):
        offv = base + i * stride
        if acc["type"] == "VEC3":
            x, y, z = struct.unpack_from("<3f", bindata, offv)
            out.append((x, y, z))
        elif acc["type"] == "SCALAR":
            v = struct.unpack_from("<f", bindata, offv)[0]
            out.append(v)
    return out

# node world transforms (support matrix or TRS, recursively)
def node_transform(ni, parent=((1,0,0,0),(0,1,0,0),(0,0,1,0),(0,0,0,1))):
    n = nodes[ni]
    if "matrix" in n:
        m = n["matrix"]
        M = [m[0:4], m[4:8], m[8:12], m[12:16]]
    else:
        t = n.get("translation", [0,0,0])
        r = n.get("rotation", [0,0,0,1])
        s = n.get("scale", [1,1,1])
        # build TRS matrix (row-major)
        qx,qy,qz,qw = r
        # rotation matrix
        R = [
            [1-2*(qy*qy+qz*qz), 2*(qx*qy-qz*qw), 2*(qx*qz+qy*qw)],
            [2*(qx*qy+qz*qw), 1-2*(qx*qx+qz*qz), 2*(qy*qz-qx*qw)],
            [2*(qx*qz-qy*qw), 2*(qy*qz+qx*qw), 1-2*(qx*qx+qy*qy)],
        ]
        M = [
            [s[0]*R[0][0], s[0]*R[0][1], s[0]*R[0][2], t[0]],
            [s[1]*R[1][0], s[1]*R[1][1], s[1]*R[1][2], t[1]],
            [s[2]*R[2][0], s[2]*R[2][1], s[2]*R[2][2], t[2]],
            [0,0,0,1],
        ]
    # multiply parent * M
    P = parent
    R = [[sum(P[i][k]*M[k][j] for k in range(4)) for j in range(4)] for i in range(4)]
    return R

def transform_point(R, p):
    x,y,z = p
    return (R[0][0]*x+R[0][1]*y+R[0][2]*z+R[0][3],
            R[1][0]*x+R[1][1]*y+R[1][2]*z+R[1][3],
            R[2][0]*x+R[2][1]*y+R[2][2]*z+R[2][3])

# walk node tree
def walk(ni, R):
    n = nodes[ni]
    R2 = node_transform(ni, R)
    if "mesh" in n:
        m = meshes[n["mesh"]]
        for prim in m["primitives"]:
            pai = prim["attributes"].get("POSITION")
            pts = read_accessor(pai)
            wpts = [transform_point(R2, p) for p in pts]
            name = n.get("name", "unnamed")
            xs = [p[0] for p in wpts]; ys = [p[1] for p in wpts]; zs = [p[2] for p in wpts]
            print(f"NODE {name}: {len(wpts)} verts | X[{min(xs):.2f},{max(xs):.2f}] Y[{min(ys):.2f},{max(ys):.2f}] Z[{min(zs):.2f},{max(zs):.2f}] | center=({sum(xs)/len(xs):.2f},{sum(ys)/len(ys):.2f},{sum(zs)/len(zs):.2f})")
    for c in n.get("children", []):
        walk(c, R2)

print(f"meshes={len(meshes)} nodes={len(nodes)} accessors={len(accessors)}")
for rn in root_nodes:
    walk(rn, ((1,0,0,0),(0,1,0,0),(0,0,1,0),(0,0,0,1)))
