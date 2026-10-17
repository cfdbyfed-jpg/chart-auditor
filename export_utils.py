"""Serialization helpers for downloadable Uncharted reports and charts."""

import csv
import io
import json
import re
from collections.abc import Mapping

from localization import get_catalog, localize_findings


REPORT_FIELDS = (
    ("id", "Check ID"),
    ("title", "Check"),
    ("status", "Status"),
    ("explanation", "Description"),
    ("impact", "Why it matters"),
    ("evidence", "Evidence"),
    ("metrics", "Numerical results"),
    ("recommendation", "Recommendation"),
    ("limitations", "Limitations"),
)


def _json_safe(value):
    """Convert common numeric scalar values into strict-JSON-compatible data."""
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "item") and callable(value.item):
        return _json_safe(value.item())
    return value


def _normalized_check(check, language="en"):
    check = check if isinstance(check, Mapping) else {}
    normalized = {}
    for key, _label in REPORT_FIELDS:
        value = check.get(key)
        if key == "metrics":
            normalized[key] = _json_safe(value) if isinstance(value, Mapping) else {}
        else:
            normalized[key] = "" if value is None else str(value)
    normalized["status_label"] = check.get(
        "status_label",
        get_catalog(language)["status_labels"].get(normalized["status"], normalized["status"]),
    )
    return normalized


def audit_csv_bytes(findings, language=None, **localization_context):
    """Serialize findings as Excel-friendly UTF-8 CSV, including empty reports."""
    output_language = language or "en"
    catalog = get_catalog(output_language)
    localized_findings = (
        localize_findings(findings, language, **localization_context)
        if language is not None else list(findings or [])
    )
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=catalog["csv_columns"],
        extrasaction="ignore",
    )
    writer.writeheader()
    for finding in localized_findings:
        normalized = _normalized_check(finding, output_language)
        row = {}
        for (_key, _label), label in zip(REPORT_FIELDS, catalog["csv_columns"]):
            key = _key
            value = normalized[key]
            if key == "metrics":
                value = json.dumps(
                    value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
                )
            elif key == "status":
                value = normalized["status_label"]
            row[label] = value
        writer.writerow(row)
    return output.getvalue().encode("utf-8-sig")


def audit_json_bytes(findings, language=None, **localization_context):
    """Serialize a complete, versioned audit report as readable UTF-8 JSON."""
    output_language = language or "en"
    catalog = get_catalog(output_language)
    localized_findings = (
        localize_findings(findings, language, **localization_context)
        if language is not None else list(findings or [])
    )
    report = {
        "report": catalog["report_title"],
        "schema_version": 1,
        "language": output_language if output_language in {"ru", "en"} else "ru",
        "checks": [_normalized_check(finding, output_language) for finding in localized_findings],
    }
    serialized = json.dumps(
        report, ensure_ascii=False, allow_nan=False, indent=2
    )
    return (serialized + "\n").encode("utf-8")


def figure_html_bytes(figure):
    """Return a standalone interactive Plotly HTML document as UTF-8 bytes."""
    html = figure.to_html(
        full_html=True,
        include_plotlyjs=True,
        config={"responsive": True},
    )
    return html.encode("utf-8")


def figure_filename(chart_title, view):
    """Build a safe and descriptive filename for one chart view."""
    slug = re.sub(r"[^\w.-]+", "_", str(chart_title), flags=re.UNICODE)
    slug = slug.strip("_.-").lower()[:64].strip("_.-") or "chart"
    view_slug = re.sub(r"[^\w.-]+", "_", str(view), flags=re.UNICODE)
    view_slug = view_slug.strip("_.-").lower() or "chart"
    return f"uncharted_{slug}_{view_slug}.html"
