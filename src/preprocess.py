"""
preprocess.py -- Stage 1: Image Pre-processing Pipeline
Biometric Vulnerability Assessment Framework
Section 3.7 of Chapter 3 -- Research Methodology

This module handles all image pre-processing before face detection.
It implements:
  3.7.1 -- Colour Space Conversion (BGR -> RGB)
  3.7.2 -- Image Resizing (to 160x160 pixels, bilinear interpolation)
  3.7.3 -- Pixel Value Normalisation (range [0, 1])
  3.7.4 -- Image Quality Assessment (flag unreadable/low-quality images)

The pre-processed output is a float32 numpy array of shape (160, 160, 3)
with pixel values scaled to the range [0.0, 1.0], in RGB channel order.
This standardised representation is consumed by the downstream face
detection and alignment stage (detect_align.py, Section 3.8).

Dependencies: cv2, numpy, os, pathlib, typing (standard scientific stack only).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Union

import cv2
import numpy as np

# --------------------------------------------------------------------------- #
# Configuration constants (aligned with Section 3.7 of the methodology)
# --------------------------------------------------------------------------- #
TARGET_SIZE: tuple[int, int] = (160, 160)   # (width, height) in pixels
MIN_DIMENSION: int = 60                      # minimum acceptable width/height (px)
MIN_MEAN_BRIGHTNESS: float = 10.0            # minimum mean pixel value (0-255)

PathLike = Union[str, os.PathLike]


# --------------------------------------------------------------------------- #
# 3.7.4 -- Image Quality Assessment
# --------------------------------------------------------------------------- #
def quality_check(image_path: PathLike) -> Dict[str, object]:
    """Assess whether an image is suitable for the pre-processing pipeline.

    Implements Section 3.7.4 (Image Quality Assessment). Three independent
    checks are performed on the *original* image before any resizing:

      1. Readability      -- OpenCV must be able to decode the file.
      2. Resolution       -- original width AND height must both be >= 60 px.
      3. Brightness       -- mean pixel value must exceed 10 (out of 255),
                             rejecting near-black / corrupted frames.

    Args:
        image_path: Path to the image file on disk.

    Returns:
        A dictionary with the following keys:
            readable (bool):                  Could OpenCV load the image?
            has_sufficient_resolution (bool): Are both dimensions >= 60 px?
            not_too_dark (bool):              Is mean brightness > 10?
            passed (bool):                    True only if all checks passed.
            reason (str):                     Human-readable failure reason,
                                              or "" (empty) when passed.
    """
    result: Dict[str, object] = {
        "readable": False,
        "has_sufficient_resolution": False,
        "not_too_dark": False,
        "passed": False,
        "reason": "",
    }

    # --- Check 1: readability ------------------------------------------------
    if not os.path.isfile(image_path):
        result["reason"] = f"File does not exist: {image_path}"
        return result

    image = cv2.imread(str(image_path))
    if image is None:
        result["reason"] = f"OpenCV could not decode the image: {image_path}"
        return result
    result["readable"] = True

    # --- Check 2: resolution -------------------------------------------------
    height, width = image.shape[:2]
    if width >= MIN_DIMENSION and height >= MIN_DIMENSION:
        result["has_sufficient_resolution"] = True
    else:
        result["reason"] = (
            f"Resolution too low ({width}x{height}); "
            f"both dimensions must be >= {MIN_DIMENSION}px"
        )
        return result

    # --- Check 3: brightness -------------------------------------------------
    mean_brightness = float(image.mean())
    if mean_brightness > MIN_MEAN_BRIGHTNESS:
        result["not_too_dark"] = True
    else:
        result["reason"] = (
            f"Image too dark (mean brightness {mean_brightness:.2f} "
            f"<= {MIN_MEAN_BRIGHTNESS})"
        )
        return result

    # --- All checks passed ---------------------------------------------------
    result["passed"] = True
    return result


# --------------------------------------------------------------------------- #
# 3.7.1 - 3.7.3 -- Core pre-processing routine
# --------------------------------------------------------------------------- #
def preprocess_image(image_path: PathLike) -> np.ndarray:
    """Load and pre-process a single image for the recognition pipeline.

    Implements Sections 3.7.1 - 3.7.3:
      3.7.1  Colour space conversion: OpenCV loads images in BGR order,
             which is converted to RGB.
      3.7.2  Resizing to 160x160 pixels using bilinear interpolation
             (cv2.INTER_LINEAR).
      3.7.3  Pixel normalisation: values are cast to float32 and scaled
             from [0, 255] to [0.0, 1.0].

    Args:
        image_path: Path to the image file on disk.

    Returns:
        A float32 numpy array of shape (160, 160, 3) in RGB order, with
        pixel values in the range [0.0, 1.0].

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError:        If the file exists but cannot be decoded by OpenCV.
    """
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")

    # Load (OpenCV returns BGR, or None on failure)
    image_bgr = cv2.imread(str(image_path))
    if image_bgr is None:
        raise ValueError(f"Unable to decode image (corrupt/unsupported): {image_path}")

    # 3.7.1 -- BGR -> RGB
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

    # 3.7.2 -- Resize to 160x160 with bilinear interpolation
    image_resized = cv2.resize(image_rgb, TARGET_SIZE, interpolation=cv2.INTER_LINEAR)

    # 3.7.3 -- Normalise to [0.0, 1.0] as float32
    image_normalised = image_resized.astype(np.float32) / 255.0

    return image_normalised


# --------------------------------------------------------------------------- #
# Batch driver
# --------------------------------------------------------------------------- #
def preprocess_batch(
    image_paths: List[PathLike], verbose: bool = True
) -> Dict[str, object]:
    """Pre-process a batch of images, skipping those that fail quality checks.

    For each path the routine first runs :func:`quality_check`. Only images
    that pass are passed on to :func:`preprocess_image`. This mirrors the
    batch extraction workflow described in Sections 3.5-3.7, where unreadable
    or low-quality samples are flagged and excluded rather than silently
    corrupting the downstream embedding stage.

    Args:
        image_paths: List of image file paths to process.
        verbose:     If True, print per-image and summary progress.

    Returns:
        A dictionary with the following keys:
            processed (Dict[str, np.ndarray]): path -> processed array,
                                               for images that succeeded.
            failed (Dict[str, str]):           path -> failure reason,
                                               for images that were skipped.
            total (int):                       Number of paths supplied.
            passed_count (int):                Number processed successfully.
            failed_count (int):                Number skipped/failed.
    """
    processed: Dict[str, np.ndarray] = {}
    failed: Dict[str, str] = {}

    total = len(image_paths)
    if verbose:
        print(f"[preprocess_batch] Processing {total} image(s)...")

    for idx, path in enumerate(image_paths, start=1):
        key = str(path)
        check = quality_check(path)

        if not check["passed"]:
            failed[key] = str(check["reason"])
            if verbose:
                print(f"  [{idx}/{total}] SKIP  {key} -- {check['reason']}")
            continue

        try:
            processed[key] = preprocess_image(path)
            if verbose:
                print(f"  [{idx}/{total}] OK    {key}")
        except (FileNotFoundError, ValueError) as exc:
            # Defensive: a race between quality_check and load, or a decode edge case.
            failed[key] = str(exc)
            if verbose:
                print(f"  [{idx}/{total}] FAIL  {key} -- {exc}")

    summary: Dict[str, object] = {
        "processed": processed,
        "failed": failed,
        "total": total,
        "passed_count": len(processed),
        "failed_count": len(failed),
    }

    if verbose:
        print(
            f"[preprocess_batch] Done. "
            f"{summary['passed_count']} passed, "
            f"{summary['failed_count']} failed, "
            f"{summary['total']} total."
        )

    return summary


# --------------------------------------------------------------------------- #
# Demonstration / manual smoke test
# --------------------------------------------------------------------------- #
def _demo() -> None:
    """Demonstrate the module on two sample images.

    Looks for two sample images under ``data/`` relative to the repository
    root. If they are not present (the dataset is not committed to git), a
    clear, non-fatal message is printed instead of raising.
    """
    repo_root = Path(__file__).resolve().parents[1]
    data_dir = repo_root / "data"

    sample_a = data_dir / "sample_a.jpg"
    sample_b = data_dir / "sample_b.jpg"
    samples = [sample_a, sample_b]

    print("=" * 70)
    print("preprocess.py -- Stage 1 demonstration (Section 3.7)")
    print("=" * 70)

    existing = [p for p in samples if p.is_file()]
    if not existing:
        print(
            "No sample images found under 'data/'.\n"
            f"  Expected: {sample_a}\n"
            f"            {sample_b}\n"
            "The ND-Twins dataset is not committed to the repository.\n"
            "Place two JPEG images at the paths above to run this demo, e.g.:\n"
            "    cp /path/to/imgA.jpg data/sample_a.jpg\n"
            "    cp /path/to/imgB.jpg data/sample_b.jpg\n"
        )
        return

    result = preprocess_batch(samples, verbose=True)

    print("-" * 70)
    for path, array in result["processed"].items():
        print(
            f"  {os.path.basename(path)} -> shape={array.shape}, "
            f"dtype={array.dtype}, min={array.min():.3f}, max={array.max():.3f}"
        )
    for path, reason in result["failed"].items():
        print(f"  {os.path.basename(path)} -> FAILED: {reason}")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
