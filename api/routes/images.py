"""
api/routes/images.py -- Secure face-image serving endpoint.

Route:
    GET /api/image?path=<report image path>

The report may contain either a bare filename (000000.jpg) or an absolute
path inside the configured image directory. Paths outside BVA_IMAGE_DIR are
rejected so the endpoint can never expose arbitrary files. Every failure is
logged with a full traceback and returned as clean JSON.
"""

from __future__ import annotations

import os
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request, send_file

from api import config

images_bp = Blueprint("images", __name__)

_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def _is_inside_directory(candidate: Path, directory: Path) -> bool:
    """
    Check whether candidate is inside directory.

    os.path.commonpath is used instead of a string prefix check so that
    similarly named sibling directories cannot pass validation.
    """
    try:
        return os.path.commonpath(
            [str(candidate), str(directory)]
        ) == str(directory)
    except ValueError:
        # This can occur when Windows paths use different drives.
        return False


def _resolve_safe_image_path(raw_path: str) -> Path:
    """
    Resolve and validate an image path under the configured image directory.

    Raises ValueError for policy rejections (no dir configured, traversal,
    missing file, disallowed type) and OSError for filesystem failures.
    """
    if config.IMAGE_DIR is None:
        raise ValueError(
            "Image directory is not configured. Set BVA_IMAGE_DIR before "
            "starting the Flask API."
        )

    image_root = config.IMAGE_DIR.resolve()

    if not image_root.is_dir():
        raise ValueError(
            f"Configured image directory does not exist: {image_root}"
        )

    requested_path = Path(raw_path)

    # Absolute paths from the report are accepted only if they resolve inside
    # the configured image directory. Bare filenames are resolved beneath it.
    if requested_path.is_absolute():
        candidate = requested_path.resolve()
    else:
        candidate = (image_root / requested_path).resolve()

    if not _is_inside_directory(candidate, image_root):
        raise ValueError("Requested image is outside the configured image directory.")

    if not candidate.is_file():
        raise ValueError("Requested image file was not found.")

    if candidate.suffix.lower() not in _ALLOWED_EXTENSIONS:
        raise ValueError("Requested file type is not an allowed image type.")

    return candidate


@images_bp.route("/image", methods=["GET"])
def image():
    """
    Serve one validated face image.

    Query parameter:
        path: the image_a or image_b value from a report result.
    """
    raw_path = request.args.get("path", "").strip()

    if not raw_path:
        return jsonify({
            "error": "missing_image_path",
            "message": "Provide an image path using the 'path' query parameter.",
        }), 400

    try:
        image_path = _resolve_safe_image_path(raw_path)
    except (ValueError, OSError) as error:
        # ValueError = policy rejections; OSError = filesystem failures
        # (invalid path syntax, permissions).
        current_app.logger.exception(
            "Rejected image request for path=%r", raw_path
        )
        return jsonify({
            "error": "image_unavailable",
            "message": str(error),
        }), 404

    try:
        return send_file(image_path)
    except OSError as error:
        # File passed validation but could not be opened: locked, deleted,
        # or unreadable.
        current_app.logger.exception(
            "Failed to read image file: %s", image_path
        )
        return jsonify({
            "error": "image_unreadable",
            "message": f"The image exists but could not be read from disk: {error}",
        }), 500
