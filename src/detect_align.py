"""
detect_align.py -- Stage 2: Face Detection and Alignment
Biometric Vulnerability Assessment Framework
Section 3.8 of Chapter 3 -- Research Methodology

This module implements the second stage of the pipeline. It receives a
pre-processed image (from preprocess.py, Section 3.7) and produces a
geometrically normalised, aligned face crop that is ready for the
embedding stage (embed.py, Section 3.9).

It implements:
  3.8.1 -- Face Detection using the Dlib HOG-based frontal face detector
  3.8.2 -- Facial Landmark Detection using the Dlib 68-point shape predictor
  3.8.3 -- Face Alignment using an affine transformation derived from the
           eye centres and the nasal tip

Pipeline position (Stage 2 of 5):
    preprocess.py  ->  detect_align.py  ->  embed.py  ->  classify.py  ->  pipeline.py

Input : pre-processed numpy array (160, 160, 3), float32, RGB, values in [0, 1]
Output: aligned face crop  numpy array (160, 160, 3), uint8,  RGB, values in [0, 255]

Dependencies: dlib, cv2 (OpenCV), numpy (plus the local preprocess module).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional, Tuple

import cv2
import dlib
import numpy as np

# Support running both as a package module (from src.detect_align import ...)
# and as a standalone script (python src/detect_align.py).
try:
    from . import preprocess
except ImportError:  # pragma: no cover - fallback for direct script execution
    import preprocess  # type: ignore


# --------------------------------------------------------------------------- #
# Configuration constants (aligned with Section 3.8 of the methodology)
# --------------------------------------------------------------------------- #
LANDMARK_MODEL_FILENAME: str = "shape_predictor_68_face_landmarks.dat"
DEFAULT_OUTPUT_SIZE: int = 160  # aligned crop is 160x160 px, matching Stage 1

# 68-point landmark index groups (Dlib / iBUG 300-W layout):
#   points  0-16 = jaw line
#   points 17-21 = left eyebrow
#   points 22-26 = right eyebrow
#   points 27-35 = nose (30 = nasal tip)
#   points 36-41 = left eye
#   points 42-47 = right eye
#   points 48-67 = mouth
LEFT_EYE_IDX: slice = slice(36, 42)
RIGHT_EYE_IDX: slice = slice(42, 48)
NOSE_TIP_IDX: int = 30

# Module-level cache so the (relatively expensive) models load only once.
_DETECTOR_CACHE: Optional["dlib.fhog_object_detector"] = None
_PREDICTOR_CACHE: Optional["dlib.shape_predictor"] = None
_PREDICTOR_PATH_CACHE: Optional[str] = None


# --------------------------------------------------------------------------- #
# Model loading
# --------------------------------------------------------------------------- #
def load_dlib_models(
    model_dir: str = "models",
) -> Tuple["dlib.fhog_object_detector", "dlib.shape_predictor"]:
    """Load (and cache) the Dlib HOG detector and 68-point shape predictor.

    Two models are used in Stage 2:

      1. The **HOG frontal face detector** (``dlib.get_frontal_face_detector``).
         This is built into Dlib and needs no external file. It scans the image
         with a Histogram-of-Oriented-Gradients feature descriptor combined with
         a linear SVM classifier and a sliding window to locate frontal faces.

      2. The **68-point shape predictor** (``dlib.shape_predictor``). This is an
         ensemble-of-regression-trees model that requires the external weights
         file ``shape_predictor_68_face_landmarks.dat``, expected in ``model_dir``.

    The loaded models are cached in module-level variables, so repeated calls
    return the cached instances instantly rather than reloading from disk.

    Args:
        model_dir: Directory containing the landmark ``.dat`` file.
                   Defaults to ``"models"``.

    Returns:
        A tuple ``(detector, predictor)``.

    Raises:
        FileNotFoundError: If the landmark ``.dat`` file is not present.
    """
    global _DETECTOR_CACHE, _PREDICTOR_CACHE, _PREDICTOR_PATH_CACHE

    predictor_path = os.path.join(model_dir, LANDMARK_MODEL_FILENAME)

    # Return cached models if already loaded for this same predictor path.
    if (
        _DETECTOR_CACHE is not None
        and _PREDICTOR_CACHE is not None
        and _PREDICTOR_PATH_CACHE == predictor_path
    ):
        return _DETECTOR_CACHE, _PREDICTOR_CACHE

    # The HOG detector is built in and always available.
    detector = dlib.get_frontal_face_detector()

    # The shape predictor requires the external weights file.
    if not os.path.isfile(predictor_path):
        raise FileNotFoundError(
            f"Dlib landmark model not found at {predictor_path}. "
            "Download it from: "
            "http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2, "
            "extract it, and place the .dat file in the models/ directory."
        )

    predictor = dlib.shape_predictor(predictor_path)

    # Populate the cache.
    _DETECTOR_CACHE = detector
    _PREDICTOR_CACHE = predictor
    _PREDICTOR_PATH_CACHE = predictor_path

    return detector, predictor


# --------------------------------------------------------------------------- #
# Internal helpers
# --------------------------------------------------------------------------- #
def _ensure_uint8_rgb(image: np.ndarray) -> np.ndarray:
    """Return an image as a contiguous uint8 RGB array (0-255).

    Stage 1 (preprocess.py) emits float32 arrays normalised to [0, 1]. Dlib
    requires 8-bit unsigned integer images, so float inputs are scaled back to
    the 0-255 range. Arrays that are already uint8 are returned unchanged
    (aside from being made contiguous, which Dlib requires).
    """
    if image is None:
        raise ValueError("Input image is None.")

    if image.dtype == np.uint8:
        out = image
    elif np.issubdtype(image.dtype, np.floating):
        # Assume normalised [0, 1] input from Stage 1.
        out = np.clip(image * 255.0, 0, 255).astype(np.uint8)
    else:
        # Any other integer/float type: clip into the valid 8-bit range.
        out = np.clip(image, 0, 255).astype(np.uint8)

    # Dlib needs a C-contiguous array.
    return np.ascontiguousarray(out)


# --------------------------------------------------------------------------- #
# 3.8.1 -- Face Detection
# --------------------------------------------------------------------------- #
def detect_face(
    image_rgb_uint8: np.ndarray,
    detector: "dlib.fhog_object_detector",
) -> Optional["dlib.rectangle"]:
    """Detect the most prominent frontal face using the Dlib HOG detector.

    HOG-based detection works by computing a Histogram of Oriented Gradients
    over the image -- effectively summarising the local edge/gradient structure
    that characterises a human face -- and sliding a linear SVM classifier
    across the image at multiple scales. Regions the SVM scores as face-like
    are returned as bounding boxes. It is fast, CPU-friendly, and robust for
    roughly frontal faces, which suits the ND-Twins frontal imagery.

    Args:
        image_rgb_uint8: Image array (H, W, 3). If float (Stage 1 output in
                         [0, 1]) it is converted to uint8 automatically.
        detector:        The Dlib HOG detector from :func:`load_dlib_models`.

    Returns:
        The largest detected face as a ``dlib.rectangle`` (largest bounding-box
        area, to disambiguate when several faces are found), or ``None`` if no
        face is detected.
    """
    image = _ensure_uint8_rgb(image_rgb_uint8)

    # Second argument is the up-sampling factor (1 = up-sample once, which helps
    # detect smaller faces at the cost of a little speed).
    detections = detector(image, 1)

    if len(detections) == 0:
        return None

    # Return the largest detection by bounding-box area.
    largest = max(detections, key=lambda rect: rect.width() * rect.height())
    return largest


# --------------------------------------------------------------------------- #
# 3.8.2 -- Facial Landmark Detection
# --------------------------------------------------------------------------- #
def detect_landmarks(
    image_rgb_uint8: np.ndarray,
    face_rect: "dlib.rectangle",
    predictor: "dlib.shape_predictor",
) -> np.ndarray:
    """Locate the 68 facial landmarks within a detected face region.

    The Dlib shape predictor is an ensemble of regression trees that, given the
    face bounding box, regresses the pixel coordinates of 68 fiducial points.
    These points map to well-defined facial structures:

        points  0-16 = jaw line
        points 17-21 = left eyebrow
        points 22-26 = right eyebrow
        points 27-35 = nose (index 30 = nasal tip)
        points 36-41 = left eye
        points 42-47 = right eye
        points 48-67 = mouth

    Args:
        image_rgb_uint8: Image array (H, W, 3); float input is auto-converted.
        face_rect:       Bounding box from :func:`detect_face`.
        predictor:       The 68-point predictor from :func:`load_dlib_models`.

    Returns:
        A numpy array of shape (68, 2) with the integer (x, y) pixel
        coordinates of each landmark.
    """
    image = _ensure_uint8_rgb(image_rgb_uint8)

    shape = predictor(image, face_rect)

    landmarks = np.empty((68, 2), dtype=np.int32)
    for i in range(68):
        part = shape.part(i)
        landmarks[i] = (part.x, part.y)

    return landmarks


# --------------------------------------------------------------------------- #
# 3.8.3 -- Face Alignment
# --------------------------------------------------------------------------- #
def align_face(
    image_rgb_uint8: np.ndarray,
    landmarks: np.ndarray,
    output_size: int = DEFAULT_OUTPUT_SIZE,
) -> np.ndarray:
    """Geometrically normalise a face via an affine transformation.

    Implements Section 3.8.3. Three stable reference points are used to define
    the transformation:

        * left eye centre  = mean of landmarks[36:42]
        * right eye centre = mean of landmarks[42:48]
        * nasal tip        = landmarks[30]

    These are mapped onto canonical target locations in the output frame so that
    every aligned face has its eyes on a common horizontal line and a consistent
    inter-ocular distance. This removes in-plane rotation, scale, and
    translation differences before embedding, which materially improves the
    comparability of the resulting feature vectors.

    Target positions (for an ``output_size`` x ``output_size`` crop):
        * left eye centre  -> (0.35 * output_size, 0.40 * output_size)
        * right eye centre -> (0.65 * output_size, 0.40 * output_size)
        * nasal tip        -> (0.50 * output_size, 0.55 * output_size)

    Args:
        image_rgb_uint8: Image array (H, W, 3); float input is auto-converted.
        landmarks:       (68, 2) landmark array from :func:`detect_landmarks`.
        output_size:     Side length of the square output crop (default 160).

    Returns:
        The aligned face as a numpy array (output_size, output_size, 3),
        uint8, RGB.
    """
    image = _ensure_uint8_rgb(image_rgb_uint8)
    landmarks = np.asarray(landmarks, dtype=np.float32)

    # Source reference points (in the input image).
    left_eye_centre = landmarks[LEFT_EYE_IDX].mean(axis=0)
    right_eye_centre = landmarks[RIGHT_EYE_IDX].mean(axis=0)
    nasal_tip = landmarks[NOSE_TIP_IDX]

    src_pts = np.array(
        [left_eye_centre, right_eye_centre, nasal_tip],
        dtype=np.float32,
    )

    # Target reference points (in the normalised output frame).
    dst_pts = np.array(
        [
            [0.35 * output_size, 0.40 * output_size],  # left eye centre
            [0.65 * output_size, 0.40 * output_size],  # right eye centre
            [0.50 * output_size, 0.55 * output_size],  # nasal tip
        ],
        dtype=np.float32,
    )

    # Affine transform mapping the 3 source points onto the 3 target points.
    affine_matrix = cv2.getAffineTransform(src_pts, dst_pts)

    aligned = cv2.warpAffine(
        image,
        affine_matrix,
        (output_size, output_size),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0),
    )

    return aligned


# --------------------------------------------------------------------------- #
# Main driver -- full Stage 1 + Stage 2 for an image pair
# --------------------------------------------------------------------------- #
def process_image_pair(
    image_path_a: str,
    image_path_b: str,
    detector: "dlib.fhog_object_detector",
    predictor: "dlib.shape_predictor",
) -> Dict[str, object]:
    """Run the full Stage 1 + Stage 2 pipeline on a pair of images.

    For each image this performs:
        1. Pre-processing (Section 3.7) via ``preprocess.preprocess_image``.
        2. Conversion to uint8 for Dlib.
        3. Face detection (Section 3.8.1).
        4. Landmark detection (Section 3.8.2).
        5. Face alignment (Section 3.8.3).

    If a face cannot be detected in either image, processing stops early and a
    result describing which image failed is returned (mirroring the "Flag &
    Exclude Image Pair" branch of the end-to-end flowchart).

    Args:
        image_path_a: Path to the first image.
        image_path_b: Path to the second image.
        detector:     Dlib HOG detector from :func:`load_dlib_models`.
        predictor:    Dlib 68-point predictor from :func:`load_dlib_models`.

    Returns:
        On success, a dict with keys:
            status ('success'),
            aligned_a, aligned_b   -- (160,160,3) uint8 RGB aligned crops,
            landmarks_a, landmarks_b -- (68,2) landmark arrays,
            face_rect_a, face_rect_b -- dlib.rectangle bounding boxes.
        On failure, a dict with keys:
            status ('no_face_detected'),
            failed_image ('A', 'B', or 'A and B'),
            message      -- human-readable explanation.
    """
    # --- Stage 1: pre-process both images ------------------------------------
    preprocessed_a = preprocess.preprocess_image(image_path_a)
    preprocessed_b = preprocess.preprocess_image(image_path_b)

    # --- Convert to uint8 for Dlib -------------------------------------------
    img_a = _ensure_uint8_rgb(preprocessed_a)
    img_b = _ensure_uint8_rgb(preprocessed_b)

    # --- Stage 2.1: face detection -------------------------------------------
    face_rect_a = detect_face(img_a, detector)
    face_rect_b = detect_face(img_b, detector)

    if face_rect_a is None or face_rect_b is None:
        if face_rect_a is None and face_rect_b is None:
            failed = "A and B"
        elif face_rect_a is None:
            failed = "A"
        else:
            failed = "B"
        return {
            "status": "no_face_detected",
            "failed_image": failed,
            "message": (
                f"No face detected in image {failed}. "
                "The image pair is flagged and excluded from further processing."
            ),
        }

    # --- Stage 2.2: landmark detection ---------------------------------------
    landmarks_a = detect_landmarks(img_a, face_rect_a, predictor)
    landmarks_b = detect_landmarks(img_b, face_rect_b, predictor)

    # --- Stage 2.3: face alignment -------------------------------------------
    aligned_a = align_face(img_a, landmarks_a)
    aligned_b = align_face(img_b, landmarks_b)

    return {
        "status": "success",
        "aligned_a": aligned_a,
        "aligned_b": aligned_b,
        "landmarks_a": landmarks_a,
        "landmarks_b": landmarks_b,
        "face_rect_a": face_rect_a,
        "face_rect_b": face_rect_b,
    }


# --------------------------------------------------------------------------- #
# Demonstration / manual smoke test
# --------------------------------------------------------------------------- #
def _demo() -> None:
    """Demonstrate Stage 2 on two sample images.

    Looks for ``data/sample_a.jpg`` and ``data/sample_b.jpg`` relative to the
    repository root. If the sample images or the Dlib landmark model are not
    present, a clear, non-fatal message is printed instead of raising.
    """
    repo_root = Path(__file__).resolve().parents[1]
    data_dir = repo_root / "data"
    model_dir = repo_root / "models"

    sample_a = data_dir / "sample_a.jpg"
    sample_b = data_dir / "sample_b.jpg"

    print("=" * 70)
    print("detect_align.py -- Stage 2 demonstration (Section 3.8)")
    print("=" * 70)

    if not sample_a.is_file() or not sample_b.is_file():
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

    try:
        detector, predictor = load_dlib_models(str(model_dir))
    except FileNotFoundError as exc:
        print(
            "Dlib landmark model is not available:\n"
            f"  {exc}\n\n"
            "Tip: run  python scripts/download_models.py  to fetch it "
            "automatically.\n"
        )
        return

    result = process_image_pair(str(sample_a), str(sample_b), detector, predictor)

    print("-" * 70)
    print(f"  status: {result['status']}")
    if result["status"] == "success":
        print(f"  aligned_a   shape: {result['aligned_a'].shape}, "
              f"dtype: {result['aligned_a'].dtype}")
        print(f"  aligned_b   shape: {result['aligned_b'].shape}, "
              f"dtype: {result['aligned_b'].dtype}")
        print(f"  landmarks_a shape: {result['landmarks_a'].shape}")
        print(f"  landmarks_b shape: {result['landmarks_b'].shape}")
    else:
        print(f"  failed_image: {result.get('failed_image')}")
        print(f"  message:      {result.get('message')}")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
