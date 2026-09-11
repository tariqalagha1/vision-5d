"""
Vision 5D — Phase 3 Scale Calibration Engine
"""
from uuid import UUID, uuid4
from packages.geometry.contracts import ScaleCalibrationResult, Point2D


class ScaleCalibrator:
    """Derives real-world scale from Phase 2 scale evidence and dimension lines."""

    def calibrate(self, phase2_scale: dict, dimension_references: list[dict],
                  manual_override: dict = None) -> ScaleCalibrationResult:
        """
        phase2_scale: {pixels_per_unit, scale_ratio, confidence, method, ...}
        dimension_references: [{value_mm, value_px, confidence}, ...]
        """
        result = ScaleCalibrationResult()
        conflicts = []

        # Try dimension-derived calibration
        dim_calibrations = []
        for dim in dimension_references:
            if dim.get("value_px", 0) > 0 and dim.get("value_mm", 0) > 0:
                px_per_mm = dim["value_px"] / dim["value_mm"]
                dim_calibrations.append({
                    "px_per_mm": px_per_mm,
                    "mm_per_pixel": 1.0/px_per_mm,
                    "confidence": dim.get("confidence", 0.7),
                    "source": f"dimension_{dim.get('value_mm',0)}mm",
                })

        if dim_calibrations:
            # Check for consistency
            vals = [d["px_per_mm"] for d in dim_calibrations]
            if len(vals) >= 2:
                import statistics
                median_val = statistics.median(vals)
                for d in dim_calibrations:
                    deviation = abs(d["px_per_mm"] - median_val) / median_val * 100
                    if deviation > 10:
                        conflicts.append(d)

            # Use median or first
            best = dim_calibrations[0]
            result.pixels_per_mm = best["px_per_mm"]
            result.mm_per_pixel = best["mm_per_pixel"]
            result.method = "dimension_derived"
            result.confidence = min(d["confidence"] for d in dim_calibrations)
            result.source_evidence = [d["source"] for d in dim_calibrations]

        elif phase2_scale and phase2_scale.get("pixels_per_unit", 0) > 0:
            ppu = phase2_scale["pixels_per_unit"]
            result.pixels_per_mm = ppu
            result.mm_per_pixel = 1.0/ppu if ppu > 0 else 0.0
            result.method = phase2_scale.get("method", "auto")
            result.confidence = phase2_scale.get("confidence", 0.5)
            result.scale_ratio = phase2_scale.get("scale_ratio", "1:1")
            result.source_evidence = ["phase2_scale_calibration"]

        else:
            # Default: assume 1:100 scale with 150 DPI
            # 150 DPI = ~5.9 pixels/mm at 1:100 → 0.059 px/mm
            result.pixels_per_mm = 0.059
            result.mm_per_pixel = 16.95
            result.scale_ratio = "1:100"
            result.method = "default"
            result.confidence = 0.20
            result.source_evidence = ["default_1:100_150dpi"]

        if manual_override:
            result.pixels_per_mm = manual_override.get("pixels_per_mm", result.pixels_per_mm)
            result.mm_per_pixel = 1.0/result.pixels_per_mm if result.pixels_per_mm > 0 else 0.0
            result.manual_override = True
            result.method = "manual"
            result.confidence = 0.99

        result.conflicts = conflicts
        result.calibration_error_pct = max((c.get("deviation", 0) for c in conflicts), default=0.0)
        return result


scale_calibrator = ScaleCalibrator()
