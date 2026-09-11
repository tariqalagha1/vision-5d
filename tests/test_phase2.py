"""
Vision 5D — Phase 2 Tests
Tests for preprocessing, OCR, CV detection, understanding, and graph pipeline.
"""
import pytest, json, hashlib
from uuid import uuid4
import numpy as np


# ═══════════════════════════════════════════════════════════
# Generate a test architectural plan image
# ═══════════════════════════════════════════════════════════

def create_test_plan_image(width=1200, height=800) -> bytes:
    """Create a simple architectural floor plan test image."""
    try:
        import cv2
        img = np.ones((height, width, 3), dtype=np.uint8) * 255

        # Draw walls (thick black lines)
        cv2.rectangle(img, (50, 100), (650, 400), (0, 0, 0), 8)  # Outer walls
        cv2.line(img, (300, 100), (300, 400), (0, 0, 0), 8)      # Interior wall

        # Draw door openings (gaps in walls)
        cv2.rectangle(img, (290, 350), (318, 400), (255, 255, 255), -1)  # Door gap

        # Draw room labels
        cv2.putText(img, "LIVING ROOM", (100, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        cv2.putText(img, "KITCHEN", (400, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        cv2.putText(img, "BEDROOM", (100, 470), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        cv2.putText(img, "BATHROOM", (400, 470), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

        # Draw dimension line
        cv2.line(img, (50, 420), (650, 420), (0, 0, 0), 1)
        cv2.putText(img, "6000", (300, 440), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

        # Draw scale and title
        cv2.putText(img, "1:100", (width - 150, height - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
        cv2.putText(img, "GROUND FLOOR PLAN", (width // 2 - 100, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)

        # Draw north arrow
        cv2.arrowedLine(img, (width - 60, 80), (width - 60, 40), (0, 0, 0), 2, tipLength=0.5)
        cv2.putText(img, "N", (width - 70, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

        _, buf = cv2.imencode('.png', img)
        return buf.tobytes()
    except ImportError:
        # Fallback: minimal PNG bytes
        import struct, zlib
        def create_png(w, h):
            def chunk(ctype, data):
                c = ctype + data
                return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
            raw = b''
            for y in range(h):
                raw += b'\x00'  # filter byte
                for x in range(w):
                    raw += b'\xff\xff\xff\xff' if (x > 20 and x < w-20 and y > 20 and y < h-20) else b'\x00\x00\x00\xff'
            return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)) +
                    chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))
        return create_png(width, height)


# ═══════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════

class TestPreprocessing:
    """Test the preprocessing pipeline."""

    def test_process_creates_output(self):
        from packages.plan_understanding.preprocessing import preprocessing_pipeline
        img = create_test_plan_image()
        result = preprocessing_pipeline.process(img, uuid4())
        assert result.preprocessed_id is not None
        assert result.width_px > 0
        assert result.height_px > 0
        assert len(result.content_hash) > 0

    def test_quality_assessment(self):
        from packages.plan_understanding.preprocessing import preprocessing_pipeline
        img = create_test_plan_image()
        result = preprocessing_pipeline.process(img, uuid4(), target_dpi=150)
        assert result.quality is not None
        assert 0.0 <= result.quality.overall <= 1.0
        assert result.quality.resolution_dpi == 150

    def test_deskew_applied(self):
        from packages.plan_understanding.preprocessing import preprocessing_pipeline
        from packages.plan_understanding.contracts import PreprocessOperation
        img = create_test_plan_image()
        result = preprocessing_pipeline.process(
            img, uuid4(),
            operations=[PreprocessOperation.DESKEW, PreprocessOperation.GRAYSCALE]
        )
        ops = [s.operation for s in result.operations_applied]
        assert PreprocessOperation.DESKEW in ops


class TestOCR:
    """Test the OCR engine."""

    def test_ocr_extracts_text(self):
        from packages.plan_understanding.preprocessing import preprocessing_pipeline
        from packages.plan_understanding.ocr import ocr_engine
        img = create_test_plan_image()
        preprocessed = preprocessing_pipeline.process(img, uuid4())
        result = ocr_engine.extract(preprocessed, img)
        assert result.ocr_id is not None
        assert len(result.entries) > 0

    def test_ocr_classifies_room_labels(self):
        from packages.plan_understanding.preprocessing import preprocessing_pipeline
        from packages.plan_understanding.ocr import ocr_engine
        img = create_test_plan_image()
        preprocessed = preprocessing_pipeline.process(img, uuid4())
        result = ocr_engine.extract(preprocessed, img)
        room_labels = [e for e in result.entries if e.classification == "room_label"]
        assert len(room_labels) > 0

    def test_ocr_extracts_scale(self):
        from packages.plan_understanding.preprocessing import preprocessing_pipeline
        from packages.plan_understanding.ocr import ocr_engine
        img = create_test_plan_image()
        preprocessed = preprocessing_pipeline.process(img, uuid4())
        result = ocr_engine.extract(preprocessed, img)
        scale_entries = [e for e in result.entries if e.classification == "scale"]
        assert len(scale_entries) > 0


class TestCVDetection:
    """Test the CV detection pipeline."""

    def test_detects_walls(self):
        from packages.plan_understanding.preprocessing import preprocessing_pipeline
        from packages.plan_understanding.detection import cv_pipeline
        from packages.plan_understanding.contracts import DetectionClass
        img = create_test_plan_image()
        preprocessed = preprocessing_pipeline.process(img, uuid4())
        result = cv_pipeline.detect_all(preprocessed)
        walls = result.by_class(DetectionClass.WALL)
        assert len(walls) > 0
        assert walls[0].confidence > 0

    def test_detects_rooms(self):
        from packages.plan_understanding.preprocessing import preprocessing_pipeline
        from packages.plan_understanding.detection import cv_pipeline
        from packages.plan_understanding.contracts import DetectionClass
        img = create_test_plan_image()
        preprocessed = preprocessing_pipeline.process(img, uuid4())
        result = cv_pipeline.detect_all(preprocessed)
        rooms = result.by_class(DetectionClass.ROOM_REGION)
        assert len(rooms) >= 2  # At least living room and kitchen

    def test_detects_openings(self):
        from packages.plan_understanding.preprocessing import preprocessing_pipeline
        from packages.plan_understanding.detection import cv_pipeline
        from packages.plan_understanding.contracts import DetectionClass
        img = create_test_plan_image()
        preprocessed = preprocessing_pipeline.process(img, uuid4())
        result = cv_pipeline.detect_all(preprocessed)
        doors = result.by_class(DetectionClass.DOOR)
        windows = result.by_class(DetectionClass.WINDOW)
        assert len(doors) + len(windows) > 0

    def test_all_detections_have_confidence(self):
        from packages.plan_understanding.preprocessing import preprocessing_pipeline
        from packages.plan_understanding.detection import cv_pipeline
        img = create_test_plan_image()
        preprocessed = preprocessing_pipeline.process(img, uuid4())
        result = cv_pipeline.detect_all(preprocessed)
        for d in result.detections:
            assert 0.0 <= d.confidence <= 1.0


class TestUnderstandingEngines:
    """Test scale, confidence, ambiguity, and understanding engines."""

    def test_scale_calibration(self):
        from packages.plan_understanding.preprocessing import preprocessing_pipeline
        from packages.plan_understanding.ocr import ocr_engine
        from packages.plan_understanding.detection import cv_pipeline
        from packages.plan_understanding.understanding import scale_engine
        img = create_test_plan_image()
        preprocessed = preprocessing_pipeline.process(img, uuid4())
        ocr = ocr_engine.extract(preprocessed, img)
        detections = cv_pipeline.detect_all(preprocessed)
        scale = scale_engine.calibrate(ocr, detections, preprocessed)
        assert scale.calibration_id is not None
        assert scale.confidence > 0

    def test_confidence_engine(self):
        from packages.plan_understanding.preprocessing import preprocessing_pipeline
        from packages.plan_understanding.detection import cv_pipeline
        from packages.plan_understanding.understanding import confidence_engine
        img = create_test_plan_image()
        preprocessed = preprocessing_pipeline.process(img, uuid4())
        detections = cv_pipeline.detect_all(preprocessed)
        report = confidence_engine.assess_detections(detections)
        assert report.report_id is not None
        assert report.overall_confidence > 0
        assert len(report.assessments) > 0

    def test_ambiguity_engine(self):
        from packages.plan_understanding.preprocessing import preprocessing_pipeline
        from packages.plan_understanding.ocr import ocr_engine
        from packages.plan_understanding.detection import cv_pipeline
        from packages.plan_understanding.understanding import (
            confidence_engine, ambiguity_engine
        )
        img = create_test_plan_image()
        preprocessed = preprocessing_pipeline.process(img, uuid4())
        ocr = ocr_engine.extract(preprocessed, img)
        detections = cv_pipeline.detect_all(preprocessed)
        conf = confidence_engine.assess_detections(detections)
        report = ambiguity_engine.analyze(detections, ocr, conf)
        assert report.report_id is not None
        assert report.total_ambiguities >= 0

    def test_architectural_understanding(self):
        from packages.plan_understanding.preprocessing import preprocessing_pipeline
        from packages.plan_understanding.ocr import ocr_engine
        from packages.plan_understanding.detection import cv_pipeline
        from packages.plan_understanding.understanding import understanding_engine
        img = create_test_plan_image()
        preprocessed = preprocessing_pipeline.process(img, uuid4())
        ocr = ocr_engine.extract(preprocessed, img)
        detections = cv_pipeline.detect_all(preprocessed)
        result = understanding_engine.understand(detections, ocr, preprocessed)
        assert result.understanding_id is not None
        assert len(result.rooms) > 0


class TestArchitecturalGraph:
    """Test the canonical architectural graph builder."""

    def test_graph_built_with_all_node_types(self):
        from packages.plan_understanding.pipeline import plan_pipeline
        img = create_test_plan_image()
        result = plan_pipeline.process(uuid4(), uuid4(), img)
        assert result.graph is not None
        assert result.graph.graph_id is not None
        assert len(result.graph.nodes) > 0
        assert len(result.graph.edges) > 0

    def test_graph_has_rooms_and_walls(self):
        from packages.plan_understanding.pipeline import plan_pipeline
        img = create_test_plan_image()
        result = plan_pipeline.process(uuid4(), uuid4(), img)
        assert result.graph.room_count() > 0
        assert result.graph.wall_count() > 0

    def test_graph_has_labels(self):
        from packages.plan_understanding.pipeline import plan_pipeline
        from packages.plan_understanding.contracts import GraphNodeType
        img = create_test_plan_image()
        result = plan_pipeline.process(uuid4(), uuid4(), img)
        labels = result.graph.nodes_by_type(GraphNodeType.LABEL)
        assert len(labels) > 0

    def test_graph_validation(self):
        from packages.plan_understanding.pipeline import plan_pipeline
        img = create_test_plan_image()
        result = plan_pipeline.process(uuid4(), uuid4(), img)
        issues = result.graph.validate_completeness()
        assert isinstance(issues, list)

    def test_full_pipeline_result(self):
        from packages.plan_understanding.pipeline import plan_pipeline
        img = create_test_plan_image()
        result = plan_pipeline.process(uuid4(), uuid4(), img)
        assert result.result_id is not None
        assert result.preprocessed is not None
        assert result.ocr is not None
        assert result.detections is not None
        assert result.scale is not None
        assert result.understanding is not None
        assert result.confidence_report is not None
        assert result.ambiguity_report is not None
        assert result.graph is not None
        assert result.total_duration_ms > 0
        print(f"Pipeline: {result.total_duration_ms:.0f}ms, "
              f"{result.graph.room_count()} rooms, "
              f"{result.graph.wall_count()} walls, "
              f"{len(result.graph.nodes)} nodes, "
              f"{len(result.graph.edges)} edges")
