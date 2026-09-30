"""
api/config.py -- Central configuration for the BVA API layer.

The API reads the artifacts the validated pipeline already writes to disk
(STORAGE RULE: no database). Everything configurable lives here, with
environment-variable overrides so the code runs on any machine unedited:

    BVA_RESULTS_DIR   override for the results directory
    BVA_IMAGE_DIR     override for the dataset image directory
    BVA_API_HOST      bind host (default 127.0.0.1)
    BVA_API_PORT      bind port (default 5000)

Paths resolve from this file's location, so the server works from any
working directory.
"""

import os
from pathlib import Path

# api/config.py -> api/ -> repo root (bva-app)
REPO_ROOT = Path(__file__).resolve().parent.parent

# --- Report artifacts written by `python -m src.pipeline ...` -------------
RESULTS_DIR = Path(os.environ.get("BVA_RESULTS_DIR", str(REPO_ROOT / "results")))
REPORT_JSON_PATH = RESULTS_DIR / "pipeline_report.json"
REPORT_CSV_PATH = RESULTS_DIR / "pipeline_report.csv"

# --- Dataset images (ND-TWINS 112x112 pre-aligned crops) ------------------
# The dataset lives outside the repo and is intentionally NOT hard-coded:
# it must be provided via the BVA_IMAGE_DIR environment variable.
_image_dir = os.environ.get("BVA_IMAGE_DIR", "")
IMAGE_DIR = Path(_image_dir) if _image_dir else None

# --- Dev server settings ----------------------------------------------------
HOST = os.environ.get("BVA_API_HOST", "127.0.0.1")
PORT = int(os.environ.get("BVA_API_PORT", "5000"))
