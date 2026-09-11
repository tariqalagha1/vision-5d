"""
Vision 5D — Phase 3 Geometry Engine Pipeline Orchestrator
Converts Phase 2 Canonical Architectural Graph → Editable Metric Floor Plan.
"""
import time, structlog
from uuid import UUID, uuid4

from packages.plan_understanding.contracts import (
    ArchitecturalGraph, GraphNodeType, GraphEdgeType,
    PlanUnderstandingResult, ScaleCalibration as P2Scale,
)
from packages.geometry.contracts import (
    GeometryModel, GeometryPipelineResult, FloorGeometry,
    ScaleCalibrationResult, CoordSystem,
    GeometryState, WallCenterline, Point2D,
)
from packages.geometry.primitives import (
    CoordTransformEngine, wall_reconstructor, wall_body_builder,
)
from packages.geometry.thickness import thickness_estimator
from packages.geometry.rooms import room_engine
from packages.geometry.openings import opening_engine
from packages.geometry.scale import scale_calibrator
from packages.geometry.constraints import constraint_engine, geometric_solver
from packages.geometry.topology import topology_engine
from packages.geometry.repair import geom_repair_engine, uncertainty_handler
from packages.geometry.validation import geometry_validator, metrics_calculator
from packages.geometry.model import editable_model

logger = structlog.get_logger()


