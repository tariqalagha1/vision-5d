"""
Vision 5D — Phase 2 Scale, Confidence, Ambiguity, and Understanding Engines
Architectural interpretation without geometry reconstruction.
"""
import time, structlog, math, re
from typing import Optional
from uuid import UUID

from packages.plan_understanding.contracts import (
    ScaleMethod, ScaleCalibration,
    ConfidenceLevel, ConfidenceAssessment, ConfidenceReport,
    Ambiguity, AmbiguityReport, BoundingBox,
    RoomFunction, Zone, RoomCandidate, ArchitecturalUnderstanding,
    DetectionClass, DetectionSet, OCRResult, OCREntry, PreprocessedImage,
)

logger = structlog.get_logger()


# ═══════════════════════════════════════════════════════════
# SCALE ENGINE
# ═══════════════════════════════════════════════════════════

class ScaleEngine:
    """Determines drawing scale, units, and pixel-to-world ratio."""

    def calibrate(self, ocr: OCRResult, detections: DetectionSet,
                  preprocessed: PreprocessedImage,
                  manual_scale: Optional[str] = None,
                  manual_dpi: Optional[int] = None) -> ScaleCalibration:
        """Multi-method scale detection."""

        # Method 1: Manual override
        if manual_scale:
            return self._parse_manual(manual_scale, manual_dpi or preprocessed.dpi)

        # Method 2: OCR scale annotation
        scale_entry = self._find_scale_in_ocr(ocr)
        if scale_entry and scale_entry.confidence > 0.6:
            return self._from_ocr_scale(scale_entry, preprocessed)

        # Method 3: Dimension-derived
        dim_entries = [e for e in ocr.entries if e.classification == "dimension"]
        if dim_entries:
            return self._from_dimensions(dim_entries, detections, preprocessed)

        # Method 4: Metadata / default
        return self._default_scale(preprocessed)

    def _parse_manual(self, scale_str: str, dpi: int) -> ScaleCalibration:
        """Parse a manual scale like '1:100' or '1/4\"=1\''."""
        ratio_match = re.match(r'1\s*[:/]\s*(\d+)', scale_str)
        if ratio_match:
            ratio = int(ratio_match.group(1))
            px_per_mm = dpi / 25.4
            return ScaleCalibration(
                method=ScaleMethod.MANUAL, units="mm",
                pixels_per_unit=px_per_mm,
                scale_ratio=f"1:{ratio}", confidence=0.95,
                manual_override=True, validated=False,
            )
        return ScaleCalibration(method=ScaleMethod.MANUAL, scale_ratio=scale_str, confidence=0.80)

    def _find_scale_in_ocr(self, ocr: OCRResult) -> Optional[OCREntry]:
        for e in ocr.entries:
            if e.classification == "scale":
                return e
        return None

    def _from_ocr_scale(self, entry: OCREntry, img: PreprocessedImage) -> ScaleCalibration:
        match = re.match(r'1\s*[:/]\s*(\d+)', entry.text)
        if match:
            ratio = int(match.group(1))
            px_per_mm = img.dpi / 25.4  # standard DPI→mm conversion
            return ScaleCalibration(
                method=ScaleMethod.AUTO, units="mm",
                pixels_per_unit=px_per_mm,
                scale_ratio=f"1:{ratio}", confidence=entry.confidence * 0.9,
            )
        return self._default_scale(img)

    def _from_dimensions(self, dim_entries: list[OCREntry],
                         detections: DetectionSet, img: PreprocessedImage) -> ScaleCalibration:
        """Estimate scale from known dimension annotations."""
        # Find dimension lines
        dim_lines = [d for d in detections.detections if d.class_ == DetectionClass.DIMENSION_LINE]
        if dim_lines and dim_entries:
            dim_value = self._parse_dimension_value(dim_entries[0].text)
            dim_length_px = dim_lines[0].bbox.width
            if dim_value and dim_length_px > 0:
                px_per_mm = dim_length_px / dim_value
                return ScaleCalibration(
                    method=ScaleMethod.DIMENSION_DERIVED, units="mm",
                    pixels_per_unit=px_per_mm, scale_ratio="derived",
                    confidence=0.70,
                    reference_dimension_mm=dim_value,
                    reference_dimension_px=dim_length_px,
                )
        return self._default_scale(img)

    def _parse_dimension_value(self, text: str) -> Optional[float]:
        nums = re.findall(r'(\d+[\.,]?\d*)', text)
        if nums:
            try:
                return float(nums[0].replace(',', '.'))
            except ValueError:
                return None
        return None

    def _default_scale(self, img: PreprocessedImage) -> ScaleCalibration:
        px_per_mm = img.dpi / 25.4
        return ScaleCalibration(
            method=ScaleMethod.UNKNOWN, units="mm",
            pixels_per_unit=px_per_mm, scale_ratio="unknown",
            confidence=0.30,
        )


