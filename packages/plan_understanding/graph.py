"""
Vision 5D — Phase 2 Canonical Architectural Graph Builder
Transforms detections, OCR, scale, and understanding into the canonical graph
that is the sole input to Phase 3 Geometry Engine.
"""
import time, structlog
from uuid import UUID
from typing import Optional

from packages.plan_understanding.contracts import (
    GraphNodeType, GraphEdgeType, GraphNode, GraphEdge, ArchitecturalGraph,
    DetectionSet, DetectionClass, OCRResult, ScaleCalibration,
    ArchitecturalUnderstanding, RoomCandidate, PreprocessedImage,
    ConfidenceReport, AmbiguityReport,
    PlanUnderstandingResult,
)

logger = structlog.get_logger()


class ArchitecturalGraphBuilder:
    """Builds the canonical architectural graph from Phase 2 outputs."""

    def build(self, project_id: UUID, source_asset_id: UUID,
              preprocessed: PreprocessedImage,
              detections: DetectionSet,
              ocr: OCRResult,
              scale: ScaleCalibration,
              understanding: ArchitecturalUnderstanding,
              confidence: ConfidenceReport,
              ambiguity: AmbiguityReport,
              ) -> ArchitecturalGraph:
        """Build the complete architectural understanding graph."""
        t0 = time.time()
        graph = ArchitecturalGraph(
            project_id=project_id,
            source_asset_id=source_asset_id,
            scale=scale,
            metadata={
                "preprocessed_id": str(preprocessed.preprocessed_id),
                "ocr_confidence": ocr.total_confidence if ocr else 0,
                "detection_count": detections.total_detections if detections else 0,
                "room_count": len(understanding.rooms) if understanding else 0,
                "ambiguity_count": ambiguity.total_ambiguities if ambiguity else 0,
                "overall_confidence": confidence.overall_confidence if confidence else 0,
            }
        )

        # 1. Add PAGE node
        page_node = graph.add_node(GraphNode(
            node_type=GraphNodeType.PAGE,
            label=f"Page {preprocessed.source_page or 1}",
            properties={"dpi": preprocessed.dpi, "width_px": preprocessed.width_px,
                       "height_px": preprocessed.height_px, "quality": preprocessed.quality.overall if preprocessed.quality else 0},
            confidence=preprocessed.quality.overall if preprocessed.quality else 0.5,
            source="preprocessing"
        ))

        # 2. Add WALL nodes from detections
        wall_detections = [d for d in detections.detections if d.class_ == DetectionClass.WALL]
        wall_nodes = {}
        for wall in wall_detections:
            wall_node = graph.add_node(GraphNode(
                node_type=GraphNodeType.WALL,
                label=f"Wall-{wall.detection_id.hex[:6]}",
                properties={
                    "thickness_px": wall.thickness_px or 0,
                    "length_px": wall.length_px or 0,
                    "bbox": [wall.bbox.x, wall.bbox.y, wall.bbox.width, wall.bbox.height],
                    "centerline": wall.centerline,
                },
                detection_ref=wall.detection_id,
                confidence=wall.confidence,
                source=wall.source_model,
            ))
            wall_nodes[wall.detection_id] = wall_node
            graph.add_edge(page_node.node_id, wall_node.node_id, GraphEdgeType.CONTAINS)

        # 3. Add OPENING nodes (doors + windows)
        for det in detections.detections:
            if det.class_ in (DetectionClass.DOOR, DetectionClass.WINDOW):
                opening_type = GraphNodeType.OPENING
                label = f"{'Door' if det.class_ == DetectionClass.DOOR else 'Window'}-{det.detection_id.hex[:6]}"
                open_node = graph.add_node(GraphNode(
                    node_type=opening_type,
                    label=label,
                    properties={"bbox": [det.bbox.x, det.bbox.y, det.bbox.width, det.bbox.height],
                               "class": det.class_.value},
                    detection_ref=det.detection_id,
                    confidence=det.confidence,
                    source=det.source_model,
                ))
                graph.add_edge(page_node.node_id, open_node.node_id, GraphEdgeType.CONTAINS)

        # 4. Add ROOM nodes from understanding
        if understanding:
            for room in understanding.rooms:
                room_node = graph.add_node(GraphNode(
                    node_type=GraphNodeType.ROOM,
                    label=room.label or f"Room-{room.room_id.hex[:6]}",
                    properties={
                        "function": room.function.value,
                        "zone": room.zone.value,
                        "area_px2": room.area_px2,
                        "function_confidence": room.function_confidence,
                    },
                    confidence=room.function_confidence,
                    source="understanding_engine",
                ))
                graph.add_edge(page_node.node_id, room_node.node_id, GraphEdgeType.CONTAINS)

                # Room → Wall edges (walls belong to room if they form its boundary)
                for wall_id in room.wall_ids:
                    if wall_id in wall_nodes:
                        graph.add_edge(wall_nodes[wall_id].node_id, room_node.node_id, GraphEdgeType.BELONGS_TO)

                # Room → Opening edges
                for open_id in room.opening_ids:
                    # Find the opening node
                    for node in graph.nodes:
                        if node.detection_ref == open_id:
                            graph.add_edge(node.node_id, room_node.node_id, GraphEdgeType.BELONGS_TO)
                            break

        # 5. Add LABEL nodes from OCR
        if ocr:
            for entry in ocr.entries:
                props = {"text": entry.text, "bbox": list(entry.bbox),
                        "rotation_deg": entry.rotation_deg, "language": entry.language,
                        "classification": entry.classification}
                label_node = graph.add_node(GraphNode(
                    node_type=GraphNodeType.LABEL,
                    label=entry.text[:50],
                    properties=props,
                    confidence=entry.confidence,
                    source=f"ocr_{ocr.engine}",
                ))
                graph.add_edge(page_node.node_id, label_node.node_id, GraphEdgeType.CONTAINS)

                # Link labels to rooms they belong to
                if entry.classification == "room_label" and understanding:
                    for room in understanding.rooms:
                        if room.label == entry.text:
                            # Find the room node
                            for rn in graph.nodes:
                                if rn.node_type == GraphNodeType.ROOM and rn.label == entry.text:
                                    graph.add_edge(label_node.node_id, rn.node_id, GraphEdgeType.LABELS)
                                    break

        # 6. Add DIMENSION nodes
        dim_lines = [d for d in detections.detections if d.class_ == DetectionClass.DIMENSION_LINE]
        for dim in dim_lines:
            dim_node = graph.add_node(GraphNode(
                node_type=GraphNodeType.DIMENSION,
                label=f"Dim-{dim.detection_id.hex[:6]}",
                properties={"length_px": dim.length_px, "bbox": [dim.bbox.x, dim.bbox.y, dim.bbox.width, dim.bbox.height]},
                detection_ref=dim.detection_id,
                confidence=dim.confidence,
                source=dim.source_model,
            ))
            graph.add_edge(page_node.node_id, dim_node.node_id, GraphEdgeType.CONTAINS)

        # 7. Add SYMBOL nodes
        symbol_classes = [c for c in DetectionClass if c.value.startswith("symbol_")]
        for det in detections.detections:
            if det.class_ in symbol_classes:
                sym_node = graph.add_node(GraphNode(
                    node_type=GraphNodeType.SYMBOL,
                    label=f"{det.class_.value}-{det.detection_id.hex[:6]}",
                    properties={"class": det.class_.value, "bbox": [det.bbox.x, det.bbox.y, det.bbox.width, det.bbox.height]},
                    detection_ref=det.detection_id,
                    confidence=det.confidence,
                    source=det.source_model,
                ))
                graph.add_edge(page_node.node_id, sym_node.node_id, GraphEdgeType.CONTAINS)

        # 8. Add FIXTURE nodes
        fixture_classes = [c for c in DetectionClass if c.value.startswith("fixture_") or c.value.startswith("furniture_")]
        for det in detections.detections:
            if det.class_ in fixture_classes:
                fix_node = graph.add_node(GraphNode(
                    node_type=GraphNodeType.FIXTURE if "fixture" in det.class_.value else GraphNodeType.FURNITURE,
                    label=f"{det.class_.value}-{det.detection_id.hex[:6]}",
                    properties={"class": det.class_.value, "bbox": [det.bbox.x, det.bbox.y, det.bbox.width, det.bbox.height]},
                    detection_ref=det.detection_id,
                    confidence=det.confidence,
                    source=det.source_model,
                ))
                graph.add_edge(page_node.node_id, fix_node.node_id, GraphEdgeType.CONTAINS)

        # 9. Add adjacency edges between rooms
        if understanding and len(understanding.rooms) >= 2:
            room_nodes = graph.nodes_by_type(GraphNodeType.ROOM)
            for i, rn_a in enumerate(room_nodes):
                for rn_b in room_nodes[i + 1:]:
                    if self._rooms_are_adjacent(rn_a, rn_b, understanding):
                        graph.add_edge(rn_a.node_id, rn_b.node_id, GraphEdgeType.ADJACENT, confidence=0.80)

        # Validate
        graph.validate_completeness()

        logger.info("graph_built", graph_id=str(graph.graph_id),
                    nodes=len(graph.nodes), edges=len(graph.edges),
                    rooms=graph.room_count(), walls=graph.wall_count(),
                    complete=graph.is_complete)

        return graph

    def _rooms_are_adjacent(self, a: GraphNode, b: GraphNode,
                            understanding: ArchitecturalUnderstanding) -> bool:
        """Determine if two rooms share a wall."""
        room_a = next((r for r in understanding.rooms if r.label == a.label), None)
        room_b = next((r for r in understanding.rooms if r.label == b.label), None)
        if not room_a or not room_b:
            return False
        # Check if they share any wall IDs
        shared = set(room_a.wall_ids) & set(room_b.wall_ids)
        return len(shared) > 0

    def build_full_result(self, project_id: UUID, source_asset_id: UUID,
                          preprocessed: PreprocessedImage,
                          detections: DetectionSet,
                          ocr: OCRResult,
                          scale: ScaleCalibration,
                          understanding: ArchitecturalUnderstanding,
                          confidence: ConfidenceReport,
                          ambiguity: AmbiguityReport,
                          ) -> PlanUnderstandingResult:
        """Build the complete PlanUnderstandingResult with all Phase 2 outputs."""
        t0 = time.time()

        graph = self.build(
            project_id=project_id, source_asset_id=source_asset_id,
            preprocessed=preprocessed, detections=detections, ocr=ocr,
            scale=scale, understanding=understanding,
            confidence=confidence, ambiguity=ambiguity,
        )

        return PlanUnderstandingResult(
            project_id=project_id,
            source_asset_id=source_asset_id,
            preprocessed=preprocessed,
            ocr=ocr,
            detections=detections,
            scale=scale,
            understanding=understanding,
            confidence_report=confidence,
            ambiguity_report=ambiguity,
            graph=graph,
            total_duration_ms=(time.time() - t0) * 1000,
        )


# Singleton
graph_builder = ArchitecturalGraphBuilder()
