"""Phase 5: live scoring endpoint -- POST /api/score.

Scores ONE pair of uploaded face images on the fly by reusing the exact
modules the batch pipeline uses (no logic is duplicated):

    detect_align.process_image_pair()   -> detect + align the two photos
    embed.embed_pair()                  -> ArcFace distance + cosine
    classify.classify_pair()            -> vulnerability grade

Thresholds are read from results/pipeline_report.json at request time and
passed straight into classify_pair -- exactly what the batch pipeline does
(the report's threshold_report IS the classifier's source of truth).
They are NEVER hardcoded here. If the report is missing or corrupt the
endpoint answers 503 with instructions to run the pipeline first.

Uploaded photos are raw (NOT pre-aligned), so this endpoint always uses
the full detect+align path, never the prealigned loader.

Models are created ONCE per API process and reused for every request,
mirroring the pipeline rule ("created once per run, reused for every
pair"). A lock makes the one-time init safe under Flask's threaded server.
"""

import json
import os
import shutil
import tempfile
import threading
import traceback
import uuid

from flask import Blueprint, jsonify, request

score_bp = Blueprint("score", __name__)

# Repo root = three levels up from this file:
#   api/routes/score.py -> api/routes -> api -> bva-app/
# If your existing routes import path constants from api/config.py (the way
# images.py gets the dataset directory), prefer that import instead -- but
# this derivation works with zero dependencies on config naming.
REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

# Report + models locations (override the models dir with BVA_MODEL_DIR if
# the model files ever move out of <repo>/models).
REPORT_JSON_PATH = os.path.join(REPO_ROOT, "results", "pipeline_report.json")
MODELS_DIR = os.environ.get("BVA_MODEL_DIR") or os.path.join(REPO_ROOT, "models")

# Only image types the face pipeline can actually consume.
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# One-time model cache + lock (dlib detector/predictor + ArcFace session).
_model_lock = threading.Lock()
_models = None


def _get_models():
    """Load dlib + ArcFace models once per process, thread-safely.

    Imports are lazy ON PURPOSE: importing src.detect_align pulls in dlib,
    which is slow -- the report-only endpoints should not pay that cost at
    API startup.
    """
    global _models
    if _models is None:
        with _model_lock:
            if _models is None:  # double-checked locking
                if not os.path.isdir(MODELS_DIR):
                    raise FileNotFoundError(f"Models directory not found: {MODELS_DIR}")
                from src import detect_align, embed  # runtime import (slow)

                detector, predictor = detect_align.load_dlib_models(MODELS_DIR)
                session = embed.load_arcface_model()
                _models = {
                    "detector": detector,
                    "predictor": predictor,
                    "session": session,
                }
    return _models


def _load_threshold_report():
    """Read the 'threshold_report' block from the pipeline's JSON report.

    Returns (threshold_report, None) on success, or (None, error_dict)
    suitable for a 503 response when the report is missing/corrupt/incomplete.

    Re-reads the file per request (it is a few KB) so a fresh pipeline run
    is picked up without restarting the API -- same behaviour as Phase 2.
    """
    try:
        with open(REPORT_JSON_PATH, "r", encoding="utf-8") as fh:
            report = json.load(fh)
    except FileNotFoundError:
        return None, {
            "error": "report_missing",
            "message": "No pipeline report found. Run the pipeline first "
                       "(it writes results/pipeline_report.json).",
        }
    except json.JSONDecodeError:
        return None, {
            "error": "report_corrupt",
            "message": "pipeline_report.json is not valid JSON -- re-run the pipeline.",
        }

    threshold_report = report.get("threshold_report") or {}
    thresholds = threshold_report.get("thresholds") or {}
    if not thresholds.get("far_0.01") or not thresholds.get("far_0.1"):
        return None, {
            "error": "thresholds_unavailable",
            "message": "The report has no derived thresholds (the run warned "
                       "'could not derive thresholds'). Re-run the pipeline "
                       "with at least one scored genuine AND one impostor pair.",
        }
    return threshold_report, None


def _has_allowed_extension(filename):
    lowered = filename.lower()
    return any(lowered.endswith(ext) for ext in ALLOWED_EXTENSIONS)


def _save_upload(file_storage, temp_dir, slot):
    """Persist one uploaded file into temp_dir. Returns the saved path.

    Raises ValueError with a user-facing message for invalid uploads.
    """
    if file_storage is None or file_storage.filename == "":
        raise ValueError("Both image_a and image_b are required.")
    if not _has_allowed_extension(file_storage.filename):
        raise ValueError(
            f"'{file_storage.filename}' is not a supported image "
            f"(allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))})."
        )
    # Randomise the name (never trust client filenames); keep the extension.
    ext = os.path.splitext(file_storage.filename)[1].lower()
    path = os.path.join(temp_dir, f"{slot}_{uuid.uuid4().hex}{ext}")
    file_storage.save(path)
    return path


