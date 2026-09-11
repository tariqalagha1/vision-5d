"""
Vision 5D — Blender Cycles Living Room — Interior Camera
Camera inside the room at eye level, looking at the sofa.
"""
import bpy, os, math

OUT = r"C:\Users\admin\workspaces\vision-5d\evidence\V5D-LOCAL-EXTERNAL-SERVICES-READINESS-001\render_frames"
F, W, H, S = 30, 1280, 720, 32
os.makedirs(OUT, exist_ok=True)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for m in list(bpy.data.materials): bpy.data.materials.remove(m)

scene = bpy.context.scene
scene.render.engine = 'CYCLES'; scene.cycles.device = 'CPU'
scene.cycles.samples = S; scene.cycles.use_denoising = True
scene.render.resolution_x = W; scene.render.resolution_y = H
scene.render.fps = F; scene.frame_start = 1; scene.frame_end = F
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = os.path.join(OUT, 'frame_')

def mat(name, r, g, b, rough=0.6):
    m = bpy.data.materials.new(name); m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (r,g,b,1)
    m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = rough
    return m

M_FLR = mat("Floor",  0.55, 0.40, 0.25, 0.4)
M_WAL = mat("Wall",   0.93, 0.89, 0.82, 0.8)
M_SOF = mat("Sofa",   0.30, 0.27, 0.25, 0.6)

def box(n, p, s, m):
    bpy.ops.mesh.primitive_cube_add(size=1, location=p)
    o = bpy.context.object; o.name = n; o.scale = s; o.data.materials.append(m)
    return o

# Room: 5m wide, 4m deep, 2.7m high
# Floor
box("floor", (2.5, 0, 2.0), (2.5, 0.05, 2.0), M_FLR)
# Walls including back wall for realism
box("back",  (2.5, 1.35, 4.05), (2.6, 1.35, 0.05), M_WAL)  # back wall
box("left",  (-0.05, 1.35, 2.0), (0.05, 1.35, 2.1), M_WAL)
box("right", (5.05, 1.35, 2.0),  (0.05, 1.35, 2.1), M_WAL)
# Ceiling
box("ceil",  (2.5, 2.72, 2.0),  (2.6, 0.03, 2.1), mat("Ceil", 0.95,0.93,0.90,0.9))

# Sofa against back wall
box("sofa", (2.5, 0.3, 3.3), (1.1, 0.3, 0.45), M_SOF)

print("Room built: floor + 3 walls + ceiling + sofa")

# ── Lighting ──
sun = bpy.data.lights.new('S', 'SUN'); sun.energy = 5
so = bpy.data.objects.new('S', sun); scene.collection.objects.link(so)
so.location = (7, -4, 10); so.rotation_euler = (math.radians(45),0,math.radians(30))

area = bpy.data.lights.new('A', 'AREA'); area.energy = 100; area.size = 2
ao = bpy.data.objects.new('A', area); scene.collection.objects.link(ao)
ao.location = (2.5, -1, 2.0); ao.rotation_euler = (math.radians(90),0,0)

w = bpy.data.worlds['World']; w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.88,0.88,0.9,1)
w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.4

# ── Camera inside room at eye level ──
cam = bpy.data.cameras.new('C'); cam.lens = 24
co = bpy.data.objects.new('C', cam)
scene.collection.objects.link(co); scene.camera = co

tgt = bpy.data.objects.new('T', None)
scene.collection.objects.link(tgt); tgt.location = (2.5, 0.8, 3.3)

tc = co.constraints.new(type='TRACK_TO')
tc.target = tgt; tc.track_axis = 'TRACK_NEGATIVE_Z'; tc.up_axis = 'UP_Y'

# Orbit from inside room
for f in range(1, F+1):
    scene.frame_set(f)
    t = (f-1)/(F-1)
    a = -0.25 + t*0.5  # -14 to +14 deg
    co.location = (2.5 + 3.5*math.sin(a), -2.0 + t*1.5, 1.5)
    co.keyframe_insert(data_path='location', frame=f)

print(f"Rendering {F} frames...")
bpy.ops.render.render(animation=True, write_still=True)
done = len([x for x in os.listdir(OUT) if x.startswith('frame_') and x.endswith('.png')])
print(f"DONE: {done}/{F}")
