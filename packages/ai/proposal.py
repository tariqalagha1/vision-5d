"""
Vision 5D — Phase 6 AI Proposal Generator
Generates structured design proposals from scene analysis + interpreted requirements.
Supports: simulation engine (deterministic, offline-capable) and LLM provider plugins.
"""
from uuid import UUID, uuid4
from datetime import datetime
from typing import Optional
from packages.ai.contracts import (
    AIDesignProposal, AIProposalOption, AIProposedEdit, AIRecommendation,
    AIInterpretedRequirement, AISceneAnalysis, AIRoomAnalysis,
    AICostBand, AIApprovalState, AIObjective,
)


class ProposalGenerator:
    """Generates design proposals. Provider-abstracted — defaults to simulation."""

    def __init__(self, provider: str = "simulation"):
        self.provider = provider

    def generate(
        self,
        analysis: AISceneAnalysis,
        requirements: AIInterpretedRequirement,
        option_count: int = 2,
    ) -> AIDesignProposal:
        """Generate design proposal with multiple options from analysis + requirements."""

        options = []
        strategies = [
            ("minimal", "Minimal Intervention", "Keep most existing pieces, add essential items only"),
            ("balanced", "Balanced Redesign", "Thoughtful mix of kept and new pieces"),
            ("transformative", "Full Transformation", "Complete redesign for maximum impact"),
        ]

        for i in range(min(option_count, 3)):
            strategy = strategies[i]
            option = self._generate_option(analysis, requirements, strategy[0], strategy[1], strategy[2])
            options.append(option)

        return AIDesignProposal(
            request_id=None,
            analysis_id=analysis.analysis_id,
            interpreted_requirements=requirements,
            options=options,
            provider=self.provider,
            model="v5d-simulation-6.0" if self.provider == "simulation" else "",
            prompt_version="6.0.0",
            input_tokens=len(str(analysis.json())) // 4 if analysis else 0,
            output_tokens=len(str([o.json() for o in options])) // 4,
            latency_ms=0.0,
            approval_state=AIApprovalState.PENDING,
        )

    def _generate_option(
        self,
        analysis: AISceneAnalysis,
        reqs: AIInterpretedRequirement,
        strategy: str,
        name: str,
        summary: str,
    ) -> AIProposalOption:
        """Generate a single design option."""
        edits = []
        furniture_additions = []
        furniture_removals = []
        finish_changes = []
        lighting_changes = []
        camera_changes = []
        advantages = []
        compromises = []

        # ── Furniture strategy ──
        seating_needed = reqs.seating or 4
        style = reqs.style or "modern"
        room_count = len(analysis.rooms)

        for room in analysis.rooms:
            area = room.area_m2
            existing_count = len(room.current_furniture)

            if strategy == "minimal":
                # Keep all existing, add only essential seating
                to_add = max(0, seating_needed - existing_count)
                if to_add > 0:
                    _add_seating(room, to_add, furniture_additions, edits, style)
                advantages.append(f"Preserved {existing_count} existing pieces in {room.label}")
            elif strategy == "balanced":
                # Keep ~60%, replace rest
                keep = max(1, existing_count * 2 // 3)
                remove = existing_count - keep if reqs.furniture_removals_allowed else 0
                for fi in room.current_furniture[remove:remove or None]:
                    if fi.get("label"):
                        furniture_removals.append(fi["label"])
                        edits.append(AIProposedEdit(
                            operation_type="REMOVE_OBJECT",
                            target_object_id=UUID(fi.get("instance_id", str(uuid4()))),
                            object_type="furniture",
                            label=fi.get("label", "Furniture"),
                            before_state={"position": fi.get("position")},
                            rationale=f"Removing {fi.get('label')} to make room for balanced layout",
                            confidence=0.75,
                        ))
                # Add replacement seating
                new_items = max(1, seating_needed // room_count)
                _add_seating(room, new_items, furniture_additions, edits, style)
                _add_accent_table(room, furniture_additions, edits, style)
                advantages.append(f"Balanced redesign of {room.label} ({keep} kept, {new_items} added)")
            elif strategy == "transformative":
                # Remove all existing, full redesign
                if reqs.furniture_removals_allowed:
                    for fi in room.current_furniture:
                        furniture_removals.append(fi.get("label", "Furniture"))
                        edits.append(AIProposedEdit(
                            operation_type="REMOVE_OBJECT",
                            target_object_id=UUID(fi.get("instance_id", str(uuid4()))),
                            object_type="furniture",
                            label=fi.get("label", "Furniture"),
                            rationale=f"Full transformation: removing all existing pieces",
                            confidence=0.9,
                        ))

                # Full seating layout
                total_seats = max(seating_needed, area // 3)
                _add_seating(room, total_seats, furniture_additions, edits, style)
                _add_coffee_table(room, furniture_additions, edits, style)
                _add_side_tables(room, furniture_additions, edits, style)
                if area > 15:
                    _add_storage(room, furniture_additions, edits, style)
                advantages.append(f"Complete transformation of {room.label} ({total_seats} seats)")
                compromises.append(f"All existing furniture removed from {room.label}")

        # ── Finish strategy ──
        if reqs.finishes_allowed:
            finish_sets = {
                "modern": {"floor": "#C4A882", "wall": "#F5F0E8", "ceiling": "#FFFFFF", "floor_type": "wood"},
                "minimal": {"floor": "#E8E8E8", "wall": "#FFFFFF", "ceiling": "#FFFFFF", "floor_type": "concrete"},
                "family": {"floor": "#8B7355", "wall": "#F5E6D3", "ceiling": "#FFFFF0", "floor_type": "carpet"},
                "office": {"floor": "#D3D3D3", "wall": "#E8ECEF", "ceiling": "#FFFFFF", "floor_type": "vinyl"},
                "healthcare": {"floor": "#F5F5DC", "wall": "#FAFFFA", "ceiling": "#FFFFFF", "floor_type": "vinyl"},
            }
            fs = finish_sets.get(style, finish_sets["modern"])
            finish_changes.append(fs)
            edits.append(AIProposedEdit(
                operation_type="CHANGE_FLOOR_FINISH",
                object_type="finish",
                label="Floor Finish",
                after_state=fs,
                rationale=f"{style.title()} floor: {fs['floor_type']} ({fs['floor']})",
                confidence=0.85,
            ))
            edits.append(AIProposedEdit(
                operation_type="CHANGE_WALL_FINISH",
                object_type="finish",
                label="Wall Finish",
                after_state={"color": fs["wall"]},
                rationale=f"{style.title()} wall color",
                confidence=0.85,
            ))
            advantages.append(f"Applied {style} finish palette")

        # ── Lighting strategy ──
        if reqs.lighting_allowed and strategy != "minimal":
            light_sets = {
                "modern": {"color": "#FFFFFF", "intensity": 0.9, "temperature": 4000},
                "minimal": {"color": "#F5F5FF", "intensity": 0.7, "temperature": 5000},
                "family": {"color": "#FFF8DC", "intensity": 1.1, "temperature": 3000},
                "office": {"color": "#FFFFFF", "intensity": 1.0, "temperature": 4500},
                "healthcare": {"color": "#F0FFF0", "intensity": 1.2, "temperature": 5000},
            }
            ls = light_sets.get(style, light_sets["modern"])
            lighting_changes.append(ls)
            edits.append(AIProposedEdit(
                operation_type="CHANGE_LIGHT",
                object_type="light",
                label="Scene Light",
                after_state=ls,
                rationale=f"{style.title()} lighting: {ls['temperature']}K, intensity {ls['intensity']}",
                confidence=0.8,
            ))
            advantages.append(f"Adjusted lighting to {ls['temperature']}K")

        # ── Camera strategy ──
        if reqs.cameras_allowed:
            for room in analysis.rooms:
                cam_edit = AIProposedEdit(
                    operation_type="SAVE_CAMERA_VIEW",
                    object_type="camera",
                    label=f"{room.label} View",
                    after_state={
                        "name": f"{room.label} {style.title()} View",
                        "type": "view",
                    },
                    rationale=f"Save a presentation view of {room.label}",
                    confidence=0.9,
                )
                edits.append(cam_edit)
                camera_changes.append({"name": f"{room.label} View", "room": room.label})
            advantages.append(f"Created {len(analysis.rooms)} camera views")

        # Validate edits
        for edit in edits:
            if edit.operation_type == "REMOVE_OBJECT" and not reqs.furniture_removals_allowed:
                edit.is_valid = False
                edit.validation_issues.append("Furniture removal not permitted by requirements")

        return AIProposalOption(
            name=name,
            summary=summary,
            strategy=strategy,
            affected_rooms=reqs.rooms,
            furniture_additions=furniture_additions,
            furniture_removals=furniture_removals,
            furniture_transforms=[],
            finish_changes=finish_changes,
            lighting_changes=lighting_changes,
            camera_changes=camera_changes,
            advantages=advantages,
            compromises=compromises,
            estimated_cost_band=AICostBand.STANDARD if strategy == "balanced" else
                              AICostBand.ECONOMY if strategy == "minimal" else AICostBand.PREMIUM,
            confidence=0.8,
            proposed_edits=edits,
        )


def _add_seating(room: AIRoomAnalysis, count: int, additions: list, edits: list, style: str):
    """Add seating furniture items to a room."""
    seat_types = {
        "modern": [("Sofa 3-Seater", [2200, 850, 900], "#4A5568"),
                   ("Armchair", [900, 900, 850], "#718096")],
        "minimal": [("Armchair", [900, 900, 850], "#A0AEC0"),
                    ("Bar Stool", [450, 750, 450], "#CBD5E0")],
        "family": [("Sofa 3-Seater", [2200, 850, 900], "#8B6914"),
                   ("Armchair", [900, 900, 850], "#A0522D")],
        "office": [("Office Chair", [600, 1100, 600], "#2D3748"),
                   ("Office Desk", [1400, 750, 700], "#4A5568")],
        "healthcare": [("Armchair", [900, 900, 850], "#F0FFF0"),
                       ("Sofa 3-Seater", [2200, 850, 900], "#E8F5E9")],
    }
    seats = seat_types.get(style, seat_types["modern"])

    for i in range(min(count, 6)):
        seat = seats[i % len(seats)]
        pos = [room.dimensions.get("width_mm", 4000) * 0.3 + i * 800,
               0,
               room.dimensions.get("depth_mm", 3000) * 0.4]
        additions.append({"label": seat[0], "position": pos, "dimensions": seat[1], "color": seat[2]})
        edits.append(AIProposedEdit(
            operation_type="ADD_OBJECT",
            object_type="furniture",
            label=seat[0],
            after_state={
                "label": seat[0], "position": pos, "dimensions": seat[1],
                "color_override": seat[2], "asset_id": str(uuid4()),
            },
            rationale=f"Add {seat[0]} for {style} seating",
            confidence=0.85,
        ))


def _add_coffee_table(room: AIRoomAnalysis, additions: list, edits: list, style: str):
    pos = [room.dimensions.get("width_mm", 4000) * 0.5, 0, room.dimensions.get("depth_mm", 3000) * 0.5]
    additions.append({"label": "Coffee Table", "position": pos, "dimensions": [1200, 450, 600], "color": "#8B7355"})
    edits.append(AIProposedEdit(
        operation_type="ADD_OBJECT", object_type="furniture", label="Coffee Table",
        after_state={"label": "Coffee Table", "position": pos, "dimensions": [1200, 450, 600],
                     "color_override": "#8B7355", "asset_id": str(uuid4())},
        rationale="Central coffee table for seating arrangement",
        confidence=0.8,
    ))


def _add_side_tables(room: AIRoomAnalysis, additions: list, edits: list, style: str):
    for i, x_off in enumerate([-800, 800]):
        pos = [room.dimensions.get("width_mm", 4000) * 0.5 + x_off, 0, room.dimensions.get("depth_mm", 3000) * 0.45]
        additions.append({"label": f"Side Table {i+1}", "position": pos, "dimensions": [500, 500, 400], "color": "#A0522D"})
        edits.append(AIProposedEdit(
            operation_type="ADD_OBJECT", object_type="furniture", label=f"Side Table {i+1}",
            after_state={"label": f"Side Table {i+1}", "position": pos, "dimensions": [500, 500, 400],
                         "color_override": "#A0522D", "asset_id": str(uuid4())},
            rationale="Side table next to seating",
            confidence=0.75,
        ))


def _add_storage(room: AIRoomAnalysis, additions: list, edits: list, style: str):
    pos = [room.dimensions.get("width_mm", 4000) * 0.85, 0, room.dimensions.get("depth_mm", 3000) * 0.2]
    additions.append({"label": "Bookshelf", "position": pos, "dimensions": [900, 2000, 350], "color": "#5C4033"})
    edits.append(AIProposedEdit(
        operation_type="ADD_OBJECT", object_type="furniture", label="Bookshelf",
        after_state={"label": "Bookshelf", "position": pos, "dimensions": [900, 2000, 350],
                     "color_override": "#5C4033", "asset_id": str(uuid4())},
        rationale="Storage for room organization",
        confidence=0.7,
    ))


def _add_accent_table(room: AIRoomAnalysis, additions: list, edits: list, style: str):
    pos = [room.dimensions.get("width_mm", 4000) * 0.7, 0, room.dimensions.get("depth_mm", 3000) * 0.7]
    additions.append({"label": "Accent Table", "position": pos, "dimensions": [800, 500, 500], "color": "#6B4226"})
    edits.append(AIProposedEdit(
        operation_type="ADD_OBJECT", object_type="furniture", label="Accent Table",
        after_state={"label": "Accent Table", "position": pos, "dimensions": [800, 500, 500],
                     "color_override": "#6B4226", "asset_id": str(uuid4())},
        rationale="Accent piece for balanced layout",
        confidence=0.7,
    ))


# Singleton
proposal_generator = ProposalGenerator(provider="simulation")