# ═══════════════════════════════════════════════════════════
# CONFIDENCE ENGINE
# ═══════════════════════════════════════════════════════════

class ConfidenceEngine:
    """Assigns confidence levels to every extracted object. Never hides uncertainty."""

    def assess_detections(self, detections: DetectionSet) -> ConfidenceReport:
        assessments = []
        for d in detections.detections:
            level = self._classify_confidence(d.confidence)
            flags = []
            if d.confidence < 0.5:
                flags.append("low_confidence_detection")
            if d.class_ == DetectionClass.UNKNOWN:
                flags.append("unknown_class")

            assessments.append(ConfidenceAssessment(
                object_id=d.detection_id,
                object_type=d.class_.value,
                confidence=d.confidence,
                level=level,
                extraction_method=d.source_model,
                supporting_evidence=[f"model={d.source_model}", f"version={d.model_version}"],
                ambiguity_flags=flags,
            ))

        overall = sum(a.confidence for a in assessments) / max(len(assessments), 1)
        low_count = sum(1 for a in assessments if a.level in (ConfidenceLevel.LOW, ConfidenceLevel.VERY_LOW))

        return ConfidenceReport(
            preprocessed_id=detections.preprocessed_id,
            assessments=assessments,
            overall_confidence=round(overall, 3),
            low_confidence_count=low_count,
            needs_review_count=low_count,
        )

    def assess_ocr(self, ocr: OCRResult) -> ConfidenceReport:
        assessments = []
        for e in ocr.entries:
            level = self._classify_confidence(e.confidence)
            assessments.append(ConfidenceAssessment(
                object_id=e.entry_id, object_type="ocr_entry",
                confidence=e.confidence, level=level,
                extraction_method="tesseract",
                supporting_evidence=[f"text={e.text[:30]}"],
                ambiguity_flags=[] if e.confidence >= 0.6 else ["low_confidence_ocr"],
            ))

        overall = sum(a.confidence for a in assessments) / max(len(assessments), 1)
        return ConfidenceReport(
            preprocessed_id=ocr.preprocessed_id, assessments=assessments,
            overall_confidence=round(overall, 3),
            low_confidence_count=sum(1 for a in assessments if a.level in (ConfidenceLevel.LOW, ConfidenceLevel.VERY_LOW))
        )

    def _classify_confidence(self, score: float) -> ConfidenceLevel:
        if score >= 0.85: return ConfidenceLevel.HIGH
        if score >= 0.60: return ConfidenceLevel.MEDIUM
        if score >= 0.30: return ConfidenceLevel.LOW
        return ConfidenceLevel.VERY_LOW


# ═══════════════════════════════════════════════════════════
# AMBIGUITY ENGINE
# ═══════════════════════════════════════════════════════════

