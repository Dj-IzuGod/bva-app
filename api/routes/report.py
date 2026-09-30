"""
api/routes/report.py -- Read-only report API endpoints.

Routes:
    GET /api/summary
    GET /api/pairs
    GET /api/pairs/<pair_id>
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, request

from api.report_data import ReportDataError, get_results, load_report

report_bp = Blueprint("report", __name__)


def _error_response(error: ReportDataError):
    """Convert a report-data failure into a consistent JSON response."""
    return jsonify({
        "error": "report_unavailable",
        "message": error.message,
    }), error.status_code


def _normalise_text(value: Any) -> str:
    """Convert a possibly-null report field into searchable lowercase text."""
    if value is None:
        return ""
    return str(value).strip().lower()


def _query_int(name: str, default: int, minimum: int, maximum: int) -> int:
    """
    Read a bounded integer query parameter.

    Invalid values fall back to the supplied default so a malformed UI query
    does not produce a server error.
    """
    raw_value = request.args.get(name)

    if raw_value is None or raw_value == "":
        return default

    try:
        value = int(raw_value)
    except ValueError:
        return default

    return max(minimum, min(value, maximum))


def _matches_filters(
    row: dict[str, Any],
    pair_type: str | None,
    vulnerability: str | None,
    status: str | None,
    search: str | None,
) -> bool:
    """Return whether one result row matches all active filters."""
    if pair_type and _normalise_text(row.get("pair_type")) != pair_type:
        return False

    if vulnerability and _normalise_text(row.get("vulnerability")) != vulnerability:
        return False

    if status and _normalise_text(row.get("status")) != status:
        return False

    if search:
        searchable_values = (
            row.get("pair_id"),
            row.get("id_a"),
            row.get("id_b"),
            row.get("image_a"),
            row.get("image_b"),
        )
        searchable_text = " ".join(
            _normalise_text(value) for value in searchable_values
        )
        if search not in searchable_text:
            return False

    return True


def _sort_key(row: dict[str, Any], field: str):
    """
    Produce a stable sort key.

    Missing/null values are placed after populated values for ascending sorts.
    """
    value = row.get(field)

    if value is None:
        return (1, "")

    if field in {"distance", "cosine_similarity"}:
        try:
            return (0, float(value))
        except (TypeError, ValueError):
            return (1, "")

    return (0, _normalise_text(value))


@report_bp.route("/summary", methods=["GET"])
def summary():
    """
    Return the report metadata used by the Overview Dashboard.

    Response shape:
        {
          "run_config": ...,
          "threshold_report": ...,
          "summary": ...,
          "report": {
            "path": ...,
            "modified_at": ...
          }
        }
    """
    try:
        report = load_report()
    except ReportDataError as error:
        return _error_response(error)

    modified_at = None
    try:
        modified_at = (
            __import__("datetime").datetime.fromtimestamp(
                # `load_report` already confirmed the file exists.
                # The path is available through the config module.
                __import__("api.config", fromlist=["REPORT_JSON_PATH"])
                .REPORT_JSON_PATH.stat().st_mtime
            ).isoformat()
        )
    except OSError:
        # The report can still be returned if its timestamp is unavailable.
        pass

    return jsonify({
        "run_config": report.get("run_config"),
        "threshold_report": report.get("threshold_report"),
        "summary": report.get("summary"),
        "report": {
            "path": str(
                __import__("api.config", fromlist=["REPORT_JSON_PATH"])
                .REPORT_JSON_PATH
            ),
            "modified_at": modified_at,
        },
    })


@report_bp.route("/pairs", methods=["GET"])
def pairs():
    """
    Return a filtered, sorted, paginated collection of pair results.

    Query parameters:
        page:
            One-based page number. Default: 1.
        page_size:
            Number of rows per page. Default: 25, maximum: 200.
        pair_type:
            Exact pair type filter, such as genuine or impostor.
        vulnerability:
            Exact vulnerability filter, such as HIGH or NONE.
        status:
            Exact status filter, such as success or failed.
        search:
            Case-insensitive search across pair_id, id_a, id_b, image_a,
            and image_b.
        sort_by:
            One of pair_id, pair_type, vulnerability, status, distance,
            cosine_similarity.
        sort_order:
            asc or desc. Default: asc.
    """
    try:
        report = load_report()
    except ReportDataError as error:
        return _error_response(error)

    page = _query_int("page", default=1, minimum=1, maximum=1_000_000)
    page_size = _query_int("page_size", default=25, minimum=1, maximum=200)

    pair_type = _normalise_text(request.args.get("pair_type")) or None
    vulnerability = _normalise_text(request.args.get("vulnerability")) or None
    status = _normalise_text(request.args.get("status")) or None
    search = _normalise_text(request.args.get("search")) or None

    allowed_sort_fields = {
        "pair_id",
        "pair_type",
        "vulnerability",
        "status",
        "distance",
        "cosine_similarity",
    }
    requested_sort = request.args.get("sort_by", "pair_id")
    sort_by = requested_sort if requested_sort in allowed_sort_fields else "pair_id"

    requested_order = request.args.get("sort_order", "asc").lower()
    sort_order = requested_order if requested_order in {"asc", "desc"} else "asc"

    filtered_rows = [
        row for row in get_results(report)
        if _matches_filters(row, pair_type, vulnerability, status, search)
    ]

    filtered_rows.sort(
        key=lambda row: _sort_key(row, sort_by),
        reverse=sort_order == "desc",
    )

    total_items = len(filtered_rows)
    total_pages = max(1, (total_items + page_size - 1) // page_size)

    # If a filter leaves the requested page beyond the last page, return the
    # final page rather than an unexpected empty response.
    actual_page = min(page, total_pages)
    start_index = (actual_page - 1) * page_size
    end_index = start_index + page_size
    page_items = filtered_rows[start_index:end_index]

    return jsonify({
        "items": page_items,
        "pagination": {
            "page": actual_page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_previous": actual_page > 1,
            "has_next": actual_page < total_pages,
        },
        "filters": {
            "pair_type": pair_type,
            "vulnerability": vulnerability,
            "status": status,
            "search": search,
        },
        "sort": {
            "sort_by": sort_by,
            "sort_order": sort_order,
        },
    })


@report_bp.route("/pairs/<path:pair_id>", methods=["GET"])
def pair_detail(pair_id: str):
    """
    Return one exact pair result by pair_id.

    The path converter allows pair IDs containing characters such as slashes.
    The value is compared exactly after URL decoding.
    """
    try:
        report = load_report()
    except ReportDataError as error:
        return _error_response(error)

    for row in get_results(report):
        if str(row.get("pair_id", "")) == pair_id:
            return jsonify({"item": row})

    return jsonify({
        "error": "pair_not_found",
        "message": f"No pair was found with pair_id '{pair_id}'.",
    }), 404
