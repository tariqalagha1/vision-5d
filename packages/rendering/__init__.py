# Vision 5D — Rendering Package
# Authoritative Blender-based 3D cinematic renderer
from packages.rendering.blender_scene_builder import (
    validate_glb,
    build_blender_script,
    build_blender_command,
    GLBValidationResult,
    MaterialMapping,
    LightConfig,
    CameraShot,
    RenderConfig,
    MATERIAL_PRESETS,
)
