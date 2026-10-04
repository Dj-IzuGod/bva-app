"""
api/routes/health.py -- GET /api/health

Phase 1 liveness + data-contract check. Reports:
  - that the API process is up,
  - whether the pipeline report JSON exists AND parses (catches corruption),
  - a preview of run_config from the report (proves the contract reads back),
  - whether the dataset image directory is configured and reachable.

Stays useful after Phase 2 as the frontend's connection indicator.
"""

import json

from flask import Blueprint

from api import config

health_bp = Blueprint("health", __name__)


def _report_status():
    """Try to read + parse the report JSON. Never raises."""
    status = {
        "path": str(config.REPORT_JSON_PATH),
        "found": config.REPORT_JSON_PATH.is_file(),
        "parses": False,
        "run_config": None,
        "results_count": None,
        "error": None,
    }
    if not status["found"]:
        status["error"] = (
            "Report not found. Run the pipeline first, e.g.: "
            "python -m src.pipeline --pairs <pairs.csv> --image-dir <images> "
            "--input-mode prealigned"
        )
        return status
    try:
        with open(config.REPORT_JSON_PATH, "r", encoding="utf-8") as fh:
            report = json.load(fh)
        status["parses"] = True
        status["run_config"] = report.get("run_config")
        results = report.get("results")
        status["results_count"] = len(results) if isinstance(results, list) else None
    except (json.JSONDecodeError, OSError) as exc:
        status["error"] = f"Report exists but could not be read: {exc}"
    return status


def _image_dir_status():
    """Image-dir readiness. Never raises."""
    configured = config.IMAGE_DIR is not None
    return {
        "configured": configured,
        "path": str(config.IMAGE_DIR) if configured else None,
        "exists": config.IMAGE_DIR.is_dir() if configured else False,
        "hint": None if configured else (
            "Set BVA_IMAGE_DIR to the ND-TWINS image directory so the API "
            "can serve face images (needed from Phase 2 onward)."
        ),
    }


@health_bp.route("/health", methods=["GET"])
def health():
    """Liveness + artifact status. Always 200; details live in the body."""
    return {
        "status": "ok",
        "service": "bva-api",
        "report": _report_status(),
        "image_dir": _image_dir_status(),
    }
