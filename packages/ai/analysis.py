"""
Vision 5D — Phase 6 Scene Analysis Engine
Deterministic analysis of rooms, geometry, furniture, circulation, and constraints.
Produces structured AIRoomAnalysis and AISceneAnalysis for proposal generation.
"""
from uuid import UUID, uuid4
from typing import Optional
from packages.ai.contracts import (
    AIRoomAnalysis, AISceneAnalysis, AIInterpretedRequirement,
    AIObjective, AICostBand,
)


class SceneAnalyzer:
    """Analyzes a Studio scene + draft data for AI proposal generation."""

    def analyze(
        self,
        scene_data: dict,
        draft_data: dict,
        request_text: str = "",
        target_room_ids: list[UUID] = None,
    ) -> AISceneAnalysis:
        rooms_data = scene_data.get("objects", [])
        furniture = draft_data.get("furniture_instances", [])
        finishes = draft_data.get("finishes", {})
        objects_list = scene_data.get("objects", [])

        analyses = []
        total_area = 0.0

        # Build rooms from scene objects
        room_objs = [o for o in objects_list if o.get("type") == "room_volume"]
        wall_objs = [o for o in objects_list if o.get("type") == "wall_solid"]
        door_objs = [o for o in objects_list if o.get("type") == "door_element"]
        window_objs = [o for o in objects_list if o.get("type") == "window_element"]

        target_set = set(str(r) for r in (target_room_ids or []))

        for room in room_objs:
            rid = room.get("id", "")
            if target_set and str(rid) not in target_set:
                continue

            props = room.get("properties", {})
            area = props.get("area_m2", 0) or 0
            total_area += area

            # Room dimensions estimate from bbox
            bbox = props.get("bbox", {})
            dims = {}
            if bbox:
                dims = {
                    "width_mm": abs((bbox.get("max_x", 0) or 0) - (bbox.get("min_x", 0) or 0)),
                    "depth_mm": abs((bbox.get("max_z", 0) or 0) - (bbox.get("min_z", 0) or 0)),
                    "height_mm": abs((bbox.get("max_y", 0) or 0) - (bbox.get("min_y", 0) or 0)),
                }

            # Find doors/windows near this room
            room_bbox = bbox
            room_walls = []
            for w in wall_objs:
                wbbox = w.get("properties", {}).get("bbox", {})
                if wbbox and _bbox_nearby(room_bbox, wbbox, 2000):
                    room_walls.append({
                        "wall_id": w.get("id"),
                        "length_mm": abs((wbbox.get("max_x", 0) or 0) - (wbbox.get("min_x", 0) or 0)),
                        "is_external": w.get("properties", {}).get("is_external", False),
                    })

            # Doors in this room
            nearby_doors = []
            for d in door_objs:
                dbbox = d.get("properties", {}).get("bbox", {})
                if dbbox and _bbox_intersects(room_bbox, dbbox):
                    nearby_doors.append({"door_id": d.get("id"), "width": d.get("properties", {}).get("width", 900)})

            # Windows in this room
            nearby_windows = []
            for w in window_objs:
                wbbox = w.get("properties", {}).get("bbox", {})
                if wbbox and _bbox_intersects(room_bbox, wbbox):
                    nearby_windows.append({"window_id": w.get("id")})

            # Furniture in this room
            room_furniture = []
            for fi in furniture:
                fpos = fi.get("position", [0, 0, 0])
                if room_bbox and _point_in_bbox(fpos, room_bbox):
                    room_furniture.append({
                        "label": fi.get("label", "Furniture"),
                        "position": fpos,
                        "dimensions": fi.get("dimensions", [200, 200, 200]),
                        "color": fi.get("color_override"),
                    })

            # Wall availability (free wall segments for furniture placement)
            free_walls = []
            for w in room_walls:
                occupied = False
                for fi in room_furniture:
                    fpos = fi.get("position", [0, 0, 0])
                    wbbox_local = w.get("bbox") if isinstance(w, dict) else {}
                    # Simplified: check if furniture is near this wall
                    if wbbox_local:
                        pass  # Detailed check would go here
                free_walls.append({"wall_id": w.get("wall_id"), "free": not occupied})

            # Circulation clearance
            clearance = 900  # default mm
            if area < 10:
                clearance = 700
            elif area > 30:
                clearance = 1100

            # Focal points
            focal_points = []
            if nearby_windows:
                focal_points.append({"type": "window", "count": len(nearby_windows)})
            if room.get("label"):
                focal_points.append({"type": "feature_wall", "orientation": "longest"})

            # Constraints
            constraints = []
            if nearby_doors:
                constraints.append(f"Keep {len(nearby_doors)} door(s) clear")
            if room_furniture:
                constraints.append(f"Consider {len(room_furniture)} existing furniture pieces")

            analyses.append(AIRoomAnalysis(
                room_id=UUID(str(rid)),
                label=room.get("label", "Room"),
                function=props.get("function", "unknown"),
                area_m2=area,
                volume_m3=area * 2.5,
                dimensions=dims,
                door_count=len(nearby_doors),
                window_count=len(nearby_windows),
                wall_availability=free_walls[:6],
                current_furniture=room_furniture,
                current_finishes=finishes,
                circulation_clearance_mm=clearance,
                focal_points=focal_points,
                constraints=constraints,
            ))

        return AISceneAnalysis(
            rooms=analyses,
            total_floor_area_m2=total_area,
            furniture_count=len(furniture),
            validation_issues=draft_data.get("placement_issues", []),
        )

    def interpret_requirements(
        self,
        user_text: str,
        objective_str: str,
        analysis: AISceneAnalysis,
        style_preference: str = "",
        budget_band: str = "unspecified",
        seating_capacity: Optional[int] = None,
    ) -> AIInterpretedRequirement:
        """Convert user language + objective into structured requirements."""

        # Map objective string to enum
        obj_map = {
            "furnish_room": AIObjective.FURNISH_ROOM,
            "improve_layout": AIObjective.IMPROVE_LAYOUT,
            "improve_circulation": AIObjective.IMPROVE_CIRCULATION,
            "modern_interior": AIObjective.MODERN_INTERIOR,
            "minimal_interior": AIObjective.MINIMAL_INTERIOR,
            "family_friendly": AIObjective.FAMILY_FRIENDLY,
            "office_layout": AIObjective.OFFICE_LAYOUT,
            "improve_lighting": AIObjective.IMPROVE_LIGHTING,
            "recommend_floor_finishes": AIObjective.RECOMMEND_FLOOR_FINISHES,
            "recommend_wall_finishes": AIObjective.RECOMMEND_WALL_FINISHES,
            "create_camera_views": AIObjective.CREATE_CAMERA_VIEWS,
            "reduce_collisions": AIObjective.REDUCE_COLLISIONS,
            "custom": AIObjective.CUSTOM,
        }
        objective = obj_map.get(objective_str, AIObjective.CUSTOM)

        # Extract style from text
        style = style_preference
        if not style:
            text_lower = user_text.lower()
            if "modern" in text_lower:
                style = "modern"
            elif "minimal" in text_lower:
                style = "minimal"
            elif "family" in text_lower or "comfortable" in text_lower:
                style = "family"
            elif "office" in text_lower:
                style = "office"
            elif "healthcare" in text_lower:
                style = "healthcare"
            else:
                style = "modern"  # default

        # Extract seating capacity from text
        seating = seating_capacity
        if not seating:
            import re
            match = re.search(r'(\d+)\s*(seat|person|people|seater)', user_text, re.IGNORECASE)
            if match:
                seating = int(match.group(1))

        # Determine allowed categories
        furniture_add = objective in {
            AIObjective.FURNISH_ROOM, AIObjective.IMPROVE_LAYOUT,
            AIObjective.IMPROVE_CIRCULATION, AIObjective.MODERN_INTERIOR,
            AIObjective.MINIMAL_INTERIOR, AIObjective.FAMILY_FRIENDLY,
            AIObjective.OFFICE_LAYOUT, AIObjective.BUDGET_FIT,
        }
        furniture_remove = objective in {
            AIObjective.IMPROVE_LAYOUT, AIObjective.MODERN_INTERIOR,
            AIObjective.MINIMAL_INTERIOR, AIObjective.FAMILY_FRIENDLY,
            AIObjective.OFFICE_LAYOUT,
        }
        finishes_allowed = objective in {
            AIObjective.MODERN_INTERIOR, AIObjective.MINIMAL_INTERIOR,
            AIObjective.FAMILY_FRIENDLY, AIObjective.RECOMMEND_FLOOR_FINISHES,
            AIObjective.RECOMMEND_WALL_FINISHES, AIObjective.CUSTOM,
        }
        lighting_allowed = objective in {
            AIObjective.IMPROVE_LIGHTING, AIObjective.MODERN_INTERIOR,
            AIObjective.CUSTOM,
        }
        cameras_allowed = objective in {
            AIObjective.CREATE_CAMERA_VIEWS, AIObjective.CREATE_WALKTHROUGH,
            AIObjective.CUSTOM,
        }

        # Build assumptions
        assumptions = []
        room_labels = [r.label for r in analysis.rooms]
        if room_labels:
            assumptions.append(f"Targeting rooms: {', '.join(room_labels)}")
        if seating:
            assumptions.append(f"Target seating capacity: {seating}")
        assumptions.append(f"Style: {style}")

        return AIInterpretedRequirement(
            objective=objective,
            rooms=room_labels,
            style=style,
            seating=seating,
            budget=AICostBand(budget_band) if budget_band in [b.value for b in AICostBand] else AICostBand.UNSPECIFIED,
            furniture_additions_allowed=furniture_add,
            furniture_removals_allowed=furniture_remove,
            finishes_allowed=finishes_allowed,
            lighting_allowed=lighting_allowed,
            cameras_allowed=cameras_allowed,
            constraints=[{"type": "clearance_mm", "value": r.circulation_clearance_mm} for r in analysis.rooms],
            assumptions=assumptions,
            confidence=0.85,
        )