class AmbiguityEngine:
    """Detects conflicting, uncertain, and missing information. Generates review requests."""

    def analyze(self, detections: DetectionSet, ocr: OCRResult,
                confidence: ConfidenceReport) -> AmbiguityReport:
        ambiguities = []

        # Conflicting OCR
        room_labels = [e for e in ocr.entries if e.classification == "room_label"]
        if len(room_labels) > 1:
            for i, a in enumerate(room_labels):
                for b in room_labels[i + 1:]:
                    if self._bboxes_overlap(a.bbox, b.bbox):
                        ambiguities.append(Ambiguity(
                            region=BoundingBox(x=a.bbox[0], y=a.bbox[1], width=a.bbox[2], height=a.bbox[3]),
                            type="conflicting_ocr",
                            description=f"Overlapping labels: '{a.text}' and '{b.text}'",
                            severity="major",
                            candidates=[a.text, b.text],
                        ))

        # Incomplete rooms
        room_regions = [d for d in detections.detections if d.class_ == DetectionClass.ROOM_REGION]
        labeled_rooms = set()
        for room in room_regions:
            for label in room_labels:
                if self._bbox_contains(room.bbox, label.bbox):
                    labeled_rooms.add(room.detection_id)
                    break

        for room in room_regions:
            if room.detection_id not in labeled_rooms:
                ambiguities.append(Ambiguity(
                    region=room.bbox,
                    type="missing_label",
                    description=f"Room region at ({room.bbox.x:.0f},{room.bbox.y:.0f}) has no label",
                    severity="minor",
                ))

        # Low confidence detections
        low_conf = [a for a in confidence.assessments
                    if a.level in (ConfidenceLevel.LOW, ConfidenceLevel.VERY_LOW)]
        for lc in low_conf[:5]:  # Cap at 5
            ambiguities.append(Ambiguity(
                region=BoundingBox(x=0, y=0, width=100, height=30),
                type="uncertain_symbol",
                description=f"Low confidence {lc.object_type}: {lc.confidence:.2f}",
                severity="minor" if lc.confidence > 0.2 else "major",
            ))

        critical = sum(1 for a in ambiguities if a.severity == "critical")

        return AmbiguityReport(
            preprocessed_id=detections.preprocessed_id,
            ambiguities=ambiguities,
            total_ambiguities=len(ambiguities),
            critical_count=critical,
            review_requests=[a.ambiguity_id for a in ambiguities if a.requires_review],
        )

    def _bboxes_overlap(self, a: tuple, b: tuple) -> bool:
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        return not (ax + aw < bx or bx + bw < ax or ay + ah < by or by + bh < ay)

    def _bbox_contains(self, outer: "BoundingBox", inner: tuple) -> bool:
        ix, iy, iw, ih = inner
        return (outer.x <= ix and outer.y <= iy and
                outer.x + outer.width >= ix + iw and
                outer.y + outer.height >= iy + ih)


# ═══════════════════════════════════════════════════════════
# ARCHITECTURAL UNDERSTANDING ENGINE
# ═══════════════════════════════════════════════════════════

ROOM_FUNCTION_KEYWORDS = {
    "living": RoomFunction.LIVING_ROOM, "lounge": RoomFunction.LIVING_ROOM,
    "dining": RoomFunction.DINING_ROOM, "kitchen": RoomFunction.KITCHEN,
    "bedroom": RoomFunction.BEDROOM, "bed": RoomFunction.BEDROOM,
    "bathroom": RoomFunction.BATHROOM, "bath": RoomFunction.BATHROOM,
    "toilet": RoomFunction.TOILET, "wc": RoomFunction.TOILET,
    "hall": RoomFunction.HALLWAY, "corridor": RoomFunction.CORRIDOR,
    "stair": RoomFunction.STAIRCASE, "entrance": RoomFunction.ENTRANCE,
    "garage": RoomFunction.GARAGE, "storage": RoomFunction.STORAGE,
    "utility": RoomFunction.UTILITY, "office": RoomFunction.OFFICE,
    "balcony": RoomFunction.BALCONY, "terrace": RoomFunction.TERRACE,
    "laundry": RoomFunction.LAUNDRY, "closet": RoomFunction.CLOSET,
    "mechanical": RoomFunction.MECHANICAL, "electrical": RoomFunction.ELECTRICAL,
}


