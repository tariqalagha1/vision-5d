"""
Vision 5D — Blender Scene Builder
Builds authoritative Blender scenes from validated GLB + pipeline metadata.
Does NOT create substitute geometry. All geometry comes from the GLB.
"""
import json
import os
import struct
import hashlib
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path


@dataclass
class GLBValidationResult:
    """Structural GLB validation result."""
    valid: bool
    magic: str = ""
    version: int = 0
    json_chunk_size: int = 0
    bin_chunk_size: int = 0
    accessor_count: int = 0
    buffer_view_count: int = 0
    vertex_count: int = 0
    index_count: int = 0
    mesh_count: int = 0
    node_count: int = 0
    material_count: int = 0
    has_bounding_box: bool = False
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


@dataclass
class MaterialMapping:
    """Maps Vision 5D material spec to Blender material."""
    name: str
    base_color: tuple = (0.8, 0.8, 0.8, 1.0)
    roughness: float = 0.5
    metallic: float = 0.0
    transmission: float = 0.0
    emission: tuple = (0.0, 0.0, 0.0, 1.0)


@dataclass
class LightConfig:
    """Vision 5D light → Blender light mapping."""
    light_type: str  # SUN, POINT, AREA, SPOT
    position: tuple = (0, 0, 5)
    rotation: tuple = (0, 0, 0)
    intensity: float = 1.0
    color_temperature: int = 5500
    color: tuple = (1.0, 1.0, 1.0)


@dataclass
class CameraShot:
    """Cinematic camera definition."""
    name: str
    shot_type: str  # static, orbit, dolly, walkthrough, crane, pan
    position_start: tuple = (5, 3, 5)
    position_end: tuple = (5, 3, 5)
    target: tuple = (0, 0, 1)
    fov: float = 60.0
    frame_start: int = 1
    frame_end: int = 90
    interpolation: str = "BEZIER"


@dataclass
class RenderConfig:
    """Render settings for Blender."""
    engine: str = "BLENDER_EEVEE"
    resolution_x: int = 1920
    resolution_y: int = 1080
    fps: int = 30
    samples: int = 64
    use_gpu: bool = False
    color_management: str = "Filmic"
    output_format: str = "PNG"
    preview_resolution_x: int = 1280
    preview_resolution_y: int = 720
    preview_samples: int = 16
    preview_duration_seconds: int = 5


# ═══════════════════════════════════════════════════════════
# MATERIAL PRESETS
# ═══════════════════════════════════════════════════════════

MATERIAL_PRESETS = {
    "wood_light": MaterialMapping("Wood Light", base_color=(0.76, 0.60, 0.42, 1.0), roughness=0.6, metallic=0.0),
    "wood_dark": MaterialMapping("Wood Dark", base_color=(0.35, 0.20, 0.10, 1.0), roughness=0.5, metallic=0.0),
    "paint_white": MaterialMapping("Paint White", base_color=(0.92, 0.92, 0.92, 1.0), roughness=0.4, metallic=0.0),
    "paint_warm": MaterialMapping("Paint Warm", base_color=(0.95, 0.90, 0.82, 1.0), roughness=0.4, metallic=0.0),
    "aluminum": MaterialMapping("Aluminum", base_color=(0.75, 0.75, 0.78, 1.0), roughness=0.3, metallic=0.9),
    "glass": MaterialMapping("Glass", base_color=(0.9, 0.95, 1.0, 0.3), roughness=0.05, metallic=0.0, transmission=0.9),
    "concrete": MaterialMapping("Concrete", base_color=(0.65, 0.63, 0.60, 1.0), roughness=0.8, metallic=0.0),
    "marble": MaterialMapping("Marble", base_color=(0.90, 0.88, 0.85, 1.0), roughness=0.2, metallic=0.05),
    "fabric": MaterialMapping("Fabric", base_color=(0.70, 0.68, 0.65, 1.0), roughness=0.9, metallic=0.0),
    "default": MaterialMapping("Default", base_color=(0.8, 0.8, 0.8, 1.0), roughness=0.5, metallic=0.0),
}


# ═══════════════════════════════════════════════════════════
# GLB VALIDATION
# ═══════════════════════════════════════════════════════════