@score_bp.route("/api/score", methods=["POST"])
def score_pair():
    """Score two uploaded images and grade the pair against run thresholds.

    multipart/form-data fields:
        image_a   (file, required) first face photo
        image_b   (file, required) second face photo
        pair_type (str,  optional) default "impostor" -- uploaded pairs have
                  no ground-truth identity, so they are graded the way an
                  attacker pair would be (see the Methodology page).

    Responses:
        200  {"status": "success", distance, cosine_similarity,
              vulnerability, is_false_accept, is_false_reject,
              thresholds_used: {...}}
        400  missing/invalid upload
        413  upload above MAX_CONTENT_LENGTH (set in app.py)
        422  no face detected / alignment failed / embedding missing
        503  models missing OR report missing/corrupt/thresholds undelivered
        500  unexpected error (full traceback stays in the API console)
    """
    temp_dir = tempfile.mkdtemp(prefix="bva_score_")
    try:
        # ---- 1. Validate + stage the uploads --------------------------------
        try:
            path_a = _save_upload(request.files.get("image_a"), temp_dir, "a")
            path_b = _save_upload(request.files.get("image_b"), temp_dir, "b")
        except ValueError as exc:
            return jsonify({"error": "bad_upload", "message": str(exc)}), 400

        # pair_type only changes the GRADING semantics (an impostor pair is
        # graded HIGH/MEDIUM/LOW by distance; a genuine pair would be graded
        # NONE + a false-reject flag). Unknown/absent -> "impostor".
        pair_type = (request.form.get("pair_type") or "impostor").strip().lower()

        # ---- 2. Thresholds from the report (never hardcoded) ----------------
        threshold_report, error = _load_threshold_report()
        if error:
            return jsonify(error), 503

        # ---- 3. Load models once per process --------------------------------
        try:
            models = _get_models()
        except Exception:  # noqa: BLE001 -- model loading has many failure modes
            traceback.print_exc()
            return jsonify({
                "error": "models_unavailable",
                "message": f"Could not load dlib/ArcFace models from '{MODELS_DIR}'. "
                           "Check the files are present, or point BVA_MODEL_DIR "
                           "at the right folder (see the API terminal).",
            }), 503

        # ---- 4. Run the real pipeline modules --------------------------------
        from src import classify, detect_align, embed  # lazy, like _get_models

        alignment = detect_align.process_image_pair(
            path_a, path_b, models["detector"], models["predictor"]
        )
        if alignment.get("status") != "success":
            return jsonify({
                "error": alignment.get("status", "alignment_failed"),
                "message": "Could not detect a face in one or both photos. "
                           "Use a clear, front-facing photo.",
            }), 422

        scoring = embed.embed_pair(alignment["aligned_a"], alignment["aligned_b"])
        distance = scoring.get("euclidean_distance")
        if scoring.get("status") != "success" or distance is None:
            return jsonify({
                "error": scoring.get("status", "embedding_failed"),
                "message": "Embedding failed for this pair.",
            }), 422

        # ---- 5. Grade with the Stage 4 classifier (identical to the batch) ---
        # NOTE: thresholds are deliberately NOT re-derived per request --
        # that needs the whole run's distances; the report is the
        # validated source of truth.
        grading = classify.classify_pair(
            distance=distance,
            pair_type=pair_type,
            threshold_report=threshold_report,
        )

        # ---- 6. Respond -------------------------------------------------------
        thresholds = threshold_report.get("thresholds") or {}
        return jsonify({
            "status": "success",
            "pair_type_assumed": pair_type,
            "distance": distance,
            "cosine_similarity": scoring.get("cosine_similarity"),
            "vulnerability": grading.get("vulnerability"),
            "is_false_accept": grading.get("is_false_accept"),
            "is_false_reject": grading.get("is_false_reject"),
            "thresholds_used": {
                "eer": threshold_report.get("eer"),
                "eer_threshold": threshold_report.get("eer_threshold"),
                "far_0.01": thresholds.get("far_0.01"),
                "far_0.1": thresholds.get("far_0.1"),
            },
        })

    except Exception:  # noqa: BLE001 -- final safety net for the dev server
        traceback.print_exc()
        return jsonify({
            "error": "score_failed",
            "message": "Unexpected error while scoring. See the API terminal.",
        }), 500
    finally:
        # Uploads are transient -- always clean up, even on error paths.
        shutil.rmtree(temp_dir, ignore_errors=True)
