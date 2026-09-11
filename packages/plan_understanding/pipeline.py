"""
Vision 5D — Phase 2 Plan Understanding Pipeline Orchestrator
Coordinates preprocessing → OCR → CV → Understanding → Graph.
"""
import time, structlog
from uuid import UUID

from packages.plan_understanding.preprocessing import preprocessing_pipeline
from packages.plan_understanding.ocr import ocr_engine
from packages.plan_understanding.detection import cv_pipeline
from packages.plan_understanding.understanding import (
    scale_engine, confidence_engine, ambiguity_engine, understanding_engine
)
from packages.plan_understanding.graph import graph_builder
from packages.plan_understanding.contracts import PlanUnderstandingResult

logger = structlog.get_logger()


class PlanUnderstandingPipeline:
    """Complete Phase 2 pipeline: image → architectural graph."""

    def process(self, project_id: UUID, source_asset_id: UUID,
                image_bytes: bytes,
                manual_scale: str = None) -> PlanUnderstandingResult:
        """Run the full plan understanding pipeline."""
        t0 = time.time()
        logger.info("phase2_pipeline_started", project_id=str(project_id), source_asset=str(source_asset_id))

        # Step 1: Preprocessing
        logger.info("step_preprocessing")
        preprocessed = preprocessing_pipeline.process(image_bytes, source_asset_id)

        # Step 2: OCR
        logger.info("step_ocr")
        ocr = ocr_engine.extract(preprocessed, image_bytes)

        # Step 3: CV Detection
        logger.info("step_detection")
        detections = cv_pipeline.detect_all(preprocessed)

        # Step 4: Scale Calibration
        logger.info("step_scale")
        scale = scale_engine.calibrate(ocr, detections, preprocessed, manual_scale=manual_scale)

        # Step 5: Confidence Assessment
        logger.info("step_confidence")
        detection_confidence = confidence_engine.assess_detections(detections)

        # Step 6: Ambiguity Detection
        logger.info("step_ambiguity")
        ambiguity = ambiguity_engine.analyze(detections, ocr, detection_confidence)

        # Step 7: Architectural Understanding
        logger.info("step_understanding")
        understanding = understanding_engine.understand(detections, ocr, preprocessed)

        # Step 8: Build Canonical Graph
        logger.info("step_graph")
        result = graph_builder.build_full_result(
            project_id=project_id, source_asset_id=source_asset_id,
            preprocessed=preprocessed, detections=detections, ocr=ocr,
            scale=scale, understanding=understanding,
            confidence=detection_confidence, ambiguity=ambiguity,
        )

        # Set pipeline-level duration
        result.total_duration_ms = (time.time() - t0) * 1000

        logger.info("phase2_pipeline_complete",
                    duration_ms=result.total_duration_ms,
                    rooms=len(understanding.rooms) if understanding else 0,
                    walls=result.graph.wall_count() if result.graph else 0,
                    graph_complete=result.graph.is_complete if result.graph else False)

        return result


# Singleton
plan_pipeline = PlanUnderstandingPipeline()