def validate_glb(glb_path: str) -> GLBValidationResult:
    """Validate GLB structural integrity before Blender import."""
    result = GLBValidationResult(valid=False)

    if not os.path.exists(glb_path):
        result.errors.append(f"GLB file not found: {glb_path}")
        return result

    file_size = os.path.getsize(glb_path)
    if file_size < 28:
        result.errors.append(f"GLB too small: {file_size} bytes (min 28)")
        return result

    with open(glb_path, "rb") as f:
        # glTF magic
        magic = f.read(4)
        result.magic = magic.hex()
        if magic != b"glTF":
            result.errors.append(f"Invalid magic: {magic.hex()}, expected 676c5446")
            return result

        version = struct.unpack("<I", f.read(4))[0]
        result.version = version
        if version != 2:
            result.errors.append(f"Unsupported version: {version}, expected 2")

        total_length = struct.unpack("<I", f.read(4))[0]
        if total_length != file_size:
            result.warnings.append(f"Length mismatch: header={total_length}, file={file_size}")

        # Parse chunks
        while f.tell() < total_length:
            chunk_length = struct.unpack("<I", f.read(4))[0]
            chunk_type = f.read(4).decode("ascii", errors="replace")
            if chunk_type == "JSON":
                result.json_chunk_size = chunk_length
            elif chunk_type == "BIN\0":
                result.bin_chunk_size = chunk_length
            f.seek(chunk_length, 1)

    if result.bin_chunk_size == 0:
        result.errors.append("BIN chunk is empty — no geometry data")

    # Parse JSON chunk for counts
    if result.json_chunk_size > 0:
        with open(glb_path, "rb") as f:
            f.seek(20)
            json_data = json.loads(f.read(result.json_chunk_size))
            result.accessor_count = len(json_data.get("accessors", []))
            result.buffer_view_count = len(json_data.get("bufferViews", []))
            result.mesh_count = len(json_data.get("meshes", []))
            result.node_count = len(json_data.get("nodes", []))
            result.material_count = len(json_data.get("materials", []))

            # Count vertices and indices from accessors
            for acc in json_data.get("accessors", []):
                if acc.get("type") == "VEC3" and "POSITION" in (acc.get("name", "") or ""):
                    result.vertex_count += acc.get("count", 0)
                elif acc.get("type") == "SCALAR" and acc.get("componentType", 0) in [5123, 5125]:
                    result.index_count += acc.get("count", 0)
                elif acc.get("type") == "VEC3":
                    result.vertex_count += acc.get("count", 0)

            # Check bounding box on nodes
            for node in json_data.get("nodes", []):
                if node.get("mesh") is not None and "translation" in node:
                    result.has_bounding_box = True
                    break

    # Final validation
    if result.accessor_count == 0:
        result.errors.append("No accessors — GLB has no data arrays")
    if result.mesh_count == 0:
        result.errors.append("No meshes — GLB contains no geometry")
    if result.vertex_count == 0:
        result.errors.append("Zero vertices — no geometry to render")

    result.valid = len(result.errors) == 0
    return result


# ═══════════════════════════════════════════════════════════
# BLENDER SCENE BUILDER (produces Python script for Blender)
# ═══════════════════════════════════════════════════════════

