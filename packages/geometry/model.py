"""
Vision 5D — Phase 3 Editable Floor-Plan Model + User Corrections
"""
from uuid import UUID, uuid4
from datetime import datetime
from copy import deepcopy
from packages.geometry.contracts import (
    GeometryModel, FloorGeometry, WallBody, RoomGeometry, Opening,
    WallCenterline, WallJunction, Point2D,
    EditOperation, EditType, EditHistory,
    GeometryState, OpeningType, OpeningSwing,
    ScaleCalibrationResult, TopologyGraph, ConstraintGraph,
    RepairLog, AmbiguityReport, ValidationReport, GeometryMetrics,
)


class EditableGeometryModel:
    """The authoritative editable metric floor-plan model with undo/redo."""

    def __init__(self):
        self._model: GeometryModel | None = None
        self._undo_stack: list[dict] = []  # snapshots
        self._redo_stack: list[dict] = []

    def initialize(self, project_id: UUID, source_graph_id: UUID,
                   calibration: ScaleCalibrationResult = None) -> GeometryModel:
        self._model = GeometryModel(
            project_id=project_id,
            source_graph_id=source_graph_id,
            calibration=calibration,
            version=1,
        )
        self._undo_stack = []
        self._redo_stack = []
        return self._model

    def add_floor(self, floor: FloorGeometry):
        if self._model:
            self._model.floors.append(floor)
            self._model.version += 1

    def get_floor(self, floor_id: UUID = None) -> FloorGeometry | None:
        if not self._model or not self._model.floors: return None
        if floor_id:
            return next((f for f in self._model.floors if f.floor_id == floor_id), None)
        return self._model.floors[0]

    @property
    def model(self) -> GeometryModel | None:
        return self._model

    # ═══════════════════════════ Edit Operations ═══════════════════════════

    def _save_snapshot(self) -> dict:
        """Save current state for undo."""
        if not self._model: return {}
        snapshot = {
            "version": self._model.version,
            "floors": deepcopy([f.model_dump() for f in self._model.floors]),
        }
        self._undo_stack.append(snapshot)
        self._redo_stack.clear()
        return snapshot

    def undo(self) -> bool:
        if not self._undo_stack or not self._model: return False
        # Save current state to redo stack directly (don't push to undo)
        current = {
            "version": self._model.version,
            "floors": deepcopy([f.model_dump() for f in self._model.floors]),
        }
        self._redo_stack.append(current)
        snapshot = self._undo_stack.pop()
        self._restore_snapshot(snapshot)
        return True

    def redo(self) -> bool:
        if not self._redo_stack or not self._model: return False
        # Save current state to undo stack
        current = {
            "version": self._model.version,
            "floors": deepcopy([f.model_dump() for f in self._model.floors]),
        }
        self._undo_stack.append(current)
        snapshot = self._redo_stack.pop()
        self._restore_snapshot(snapshot)
        return True

    def _restore_snapshot(self, snapshot: dict):
        if not self._model: return
        self._model.version = snapshot["version"]
        self._model.floors = [FloorGeometry(**f) for f in snapshot["floors"]]
        # Rebind any external references by replacing floor contents
        # (external references to old floor objects won't see changes)

    # Wall operations
    def add_wall(self, floor_id: UUID, centerline: list[Point2D],
                 thickness: float = 120.0) -> WallBody | None:
        floor = self.get_floor(floor_id)
        if not floor: return None
        self._save_snapshot()

        cl = WallCenterline(points=centerline, state=GeometryState.MANUALLY_CORRECTED)
        from packages.geometry.primitives import wall_body_builder
        body = wall_body_builder.build(cl, thickness)
        floor.walls.append(body)
        self._model.version += 1
        self._model.updated_at = datetime.utcnow()
        return body

    def move_wall_endpoint(self, floor_id: UUID, wall_id: UUID,
                           endpoint_index: int, new_pos: Point2D) -> bool:
        floor = self.get_floor(floor_id)
        if not floor: return False
        wall = next((w for w in floor.walls if w.body_id == wall_id), None)
        if not wall or endpoint_index >= len(wall.centerline): return False

        self._save_snapshot()
        wall.centerline[endpoint_index] = new_pos

        # Rebuild body
        from packages.geometry.primitives import wall_body_builder
        cl = WallCenterline(points=wall.centerline, centerline_id=wall.centerline_id,
                           state=GeometryState.MANUALLY_CORRECTED)
        new_body = wall_body_builder.build(cl, wall.thickness)

        idx = floor.walls.index(wall)
        floor.walls[idx] = new_body
        self._model.version += 1
        self._model.updated_at = datetime.utcnow()
        return True

    def change_wall_thickness(self, floor_id: UUID, wall_id: UUID,
                              new_thickness: float) -> bool:
        floor = self.get_floor(floor_id)
        if not floor: return False
        wall = next((w for w in floor.walls if w.body_id == wall_id), None)
        if not wall: return False

        self._save_snapshot()
        from packages.geometry.primitives import wall_body_builder
        cl = WallCenterline(points=wall.centerline, centerline_id=wall.centerline_id)
        new_body = wall_body_builder.build(cl, new_thickness)
        new_body.state = GeometryState.MANUALLY_CORRECTED

        idx = floor.walls.index(wall)
        floor.walls[idx] = new_body
        self._model.version += 1
        self._model.updated_at = datetime.utcnow()
        return True

    def remove_wall(self, floor_id: UUID, wall_id: UUID) -> bool:
        floor = self.get_floor(floor_id)
        if not floor: return False
        wall = next((w for w in floor.walls if w.body_id == wall_id), None)
        if not wall: return False

        self._save_snapshot()
        floor.walls.remove(wall)
        # Remove references from rooms
        for room in floor.rooms:
            if wall_id in room.wall_ids:
                room.wall_ids.remove(wall_id)
        self._model.version += 1
        self._model.updated_at = datetime.utcnow()
        return True

    # Room operations
    def rename_room(self, floor_id: UUID, room_id: UUID, new_label: str) -> bool:
        floor = self.get_floor(floor_id)
        if not floor: return False
        room = next((r for r in floor.rooms if r.room_id == room_id), None)
        if not room: return False
        self._save_snapshot()
        room.label = new_label
        self._model.version += 1
        self._model.updated_at = datetime.utcnow()
        return True

    # Opening operations
    def move_opening(self, floor_id: UUID, opening_id: UUID, new_pos_along: float) -> bool:
        floor = self.get_floor(floor_id)
        if not floor: return False
        op = next((o for o in floor.openings if o.opening_id == opening_id), None)
        if not op: return False
        self._save_snapshot()
        op.position_along_wall = max(0.0, min(1.0, new_pos_along))
        self._model.version += 1
        self._model.updated_at = datetime.utcnow()
        return True

    def resize_opening(self, floor_id: UUID, opening_id: UUID, new_width: float) -> bool:
        floor = self.get_floor(floor_id)
        if not floor: return False
        op = next((o for o in floor.openings if o.opening_id == opening_id), None)
        if not op: return False
        self._save_snapshot()
        op.width_mm = new_width
        self._model.version += 1
        self._model.updated_at = datetime.utcnow()
        return True

    # Scale
    def change_scale(self, px_per_mm: float):
        if not self._model: return
        self._save_snapshot()
        self._model.calibration = ScaleCalibrationResult(
            pixels_per_mm=px_per_mm,
            mm_per_pixel=1.0/px_per_mm if px_per_mm > 0 else 0.0,
            method="manual",
            confidence=0.99,
            manual_override=True,
        )
        self._model.version += 1
        self._model.updated_at = datetime.utcnow()

    # Repair
    def accept_repair(self, repair_id: UUID):
        if not self._model or not self._model.repair_log: return
        for action in self._model.repair_log.actions:
            if action.repair_id == repair_id:
                action.is_validated = True
                break

    def reject_repair(self, repair_id: UUID):
        if not self._model or not self._model.repair_log: return
        for action in self._model.repair_log.actions:
            if action.repair_id == repair_id:
                action.reverse()
                self._model.repair_log.accepted -= 1
                self._model.repair_log.rejected += 1
                break

    # Finalization
    def finalize(self):
        if self._model:
            self._model.is_complete = True


editable_model = EditableGeometryModel()
