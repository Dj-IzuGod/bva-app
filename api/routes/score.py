"""Phase 5: live scoring endpoint -- POST /api/score.

Scores ONE pair of uploaded face images on the fly by reusing the exact
modules the batch pipeline uses (no logic is duplicated):

    detect_align.process_image_pair()   -> detect + align raw photos
    detect_align.load_prealigned_pair() -> accept pre-aligned 112x112 crops
    embed.embed_pair()                  -> ArcFace distance + cosine
    classify.classify_pair()            -> vulnerability grade

MODE-AWARE, mirroring the batch run: the pipeline records how the report's
thresholds were calibrated under run_config.input_mode. This endpoint reads
that field from results/pipeline_report.json at request time and dispatches
exactly the same way the batch pipeline does:

    input_mode == "prealigned" -> load_prealigned_pair (no dlib at all)
    anything else              -> process_image_pair  (full detect+align)

This guarantees live scores land on the SAME scale the thresholds were
derived from: a threshold is only valid for the triplet (model, preprocessing
chain, reference population), so live scoring must reuse the run's chain,
never re-align pre-aligned crops.

Thresholds are read from the report at request time and passed straight
into classify_pair -- exactly what the batch pipeline does. They are NEVER
hardcoded here. If the report is missing/corrupt the endpoint answers 503
with instructions to run the pipeline first.

Models are created ONCE per API process and reused for every request,
mirroring the pipeline rule ("created once per run, reused for every
pair"). Locks make the one-time init safe under Flask's threaded server;
dlib is only loaded when the raw path actually needs it.
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

# One-time model caches + locks. ArcFace is needed for every request; the
# dlib detector/predictor are ONLY needed by the raw detect+align path, so
# they load lazily on the first raw-mode request (prealigned requests never
# pay that cost).
_session_lock = threading.Lock()
_arcface_session = None
_dlib_lock = threading.Lock()
_dlib_models = None


def _get_arcface_session():
    """Load the ArcFace ONNX session once per process, thread-safely.

    Imports are lazy ON PURPOSE: importing src modules pulls in heavy
    dependencies (dlib, onnxruntime) -- the report-only endpoints should
    not pay that cost at API startup.
    """
    global _arcface_session
    if _arcface_session is None:
        with _session_lock:
            if _arcface_session is None:  # double-checked locking
                from src import embed  # runtime import (slow)

                _arcface_session = embed.load_arcface_model()
    return _arcface_session


def _get_dlib_models():
    """Load dlib detector + predictor once per process (raw mode only)."""
    global _dlib_models
    if _dlib_models is None:
        with _dlib_lock:
            if _dlib_models is None:  # double-checked locking
                if not os.path.isdir(MODELS_DIR):
                    raise FileNotFoundError(f"Models directory not found: {MODELS_DIR}")
                from src import detect_align  # runtime import (slow)

                detector, predictor = detect_align.load_dlib_models(MODELS_DIR)
                _dlib_models = {"detector": detector, "predictor": predictor}
    return _dlib_models


def _load_report():
    """Read the pipeline's JSON report and validate what we depend on.

    Returns (report_dict, None) on success, or (None, error_dict) suitable
    for a 503 response when the report is missing/corrupt/incomplete.

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
    return report, None


def _identity_decision(distance, threshold_report):
    """Verification verdict: is this one person or two?

    Uses the SAME report-derived thresholds at two operating points:
      d <= t@FAR=0.01    -> "match"     (safe even against twin impostors)
      d <= eer_threshold -> "uncertain" (grey zone: could genuinely be either)
      otherwise          -> "no_match"  (model sees two different people)
    The EER point is the balanced one: the strict t@FAR=0.01 threshold is
    tuned against twin impostors, so it rejects most true genuine pairs --
    which is precisely the FRR finding this project documented.
    """
    thresholds = threshold_report.get("thresholds") or {}
    t_strict = thresholds.get("far_0.01")
    t_balanced = threshold_report.get("eer_threshold")
    if t_strict is not None and distance <= t_strict:
        return "match"
    if t_balanced is not None and distance <= t_balanced:
        return "uncertain"
    return "no_match"


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
              vulnerability, identity_decision, is_false_accept,
              is_false_reject, input_mode_used, thresholds_used: {...}}
        400  missing/invalid upload
        413  upload above MAX_CONTENT_LENGTH (set in app.py)
        422  no face detected / alignment failed / load failed / embedding missing
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

        # ---- 2. Report: thresholds + input mode (never hardcoded) -----------
        report, error = _load_report()
        if error:
            return jsonify(error), 503

        threshold_report = report.get("threshold_report") or {}
        # The mode the thresholds were calibrated under. If an older report
        # predates run_config, fall back to the full detect+align path (and
        # re-run the pipeline so the mode gets recorded).
        input_mode = (
            (report.get("run_config") or {}).get("input_mode") or "raw"
        ).strip().lower()

        # ---- 3. ArcFace session (always needed) -----------------------------
        try:
            _get_arcface_session()
        except Exception:  # noqa: BLE001 -- model loading has many failure modes
            traceback.print_exc()
            return jsonify({
                "error": "models_unavailable",
                "message": "Could not load the ArcFace model. Check the files "
                           "are present, or point BVA_MODEL_DIR at the right "
                           "folder (see the API terminal).",
            }), 503

        # ---- 4. Run the real pipeline modules (mode-aware, like the batch) --
        from src import classify, detect_align, embed  # lazy, like _get_*

        if input_mode == "prealigned":
            # Same path the batch run used for this report: the uploads are
            # (or resemble) pre-aligned 112x112 crops, so they go straight
            # to the embedder -- NO detection, NO re-alignment. Re-aligning
            # pre-aligned crops shifts the embeddings onto a different scale
            # than the one the thresholds were calibrated on.
            try:
                alignment = detect_align.load_prealigned_pair(path_a, path_b)
            except Exception:  # noqa: BLE001 -- unreadable/corrupt upload
                traceback.print_exc()
                return jsonify({
                    "error": "load_failed",
                    "message": "Could not read one or both images as "
                               "pre-aligned face crops. Upload the original "
                               "dataset crops or clear face photos.",
                }), 422
            if alignment.get("status") != "success":
                return jsonify({
                    "error": alignment.get("status", "load_failed"),
                    "message": "Could not read one or both images as "
                               "pre-aligned face crops. Upload the original "
                               "dataset crops or clear face photos.",
                }), 422
        else:
            # Raw photos: full Stage 1+2 detect + align, exactly like the
            # batch pipeline's non-prealigned mode.
            try:
                dlib_models = _get_dlib_models()
            except Exception:  # noqa: BLE001 -- model loading has many failure modes
                traceback.print_exc()
                return jsonify({
                    "error": "models_unavailable",
                    "message": f"Could not load dlib models from '{MODELS_DIR}'. "
                               "Check the files are present, or point "
                               "BVA_MODEL_DIR at the right folder (see the API "
                               "terminal).",
                }), 503

            alignment = detect_align.process_image_pair(
                path_a, path_b, dlib_models["detector"], dlib_models["predictor"]
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
            "identity_decision": _identity_decision(distance, threshold_report),
            "is_false_accept": grading.get("is_false_accept"),
            "is_false_reject": grading.get("is_false_reject"),
            "input_mode_used": input_mode,
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