class GeometryPipeline:
    """Phase 3: Canonical Graph → Editable Geometry Model."""

    def __init__(self):
        self._checkpoints: dict[str, dict] = {}

    def process(self, project_id: UUID,
                phase2_result: PlanUnderstandingResult = None,
                graph: ArchitecturalGraph = None,
                manual_scale: float = None) -> GeometryPipelineResult:
        """Run the complete geometry reconstruction pipeline."""
        t0 = time.time()
        stages_complete = []
        stages_failed = []
        result = GeometryPipelineResult(project_id=project_id)

        try:
            # Resolve input
            if phase2_result and phase2_result.graph:
                graph = phase2_result.graph
            if graph is None:
                raise ValueError("No architectural graph provided")

            result.source_graph_id = graph.graph_id

            # Stage 1: Load canonical graph
            logger.info("p3_stage_load_graph", nodes=len(graph.nodes), edges=len(graph.edges))
            stages_complete.append("load_graph")

            # Extract wall nodes, room nodes, opening nodes
            wall_nodes = [n for n in graph.nodes if n.node_type == GraphNodeType.WALL]
            room_nodes = [n for n in graph.nodes if n.node_type == GraphNodeType.ROOM]
            opening_nodes = [n for n in graph.nodes if n.node_type == GraphNodeType.OPENING]
            dimension_nodes = [n for n in graph.nodes if n.node_type == GraphNodeType.DIMENSION]

            # Stage 2: Initialize coordinate systems
            img_w = graph.metadata.get("width_px", 1200)
            img_h = graph.metadata.get("height_px", 800)
            coord = CoordTransformEngine(image_width=img_w, image_height=img_h, px_per_mm=5.9)
            logger.info("p3_stage_coordinate_systems", width=img_w, height=img_h)
            stages_complete.append("coordinate_systems")

            # Stage 3: Calibrate scale
            p2_scale = graph.scale
            p2_scale_dict = {}
            if p2_scale:
                p2_scale_dict = {
                    "pixels_per_unit": p2_scale.pixels_per_unit,
                    "scale_ratio": p2_scale.scale_ratio,
                    "confidence": p2_scale.confidence,
                    "method": p2_scale.method.value if hasattr(p2_scale.method, 'value') else str(p2_scale.method),
                }

            dim_refs = []
            for dn in dimension_nodes:
                props = dn.properties
                length_px = props.get("length_px", 0) or 0
                if length_px > 0:
                    dim_refs.append({"value_px": length_px, "value_mm": 6000, "confidence": dn.confidence})

            calibration = scale_calibrator.calibrate(p2_scale_dict, dim_refs)
            if manual_scale:
                calibration = scale_calibrator.calibrate(p2_scale_dict, dim_refs,
                                                         {"pixels_per_mm": manual_scale})
            coord.set_scale(calibration.pixels_per_mm)
            logger.info("p3_stage_scale", px_per_mm=calibration.pixels_per_mm,
                        method=calibration.method, confidence=calibration.confidence)
            stages_complete.append("scale_calibrate")

            # Stage 4: Reconstruct wall centerlines
            wall_dicts = []
            for wn in wall_nodes:
                wall_dicts.append({
                    "node_id": str(wn.node_id),
                    "label": wn.label,
                    "properties": wn.properties,
                    "confidence": wn.confidence,
                    "source": wn.source,
                    "detection_ref": str(wn.detection_ref) if wn.detection_ref else None,
                })

            centerlines = wall_reconstructor.reconstruct(wall_dicts, calibration.pixels_per_mm)
            centerlines = wall_reconstructor.merge_fragmented(centerlines)
            centerlines = wall_reconstructor.snap_endpoints(centerlines)
            centerlines = wall_reconstructor.split_intersecting(centerlines)
            logger.info("p3_stage_walls_centerlines", count=len(centerlines))
            stages_complete.append("wall_centerlines")

            # C5: Convert pixel coordinates to metric (mm)
            mm_per_px = calibration.mm_per_pixel
            for cl in centerlines:
                cl.points = [Point2D(x=p.x * mm_per_px, y=p.y * mm_per_px) for p in cl.points]
            logger.info("p3_stage_metric_transform", mm_per_px=mm_per_px)
            stages_complete.append("metric_transform")

            # Stage 5: Estimate wall thickness
            thicknesses = thickness_estimator.estimate_all(centerlines)
            logger.info("p3_stage_thickness", count=len(thicknesses))
            stages_complete.append("wall_thickness")

            # Stage 6: Construct wall bodies
            wall_bodies = []
            for cl in centerlines:
                wt = thickness_estimator.get(cl.centerline_id)
                thickness_mm = wt.value_mm if wt else 120.0
                body = wall_body_builder.build(cl, thickness_mm)
                wall_bodies.append(body)
            logger.info("p3_stage_wall_bodies", count=len(wall_bodies))
            stages_complete.append("wall_bodies")

            # Stage 7: Place openings
            opening_dicts = []
            for on in opening_nodes:
                opening_dicts.append({
                    "node_id": str(on.node_id),
                    "label": on.label,
                    "properties": on.properties,
                    "confidence": on.confidence,
                    "detection_ref": str(on.detection_ref) if on.detection_ref else None,
                })
            openings = opening_engine.place_all(opening_dicts, centerlines, wall_bodies)
            logger.info("p3_stage_openings", count=len(openings))
            stages_complete.append("openings")

            # Stage 8: Generate room polygons
            room_dicts = []
            for rn in room_nodes:
                room_dicts.append({
                    "node_id": str(rn.node_id),
                    "label": rn.label,
                    "properties": rn.properties,
                    "confidence": rn.confidence,
                })
            rooms = room_engine.generate(wall_bodies, openings, room_dicts, centerlines)
            logger.info("p3_stage_rooms", count=len(rooms))
            stages_complete.append("rooms")

            # Stage 9: Build topology
            topology = topology_engine.build(wall_bodies, rooms, openings)
            logger.info("p3_stage_topology", edges=len(topology.edges),
                        consistent=topology.is_consistent)
            stages_complete.append("topology")

            # Stage 10: Apply constraints
            cgraph = constraint_engine.build_constraints(centerlines, wall_bodies, rooms, openings)
            logger.info("p3_stage_constraints", count=len(cgraph.constraints),
                        violations=cgraph.violation_count)
            stages_complete.append("constraints")

            # Stage 11: Run repairs
            junctions = wall_reconstructor.create_junctions(centerlines)
            repair_log = geom_repair_engine.detect_and_repair(
                centerlines, wall_bodies, rooms, openings, junctions)
            logger.info("p3_stage_repairs", count=repair_log.total_repairs)
            stages_complete.append("repairs")

            # Stage 12: Validate geometry
            floor = FloorGeometry(
                walls=wall_bodies, rooms=rooms, openings=openings,
                scale_px_per_mm=calibration.pixels_per_mm,
                units=calibration.units,
                junctions=junctions,
            )
            validation = geometry_validator.validate_all(floor)
            logger.info("p3_stage_validation", pass_count=validation.pass_count,
                        fail_count=validation.fail_count, clean=validation.is_clean)
            stages_complete.append("validation")

            # Stage 13: Calculate metrics
            metrics = metrics_calculator.calculate(floor, source_wall_count=len(wall_dicts))
            stages_complete.append("metrics")

            # Stage 14: Handle uncertainty
            ambiguity = uncertainty_handler.classify_geometry(
                centerlines, wall_bodies, rooms, openings)
            stages_complete.append("ambiguity")

            # Stage 15: Persist editable model
            editable_model.initialize(project_id, graph.graph_id, calibration)
            editable_model.add_floor(floor)
            model = editable_model.model
            if model:
                model.topology = topology
                model.constraints = cgraph
                model.repair_log = repair_log
                model.ambiguity_report = ambiguity
                model.validation = validation
                model.metrics = metrics
                model.is_complete = validation.can_complete
                if not validation.can_complete:
                    model.completeness_issues = [
                        d.description for d in validation.decisions
                        if d.severity == "blocking" and d.decision == "fail"
                    ]
                model.state = GeometryState.CONFIRMED if validation.is_clean else GeometryState.PROVISIONAL

            logger.info("p3_stage_model", complete=model.is_complete if model else False)
            stages_complete.append("persist_model")

            # Build result
            result.model = model
            result.stages_completed = stages_complete
            result.stages_failed = stages_failed
            result.total_duration_ms = (time.time() - t0) * 1000

        except Exception as e:
            import traceback
            logger.error("p3_pipeline_failed", error=str(e), traceback=traceback.format_exc())
            result.stages_failed.append(str(e))
            result.total_duration_ms = (time.time() - t0) * 1000

        return result


geometry_pipeline = GeometryPipeline()
