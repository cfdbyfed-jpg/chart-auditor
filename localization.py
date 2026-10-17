"""Translation catalog and localized presentation for Uncharted."""

import json
import math
from pathlib import Path


_LOCALE_DIR = Path(__file__).resolve().parent / "locales"
_CATALOGS = {
    language: json.loads((_LOCALE_DIR / f"{language}.json").read_text(encoding="utf-8"))
    for language in ("ru", "en")
}


def get_catalog(language="ru"):
    """Return a supported catalog; Russian is the safe default."""
    return _CATALOGS.get(language, _CATALOGS["ru"])


def tr(language, key, **values):
    """Translate a UI key and interpolate its values."""
    catalog = get_catalog(language)
    message = catalog["ui"].get(key, _CATALOGS["en"]["ui"].get(key, key))
    return message.format(**values) if values else message


def _number(value, language, spec="g"):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(number):
        return str(value)
    rendered = format(number, spec)
    return rendered.replace(".", ",") if language == "ru" else rendered


def _axis_name(language, axis_name):
    letter = "X" if axis_name == "X-axis" else "Y"
    if language == "ru":
        return letter
    key = "axis_x" if letter == "X" else "axis_y"
    return tr(language, key)


def _chart_name(language, chart_type):
    return get_catalog(language).get("chart_types", {}).get(chart_type, chart_type or "")


def _evidence(language, check_id, status, metrics, context):
    catalog = get_catalog(language)
    strings = catalog["audit"][check_id]
    chart_type = context.get("chart_type")
    chart_name = _chart_name(language, chart_type)
    values = context.get("values")
    if values is not None:
        values = list(values)
    axis_name = _axis_name(language, context.get("axis_name", "Y-axis"))
    axis_range = context.get("original_range")
    x_values = context.get("x_values")
    if x_values is not None:
        x_values = list(x_values)

    def value_bounds():
        if not values:
            return None, None
        return min(values), max(values)

    if check_id == "bar_axis_integrity":
        if chart_type != "Bar chart":
            return strings["evidence_not_bar"].format(chart_type=chart_name)
        data_min, data_max = value_bounds()
        if data_min is None:
            return strings["evidence_no_values"]
        if axis_range is None:
            return strings["evidence_auto"].format(
                data_min=_number(data_min, language),
                data_max=_number(data_max, language),
            )
        lower, upper = axis_range
        clips = lower > data_min or upper < data_max
        excludes_zero = lower > 0 or upper < 0
        return strings["evidence_custom"].format(
            data_min=_number(data_min, language),
            data_max=_number(data_max, language),
            axis_min=_number(lower, language),
            axis_max=_number(upper, language),
            clip=strings["clip"] if clips else "",
            zero=strings["zero"] if excludes_zero else "",
        )

    if check_id == "axis_data_visibility":
        data_min, data_max = value_bounds()
        if data_min is None:
            return strings["evidence_no_values"]
        if axis_range is None:
            return strings["evidence_auto"].format(
                data_min=_number(data_min, language), data_max=_number(data_max, language),
                axis=axis_name,
            )
        lower, upper = axis_range
        return strings["evidence_custom"].format(
            data_min=_number(data_min, language), data_max=_number(data_max, language),
            axis=axis_name, axis_min=_number(lower, language), axis_max=_number(upper, language),
            clip_low=strings["clip_low"] if lower > data_min else "",
            clip_high=strings["clip_high"] if upper < data_max else "",
        )

    if check_id == "difference_amplification":
        if chart_type != "Bar chart":
            return strings["evidence_not_bar"]
        data_min, data_max = value_bounds()
        distinct_categories = len(set(x_values)) if x_values is not None else None
        if distinct_categories is not None and distinct_categories < 2:
            return strings["evidence_one_category"]
        if data_min is None or data_min <= 0 or data_max <= data_min:
            return strings["evidence_nonpositive"]
        if axis_range is not None and (axis_range[0] > data_min or axis_range[1] < data_max):
            return strings["evidence_clipped"]
        if metrics.get("amplification_factor") == 1.0:
            return strings["evidence_zero"]
        if all(key in metrics for key in ("data_ratio", "displayed_ratio", "amplification_factor")):
            return strings["evidence_estimate"].format(
                data_ratio=_number(metrics["data_ratio"], language, ".4g"),
                displayed_ratio=_number(metrics["displayed_ratio"], language, ".4g"),
                factor=_number(metrics["amplification_factor"], language, ".2f"),
            )
        if axis_range is None or axis_range[0] >= data_min:
            return strings["evidence_unavailable"]
        return strings["evidence_unstable"]

    if check_id == "incomplete_rows":
        count = int(metrics.get("excluded_rows", 0))
        if chart_type == "Histogram":
            key = "evidence_histogram" if count else "evidence_histogram_clear"
        elif chart_type == "Box plot" and x_values is None:
            key = "evidence_box_all" if count else "evidence_box_all_clear"
        else:
            key = "evidence_xy" if count else "evidence_xy_clear"
        return strings[key].format(count=count) if count else strings[key]

    if check_id == "line_x_order":
        if chart_type != "Line chart":
            return strings["evidence_not_line"].format(chart_type=chart_name)
        if context.get("line_sort_kind") is None:
            return strings["evidence_not_sortable"]
        return strings["evidence_unsorted"] if status == "detected" else strings["evidence_sorted"]

    if check_id == "chart_data_suitability":
        value_count = len(values) if values is not None else 0
        finite_rows = int(metrics.get("finite_rows", value_count))
        distinct = int(metrics.get("distinct_y_values", len(set(values or []))))
        category_count = metrics.get("bar_category_count")
        threshold = int(metrics.get("bar_category_review_threshold", 20))
        if not finite_rows:
            return strings["evidence_empty"]
        if status == "not_applicable":
            return strings["evidence_single"]
        if status == "detected":
            items = []
            if distinct == 1 and finite_rows > 1:
                items.append(strings["evidence_detected_constant"])
            if chart_type == "Bar chart" and category_count is not None and category_count > threshold:
                items.append(strings["evidence_detected_crowded"].format(
                    categories=category_count, threshold=threshold
                ))
            return " ".join(items)
        note = (
            f" The chart has {category_count} distinct X categories."
            if chart_type == "Bar chart" and category_count is not None
            else ""
        )
        if language == "ru" and note:
            note = f" На графике категорий X: {category_count}."
        return strings["evidence_clear"].format(distinct=distinct, categories_note=note)

    if check_id == "repeated_categories":
        if chart_type != "Bar chart":
            return strings["evidence_not_bar"].format(chart_type=chart_name)
        if x_values is None:
            return strings["evidence_no_x"]
        rows = int(metrics.get("rows", len(x_values)))
        repeated = int(metrics.get("repeated_categories", 0))
        duplicates = int(metrics.get("duplicate_rows", 0))
        if status == "detected":
            return strings["evidence_detected"].format(
                duplicates=duplicates, repeated=repeated, rows=rows
            )
        return strings["evidence_clear"].format(rows=rows)

    if check_id == "extreme_value_context":
        finite_rows = int(metrics.get("finite_rows", len(values or [])))
        if finite_rows < 5:
            return strings["evidence_few"].format(count=finite_rows)
        iqr = metrics.get("iqr")
        if iqr is None or not math.isfinite(float(iqr)) or iqr <= 0:
            return strings["evidence_iqr"]
        outliers = int(metrics.get("outlier_rows", 0))
        ratio = metrics.get("range_iqr_ratio")
        if ratio is None or not math.isfinite(float(ratio)):
            if language == "ru":
                return strings["evidence_ratio_overflow"].format(outliers=outliers)
            return strings["evidence_ratio_overflow"].format(outliers=outliers)
        return strings["evidence_result"].format(
            outliers=outliers, ratio=_number(ratio, language, ".4g")
        )

    return ""