class UnderstandingEngine:
    """Infers architectural meaning from detections and OCR without geometry reconstruction."""

    def understand(self, detections: DetectionSet, ocr: OCRResult,
                   preprocessed: PreprocessedImage) -> ArchitecturalUnderstanding:
        understanding = ArchitecturalUnderstanding(preprocessed_id=preprocessed.preprocessed_id)

        # Build room candidates
        room_regions = [d for d in detections.detections if d.class_ == DetectionClass.ROOM_REGION]
        room_labels = [e for e in ocr.entries if e.classification == "room_label"]
        doors = [d for d in detections.detections if d.class_ == DetectionClass.DOOR]
        windows = [d for d in detections.detections if d.class_ == DetectionClass.WINDOW]
        fixtures = [d for d in detections.detections
                    if d.class_.value.startswith("fixture_")]

        for room_region in room_regions:
            room = RoomCandidate(area_px2=room_region.area_px2 or 0)

            # Find label
            for label in room_labels:
                if self._bbox_contains(room_region.bbox, (label.bbox[0], label.bbox[1],
                                                           label.bbox[2], label.bbox[3])):
                    room.label = label.text
                    room.function = self._classify_room_function(label.text)
                    room.function_confidence = label.confidence
                    break

            # Find openings in this room
            for door in doors:
                if self._bbox_overlap(room_region.bbox, door.bbox):
                    room.opening_ids.append(door.detection_id)
            for window in windows:
                if self._bbox_overlap(room_region.bbox, window.bbox):
                    room.opening_ids.append(window.detection_id)

            # Find fixtures
            for fixture in fixtures:
                if self._bbox_contains(room_region.bbox,
                                       (fixture.bbox.x, fixture.bbox.y, fixture.bbox.width, fixture.bbox.height)):
                    room.fixture_ids.append(fixture.detection_id)

            # Zone classification
            room.zone = self._classify_zone(room.function)
            understanding.rooms.append(room)

        # Classify entrances
        for room in understanding.rooms:
            if room.function in (RoomFunction.ENTRANCE, RoomFunction.HALLWAY):
                understanding.entrance_ids.append(room.room_id)

        # Detect floor
        floor_labels = [e for e in ocr.entries if e.classification == "floor_label"]
        if floor_labels:
            understanding.floors_detected = [fl.text for fl in floor_labels]

        return understanding

    def _classify_room_function(self, label: str) -> RoomFunction:
        label_lower = label.lower().strip()
        for keyword, function in ROOM_FUNCTION_KEYWORDS.items():
            if keyword in label_lower:
                return function
        return RoomFunction.UNKNOWN

    def _classify_zone(self, function: RoomFunction) -> Zone:
        private = {RoomFunction.BEDROOM, RoomFunction.BATHROOM, RoomFunction.TOILET,
                   RoomFunction.CLOSET, RoomFunction.OFFICE}
        service = {RoomFunction.KITCHEN, RoomFunction.UTILITY, RoomFunction.LAUNDRY,
                   RoomFunction.MECHANICAL, RoomFunction.ELECTRICAL, RoomFunction.STORAGE}
        circulation = {RoomFunction.HALLWAY, RoomFunction.CORRIDOR, RoomFunction.STAIRCASE,
                       RoomFunction.ENTRANCE}
        if function in private: return Zone.PRIVATE
        if function in service: return Zone.SERVICE
        if function in circulation: return Zone.CIRCULATION
        if function == RoomFunction.UNKNOWN: return Zone.UNKNOWN
        return Zone.SEMI_PUBLIC

    def _bbox_contains(self, outer: BoundingBox, inner: tuple) -> bool:
        ix, iy, iw, ih = inner
        return (outer.x <= ix and outer.y <= iy and
                outer.x + outer.width >= ix + iw and
                outer.y + outer.height >= iy + ih)

    def _bbox_overlap(self, a: BoundingBox, b: BoundingBox) -> bool:
        return not (a.x + a.width < b.x or b.x + b.width < a.x or
                    a.y + a.height < b.y or b.y + b.height < a.y)


# Singletons
scale_engine = ScaleEngine()
confidence_engine = ConfidenceEngine()
ambiguity_engine = AmbiguityEngine()
understanding_engine = UnderstandingEngine()
