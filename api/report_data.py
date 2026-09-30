"""
api/report_data.py -- Shared helpers for reading pipeline report artifacts.

The frontend has no database. This module reads the latest JSON report from
disk for each request, validates its basic shape, and converts file/report
problems into predictable API errors.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from api import config


class ReportDataError(Exception):
    """Expected report-data problem that can be returned as a JSON API error."""

    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def load_report() -> dict[str, Any]:
    """
    Load and validate the pipeline JSON report.

    Returns:
        The parsed report dictionary.

    Raises:
        ReportDataError:
            If the report is missing, unreadable, malformed, or has an
            unexpected top-level structure.
    """
    report_path = config.REPORT_JSON_PATH

    if not report_path.is_file():
        raise ReportDataError(
            "Pipeline report not found. Run the pipeline before using the "
            "frontend: results/pipeline_report.json.",
            status_code=404,
        )

    try:
        with report_path.open("r", encoding="utf-8") as report_file:
            report = json.load(report_file)
    except json.JSONDecodeError as exc:
        raise ReportDataError(
            f"Pipeline report contains invalid JSON: {exc}",
            status_code=503,
        ) from exc
    except OSError as exc:
        raise ReportDataError(
            f"Pipeline report could not be read: {exc}",
            status_code=503,
        ) from exc

    if not isinstance(report, dict):
        raise ReportDataError(
            "Pipeline report must contain a top-level JSON object.",
            status_code=503,
        )

    results = report.get("results")
    if results is not None and not isinstance(results, list):
        raise ReportDataError(
            "Pipeline report field 'results' must be a JSON array.",
            status_code=503,
        )

    return report


def get_results(report: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Return only dictionary-shaped result rows from the report.

    A malformed row is ignored rather than crashing the entire API response.
    """
    raw_results = report.get("results", [])
    return [row for row in raw_results if isinstance(row, dict)]