def localize_findings(findings, language="ru", **context):
    """Return presentation copies of audit findings in the chosen language.

    Status codes and metrics stay language-neutral; only user-facing labels and
    prose are translated. The audit engine remains the single source of truth.
    """
    catalog = get_catalog(language)
    language = language if language in _CATALOGS else "ru"
    translated = []
    for finding in findings or []:
        result = dict(finding)
        check_id = result.get("id")
        template = catalog.get("audit", {}).get(check_id)
        if template is None:
            translated.append(result)
            continue

        status = result.get("status", "not_applicable")
        metrics = result.get("metrics") or {}
        params = dict(context)
        chart_type = params.get("chart_type")
        axis_name = _axis_name(language, params.get("axis_name", "Y-axis"))
        params["axis"] = axis_name
        params["threshold"] = metrics.get("bar_category_review_threshold", 20)

        result["title"] = template["title"].format(**params)
        result["explanation"] = template.get("explanation", "").format(**params)
        impact_key = "impact"
        if check_id == "axis_data_visibility":
            impact_key = (
                "impact_histogram" if chart_type == "Histogram"
                else "impact_box" if chart_type == "Box plot"
                else "impact_line"
            )
        result["impact"] = template.get(impact_key, template.get("impact", ""))
        result["evidence"] = _evidence(language, check_id, status, metrics, params)
        recommendation_key = f"recommendation_{status}"
        result["recommendation"] = template.get(
            recommendation_key, template.get("recommendation_clear", "")
        ).format(**params)
        result["limitations"] = template.get("limitations", "").format(**params)
        result["status_label"] = catalog["status_labels"].get(status, status)
        translated.append(result)
    return translated
