"""PR003 diagnostic: is to_track_quat('-Z','Y') aiming the camera correctly?
Renders shot_05 midpoint with both aim methods + prints camera forward vectors."""
import bpy, os, sys
from mathutils import Vector, Matrix

GLB = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-LOCAL-EXTERNAL-SERVICES-READINESS-001\fixed_api_glb.glb"
OUT = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-PROCESS-REPAIR-003"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)

obs = [o for o in bpy.data.objects if o.type == "MESH"]

# materials
def make_mat(name, color, rough):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        bsdf = m.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        m.node_tree.links.new(bsdf.outputs["BSDF"], m.node_tree.nodes["Material Output"].inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = rough
    return m

mf = make_mat("F", (0.45,0.32,0.20,1), 0.6)
mw = make_mat("W", (0.90,0.89,0.86,1), 0.9)
ms = make_mat("S", (0.35,0.45,0.55,1), 0.9)
mt = make_mat("T", (0.30,0.20,0.13,1), 0.5)

for o in obs:
    n = o.name.lower()
    xs = [o.matrix_world @ v.co for v in o.data.vertices]
    cy = sum(v.y for v in xs)/len(xs)
    if o.data.materials: o.data.materials.clear()
    if "floor" in n: o.data.materials.append(mf)
    elif "wall" in n: o.data.materials.append(mw)
    elif "furniture" in n:
        o.data.materials.append(ms if cy < -2.6 else mt)
    else: o.data.materials.append(mw)

# world + lights
sc = bpy.context.scene
sc.world = bpy.data.worlds.new("W")
sc.world.use_nodes = True
nt = sc.world.node_tree
for n in list(nt.nodes): nt.nodes.remove(n)
bg = nt.nodes.new("ShaderNodeBackground"); bg.inputs["Color"].default_value=(0.6,0.7,0.9,1); bg.inputs["Strength"].default_value=1.0
outn = nt.nodes.new("ShaderNodeOutputWorld"); nt.links.new(bg.outputs["Background"], outn.inputs["Surface"])
bpy.ops.object.light_add(type="SUN", location=(10,-10,12)); bpy.context.object.data.energy=5.0; bpy.context.object.data.angle=0.2
bpy.ops.object.light_add(type="AREA", location=(2.5,-2,6)); bpy.context.object.data.energy=250.0; bpy.context.object.data.size=9.0

# camera
bpy.ops.object.camera_add(location=(0,0,3))
cam = bpy.context.object; sc.camera = cam
cam.data.clip_end=200.0; cam.data.clip_start=0.05
sc.render.engine="CYCLES"; sc.cycles.device="CPU"; sc.cycles.samples=2; sc.cycles.use_denoising=True
sc.render.resolution_x=640; sc.render.resolution_y=360; sc.render.image_settings.file_format="PNG"

eye = Vector((2.5,-2.6,2.0)); tgt = Vector((2.5,-2.5,0.8))

def aim_quat(cam, target):
    d = (Vector(target) - cam.location).normalized()
    cam.rotation_quaternion = d.to_track_quat('-Z','Y')

def aim_euler(cam, target):
    d = (Vector(target) - cam.location).normalized()
    cam.rotation_euler = d.to_track_quat('-Z','Y').to_euler()

def look_at(cam, eye, target):
    eye=Vector(eye); target=Vector(target); up=Vector((0,0,1))
    fwd=(target-eye).normalized()
    right=fwd.cross(up).normalized()
    if right.length<1e-6: right=Vector((1,0,0))
    up2=right.cross(fwd).normalized()
    m=Matrix(((right.x,right.y,right.z,0),(up2.x,up2.y,up2.z,0),(-fwd.x,-fwd.y,-fwd.z,0),(eye.x,eye.y,eye.z,1)))
    cam.matrix_world = m

def fwd_vec(cam):
    # camera looks along -Z local; world forward = -localZ
    m = cam.matrix_world
    lz = Vector((m[0][2], m[1][2], m[2][2]))  # local Z axis in world
    return -lz

# A: euler to_track_quat
cam.location = eye; aim_euler(cam, tgt)
sc.render.filepath = os.path.join(OUT, "diag_A_euler.png")
bpy.ops.render.render(write_still=True)
print("A euler   rot:", [round(x,3) for x in cam.rotation_euler], "fwd:", [round(x,3) for x in fwd_vec(cam)])

# B: quaternion to_track_quat
cam.location = eye; aim_quat(cam, tgt)
sc.render.filepath = os.path.join(OUT, "diag_B_quat.png")
bpy.ops.render.render(write_still=True)
print("B quat    rot:", [round(x,3) for x in cam.rotation_quaternion], "fwd:", [round(x,3) for x in fwd_vec(cam)])

# C: matrix look_at
look_at(cam, eye, tgt)
sc.render.filepath = os.path.join(OUT, "diag_C_matrix.png")
bpy.ops.render.render(write_still=True)
print("C matrix  fwd:", [round(x,3) for x in fwd_vec(cam)])

print("expected fwd (eye->tgt):", [round(x,3) for x in (tgt-eye).normalized()])
print("DONE")
