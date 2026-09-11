"""
Vision 5D — Phase 3 Wall Thickness Estimation Engine
"""
from uuid import UUID
import math
from packages.geometry.contracts import WallThickness, WallCenterline, Point2D


class ThicknessEstimator:
    """Estimates wall thickness from centerline evidence, paired lines, and conventions."""

    DEFAULT_INTERNAL = 120.0
    DEFAULT_EXTERNAL = 250.0
    DEFAULT_PARTITION = 80.0

    def __init__(self):
        self._results: dict[UUID, WallThickness] = {}

    def estimate_all(self, centerlines: list[WallCenterline],
                     paired_line_distances: dict[UUID, float] = None,
                     explicit_dimensions: dict[UUID, float] = None,
                     ) -> list[WallThickness]:
        results = []
        paired = paired_line_distances or {}
        explicit = explicit_dimensions or {}

        for cl in centerlines:
            method = "convention"
            value = self.DEFAULT_INTERNAL
            if cl.is_external:
                value = self.DEFAULT_EXTERNAL
            evidence = [f"default_{'external' if cl.is_external else 'internal'}_thickness_{value}mm"]
            confidence = 0.50

            if cl.centerline_id in explicit:
                value = explicit[cl.centerline_id]
                method = "explicit_dimension"
                confidence = 0.95
                evidence = [f"explicit_dimension_{value}mm"]
            elif cl.centerline_id in paired:
                value = paired[cl.centerline_id]
                method = "paired_lines"
                confidence = 0.80
                evidence = [f"paired_line_distance_{value}mm"]
            elif method == "convention":
                pattern_val = self._detect_pattern_thickness(cl, centerlines)
                if pattern_val:
                    value = pattern_val
                    method = "repeated_pattern"
                    confidence = 0.70
                    evidence = [f"repeated_pattern_{value}mm"]

            wt = WallThickness(
                centerline_id=cl.centerline_id,
                value_mm=value,
                confidence=confidence,
                method=method,
                evidence=evidence,
            )
            results.append(wt)
            self._results[cl.centerline_id] = wt
        return results

    def _detect_pattern_thickness(self, target: WallCenterline, all_cls: list[WallCenterline]) -> float:
        if len(target.points) < 2: return 0.0
        dir_target = (target.points[-1] - target.points[0]).normalized()
        distances = []
        for other in all_cls:
            if other.centerline_id == target.centerline_id or len(other.points) < 2: continue
            dir_other = (other.points[-1] - other.points[0]).normalized()
            dot = abs(dir_target.dot(dir_other))
            if dot < 0.95: continue
            d = self._line_distance(target.points[0], target.points[-1],
                                     other.points[0], other.points[-1])
            if 50 < d < 500:
                distances.append(d)
        if len(distances) >= 2:
            import statistics
            return statistics.median(distances)
        return 0.0

    @staticmethod
    def _line_distance(a1: Point2D, a2: Point2D, b1: Point2D, b2: Point2D) -> float:
        return min(
            ThicknessEstimator._point_line_dist(a1, b1, b2),
            ThicknessEstimator._point_line_dist(a2, b1, b2),
            ThicknessEstimator._point_line_dist(b1, a1, a2),
            ThicknessEstimator._point_line_dist(b2, a1, a2),
        )

    @staticmethod
    def _point_line_dist(pt: Point2D, l1: Point2D, l2: Point2D) -> float:
        v = l2 - l1
        w = pt - l1
        dot_v = v.dot(v)
        if dot_v < 1e-10: return pt.distance_to(l1)
        t = max(0, min(1, w.dot(v) / dot_v))
        proj = l1 + v * t
        return pt.distance_to(proj)

    def get(self, centerline_id: UUID) -> WallThickness:
        return self._results.get(centerline_id)


thickness_estimator = ThicknessEstimator()