def build_blender_script(
    glb_path: str,
    output_dir: str,
    materials: dict,
    lighting: dict,
    cinematic: dict,
    render_config: RenderConfig = None,
    preview: bool = False,
) -> str:
    """
    Generate a self-contained Blender Python script that:
    1. Imports the validated GLB
    2. Applies materials, lighting, cameras
    3. Renders frames
    4. Saves .blend file
    """
    rc = render_config or RenderConfig()
    res_x = rc.preview_resolution_x if preview else rc.resolution_x
    res_y = rc.preview_resolution_y if preview else rc.resolution_y
    samples = rc.preview_samples if preview else rc.samples

    # Build material nodes
    material_assignments = []
    for slot, mat_name in materials.items():
        preset = MATERIAL_PRESETS.get(mat_name, MATERIAL_PRESETS["default"])
        material_assignments.append({
            "slot": slot,
            "name": preset.name,
            "base_color": list(preset.base_color),
            "roughness": preset.roughness,
            "metallic": preset.metallic,
        })

    # Build lights
    lights = []
    if lighting.get("interior_lights", True):
        lights.append({"type": "POINT", "position": [0, 3, 3], "intensity": 100, "color_temp": lighting.get("color_temperature", 4000)})
        lights.append({"type": "POINT", "position": [3, 3, -2], "intensity": 80, "color_temp": lighting.get("color_temperature", 4000)})
    lights.append({
        "type": "SUN",
        "position": [5, 10, 5],
        "intensity": lighting.get("daylight_intensity", 1.0) * 5,
        "rotation": [0.5, 0.3, 0.8] if lighting.get("time_of_day") == "afternoon" else [0.8, 0.1, 0.5],
    })

    # Build cameras
    shots = []
    shot_types = cinematic.get("shots", ["orbit"])
    fov = cinematic.get("fov", 60)
    duration = cinematic.get("duration", 30)
    frames_per_shot = max(30, int((duration * rc.fps) / max(len(shot_types), 1)))

    for i, shot_type in enumerate(shot_types):
        start_frame = i * frames_per_shot + 1
        end_frame = start_frame + frames_per_shot - 1
        shots.append({
            "name": f"Shot_{i+1}_{shot_type}",
            "type": shot_type,
            "frame_start": start_frame,
            "frame_end": end_frame,
            "fov": fov,
        })

    # Generate the Blender Python script
    # Use forward slashes in docstring to avoid \U unicode escape issues on Windows
    safe_glb = glb_path.replace("\\", "/")
    safe_out = output_dir.replace("\\", "/")
    script = f'''"""
Vision 5D — Blender Render Script (auto-generated)
Source GLB: {safe_glb}
Preview: {preview}
Resolution: {res_x}x{res_y}
"""
import bpy
import json
import os
import sys
from math import radians, sin, cos, pi
from mathutils import Vector, Euler

# ══ CONFIG ══
GLB_PATH = {json.dumps(glb_path)}
OUTPUT_DIR = {json.dumps(output_dir)}
RES_X = {res_x}
RES_Y = {res_y}
FPS = {rc.fps}
SAMPLES = {samples}
PREVIEW = {preview}

MATERIALS = {json.dumps(material_assignments, indent=2)}
LIGHTS = {json.dumps(lights, indent=2)}
SHOTS = {json.dumps(shots, indent=2)}

# ══ CLEAR SCENE ══
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Clear orphan data
for block in bpy.data.meshes:
    bpy.data.meshes.remove(block)
for block in bpy.data.materials:
    bpy.data.materials.remove(block)
for block in bpy.data.lights:
    bpy.data.lights.remove(block)

# ══ IMPORT GLB ══
print(f"[V5D] Importing GLB: {{GLB_PATH}}")
bpy.ops.import_scene.gltf(filepath=GLB_PATH)

# Count imported objects
imported_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
imported_count = len(imported_objects)
print(f"[V5D] Imported {{imported_count}} mesh objects")

if imported_count == 0:
    print("[V5D] ERROR: No geometry imported from GLB!")
    sys.exit(1)

# ══ WORLD BACKGROUND ══
world = bpy.data.worlds.new("V5D_World")
bpy.context.scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs["Color"].default_value = (0.05, 0.05, 0.08, 1.0)
    bg.inputs["Strength"].default_value = 0.3

# ══ APPLY MATERIALS ══
print(f"[V5D] Applying {{len(MATERIALS)}} materials...")
for mat_spec in MATERIALS:
    mat = bpy.data.materials.new(name=mat_spec["name"])
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = tuple(mat_spec["base_color"])
        bsdf.inputs["Roughness"].default_value = mat_spec["roughness"]
        bsdf.inputs["Metallic"].default_value = mat_spec["metallic"]

# ══ ADD LIGHTS ══
print(f"[V5D] Adding {{len(LIGHTS)}} lights...")
for i, light_spec in enumerate(LIGHTS):
    light_data = bpy.data.lights.new(name=f"V5D_Light_{{i}}", type=light_spec["type"])
    light_data.energy = light_spec.get("intensity", 100)
    light_obj = bpy.data.objects.new(name=f"V5D_Light_{{i}}", object_data=light_data)
    bpy.context.collection.objects.link(light_obj)
    pos = light_spec.get("position", [0, 0, 5])
    light_obj.location = Vector(pos)
    if "rotation" in light_spec:
        light_obj.rotation_euler = Euler(light_spec["rotation"])

# ══ CREATE CAMERAS + ANIMATION ══
print(f"[V5D] Creating {{len(SHOTS)}} camera shots...")
bpy.context.scene.render.fps = FPS
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = SHOTS[-1]["frame_end"] if SHOTS else 90

for shot in SHOTS:
    cam_data = bpy.data.cameras.new(name=shot["name"])
    cam_data.lens_unit = 'FOV'
    cam_data.angle = radians(shot.get("fov", 60))
    cam_obj = bpy.data.objects.new(name=shot["name"], object_data=cam_data)
    bpy.context.collection.objects.link(cam_obj)

    # Set initial position
    start_frame = shot["frame_start"]
    end_frame = shot["frame_end"]
    shot_type = shot.get("type", "static")

    if shot_type == "orbit":
        cam_obj.location = Vector((5, -5, 3))
        cam_obj.keyframe_insert(data_path="location", frame=start_frame)
        cam_obj.location = Vector((-5, 5, 3))
        cam_obj.keyframe_insert(data_path="location", frame=end_frame)
    elif shot_type == "walkthrough":
        cam_obj.location = Vector((-3, 4, 1.7))
        cam_obj.keyframe_insert(data_path="location", frame=start_frame)
        cam_obj.location = Vector((3, -4, 1.7))
        cam_obj.keyframe_insert(data_path="location", frame=end_frame)
    elif shot_type == "dolly":
        cam_obj.location = Vector((0, 6, 1.5))
        cam_obj.keyframe_insert(data_path="location", frame=start_frame)
        cam_obj.location = Vector((0, -6, 1.5))
        cam_obj.keyframe_insert(data_path="location", frame=end_frame)
    elif shot_type == "crane":
        cam_obj.location = Vector((0, -8, 1))
        cam_obj.keyframe_insert(data_path="location", frame=start_frame)
        cam_obj.location = Vector((0, -2, 6))
        cam_obj.keyframe_insert(data_path="location", frame=end_frame)
    elif shot_type == "reveal":
        cam_obj.location = Vector((-6, 0, 1.5))
        cam_obj.rotation_euler = Euler((radians(90), 0, radians(90)))
        cam_obj.keyframe_insert(data_path="location", frame=start_frame)
        cam_obj.location = Vector((0, 0, 1.5))
        cam_obj.rotation_euler = Euler((radians(90), 0, radians(0)))
        cam_obj.keyframe_insert(data_path="location", frame=end_frame)
        cam_obj.keyframe_insert(data_path="rotation_euler", frame=end_frame)
    else:  # static
        cam_obj.location = Vector((3, -3, 3))
        cam_obj.keyframe_insert(data_path="location", frame=start_frame)

    # Point at scene center
    look_at = Vector((0, 0, 1.2))
    direction = look_at - cam_obj.location
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    if shot_type != "reveal":
        cam_obj.keyframe_insert(data_path="rotation_euler", frame=start_frame)

    # Set as scene camera for this shot
    if shot == SHOTS[0]:
        bpy.context.scene.camera = cam_obj

# ══ RENDER SETTINGS ══
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = RES_X
scene.render.resolution_y = RES_Y
scene.render.resolution_percentage = 100
scene.render.film_transparent = False
scene.eevee.taa_render_samples = SAMPLES

# Color management
scene.view_settings.view_transform = 'Filmic'
scene.view_settings.look = 'Medium High Contrast'

# Output
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
os.makedirs(OUTPUT_DIR, exist_ok=True)
scene.render.filepath = os.path.join(OUTPUT_DIR, "frame_")

# ══ SAVE .BLEND ══
blend_path = os.path.join(OUTPUT_DIR, "scene.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
print(f"[V5D] Saved .blend: {{blend_path}}")

# ══ RENDER FRAMES ══
print(f"[V5D] Rendering frames {{scene.frame_start}}-{{scene.frame_end}} at {{RES_X}}x{{RES_Y}}...")
bpy.ops.render.render(animation=True, write_still=False)
print(f"[V5D] Render complete. Frames in: {{OUTPUT_DIR}}")
'''

    return script


def build_blender_command(
    script_path: str,
    blender_exe: str = "blender",
    background: bool = True,
) -> list:
    """Build the Blender command-line invocation."""
    cmd = [blender_exe]
    if background:
        cmd.append("--background")
    cmd.extend(["--python", script_path])
    return cmd