def _bbox_intersects(a: dict, b: dict) -> bool:
    if not a or not b:
        return False
    return (
        (a.get("min_x", 0) or 0) < (b.get("max_x", 0) or 0) and
        (a.get("max_x", 0) or 0) > (b.get("min_x", 0) or 0) and
        (a.get("min_y", -999) or -999) < (b.get("max_y", 0) or 0) and
        (a.get("max_y", 0) or 0) > (b.get("min_y", -999) or -999) and
        (a.get("min_z", 0) or 0) < (b.get("max_z", 0) or 0) and
        (a.get("max_z", 0) or 0) > (b.get("min_z", 0) or 0)
    )


def _bbox_nearby(a: dict, b: dict, threshold: float) -> bool:
    if not a or not b:
        return False
    # Simple proximity check on XZ plane
    ax = ((a.get("min_x", 0) or 0) + (a.get("max_x", 0) or 0)) / 2
    az = ((a.get("min_z", 0) or 0) + (a.get("max_z", 0) or 0)) / 2
    bx = ((b.get("min_x", 0) or 0) + (b.get("max_x", 0) or 0)) / 2
    bz = ((b.get("min_z", 0) or 0) + (b.get("max_z", 0) or 0)) / 2
    return ((ax - bx) ** 2 + (az - bz) ** 2) ** 0.5 < threshold


def _point_in_bbox(point: list, bbox: dict) -> bool:
    if not bbox or len(point) < 2:
        return False
    return (
        (bbox.get("min_x", -1e9) or -1e9) <= point[0] <= (bbox.get("max_x", 1e9) or 1e9) and
        (bbox.get("min_z", -1e9) or -1e9) <= point[2] <= (bbox.get("max_z", 1e9) or 1e9)
    )


# Singleton
scene_analyzer = SceneAnalyzer()
