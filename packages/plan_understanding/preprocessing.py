"""
Vision 5D — Phase 2 Preprocessing Pipeline
Image normalization, deskew, denoise, contrast, perspective correction, quality scoring.
"""
import hashlib, time, structlog
from typing import Optional
from uuid import UUID
from datetime import datetime
import numpy as np

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

from packages.plan_understanding.contracts import (
    PreprocessOperation, PreprocessStep, QualityScore, PreprocessedImage
)

logger = structlog.get_logger()


class PreprocessingPipeline:
    """Production preprocessing pipeline for architectural plans."""

    def __init__(self):
        if not HAS_CV2:
            logger.warn("opencv_not_available", message="Preprocessing will operate in limited mode")

    def process(self, image_bytes: bytes, source_asset_id: UUID,
                target_dpi: int = 150, operations: Optional[list[PreprocessOperation]] = None
                ) -> PreprocessedImage:
        """Run the full preprocessing pipeline."""
        if not HAS_CV2:
            return self._fallback_process(image_bytes, source_asset_id, target_dpi)

        t0 = time.time()
        img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Cannot decode image")

        preprocessed = PreprocessedImage(
            source_asset_id=source_asset_id,
            width_px=img.shape[1],
            height_px=img.shape[0],
            dpi=target_dpi,
            format="png"
        )

        ops = operations or [
            PreprocessOperation.GRAYSCALE,
            PreprocessOperation.DENOISE,
            PreprocessOperation.DESKEW,
            PreprocessOperation.CONTRAST,
            PreprocessOperation.NORMALIZE,
        ]

        for op in ops:
            step_start = time.time()
            img = self._apply_operation(img, op)
            step = PreprocessStep(
                operation=op,
                duration_ms=(time.time() - step_start) * 1000,
                output_hash=hashlib.sha256(img.tobytes()).hexdigest()[:16]
            )
            preprocessed.operations_applied.append(step)

        # Quality assessment
        preprocessed.quality = self._assess_quality(img, target_dpi)
        preprocessed.content_hash = hashlib.sha256(img.tobytes()).hexdigest()

        # Encode result
        _, buffer = cv2.imencode('.png', img)
        preprocessed.storage_locator = f"preproc://{source_asset_id}/{preprocessed.preprocessed_id}"
        preprocessed.width_px = img.shape[1]
        preprocessed.height_px = img.shape[0]

        logger.info("preprocessing_complete", source_asset=str(source_asset_id),
                    steps=len(preprocessed.operations_applied),
                    quality=preprocessed.quality.overall if preprocessed.quality else 0)

        return preprocessed

    def _apply_operation(self, img: np.ndarray, op: PreprocessOperation) -> np.ndarray:
        """Apply a single preprocessing operation."""
        if op == PreprocessOperation.GRAYSCALE:
            if len(img.shape) == 3:
                return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            return img

        elif op == PreprocessOperation.DENOISE:
            if len(img.shape) == 3:
                return cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
            return cv2.fastNlMeansDenoising(img, None, 10, 7, 21)

        elif op == PreprocessOperation.DESKEW:
            gray = img if len(img.shape) == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            coords = np.column_stack(np.where(binary > 0))
            if len(coords) < 100:
                return img
            angle = cv2.minAreaRect(coords.astype(np.float32))[2]
            if angle < -45:
                angle = 90 + angle
            if abs(angle) < 0.3:
                return img
            h, w = img.shape[:2]
            matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
            return cv2.warpAffine(img, matrix, (w, h), borderMode=cv2.BORDER_REPLICATE)

        elif op == PreprocessOperation.CONTRAST:
            if len(img.shape) == 2:
                return cv2.equalizeHist(img)
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            l = cv2.equalizeHist(l)
            return cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)

        elif op == PreprocessOperation.NORMALIZE:
            return cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX)

        elif op == PreprocessOperation.ENHANCE:
            if len(img.shape) == 2:
                blurred = cv2.GaussianBlur(img, (0, 0), 3)
                return cv2.addWeighted(img, 1.5, blurred, -0.5, 0)
            return img

        elif op == PreprocessOperation.BINARIZE:
            gray = img if len(img.shape) == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return binary

        return img

    def _assess_quality(self, img: np.ndarray, dpi: int) -> QualityScore:
        """Score image quality for downstream suitability."""
        gray = img if len(img.shape) == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Sharpness via Laplacian variance
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        sharpness = min(1.0, laplacian_var / 500.0)

        # Contrast via standard deviation
        contrast = min(1.0, gray.std() / 80.0)

        # Noise estimate via high-pass filter
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        noise = np.abs(gray.astype(float) - blurred.astype(float)).mean()
        noise_level = min(1.0, noise / 30.0)

        overall = (sharpness * 0.4 + contrast * 0.3 + (1.0 - noise_level) * 0.3)
        usable = overall >= 0.3 and dpi >= 72

        issues = []
        if sharpness < 0.3:
            issues.append("low_sharpness")
        if contrast < 0.3:
            issues.append("low_contrast")
        if noise_level > 0.7:
            issues.append("high_noise")
        if dpi < 72:
            issues.append("low_resolution")

        return QualityScore(
            overall=round(overall, 3),
            sharpness=round(sharpness, 3),
            contrast=round(contrast, 3),
            noise_level=round(noise_level, 3),
            resolution_dpi=dpi,
            usable=usable,
            issues=issues
        )

    def _fallback_process(self, image_bytes: bytes, source_asset_id: UUID, dpi: int) -> PreprocessedImage:
        """Limited processing when OpenCV is unavailable."""
        logger.warn("preprocessing_fallback", source_asset=str(source_asset_id))
        return PreprocessedImage(
            source_asset_id=source_asset_id,
            dpi=dpi,
            storage_locator=f"preproc://{source_asset_id}/fallback",
            content_hash=hashlib.sha256(image_bytes).hexdigest(),
            quality=QualityScore(overall=0.5, sharpness=0.5, contrast=0.5,
                                noise_level=0.5, resolution_dpi=dpi, usable=True)
        )


# Singleton
preprocessing_pipeline = PreprocessingPipeline()
