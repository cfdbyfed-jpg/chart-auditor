"""Explainable, rule-based checks for chart configurations and source data."""

import math
import sys

import pandas as pd


DETECTED = "detected"
CLEAR = "clear"
NOT_APPLICABLE = "not_applicable"
MAX_BAR_CATEGORIES = 20
EXTREME_OUTLIER_IQR_MULTIPLIER = 3.0
EXTREME_RANGE_IQR_MULTIPLIER = 10.0


def get_numeric_columns(data):
    """Return numeric columns that can be charted or used for a Y axis."""
    return data.select_dtypes(include="number").columns.tolist()


def line_sort_values(series):
    """Return sortable X values for numeric or date-like line charts."""
    numeric_values = pd.to_numeric(series, errors="coerce")
    if numeric_values.notna().all():
        return numeric_values, "numeric"

    date_values = pd.to_datetime(series, errors="coerce", format="mixed")
    if date_values.notna().all():
        return date_values, "date"
    return None, None


def _finite_padding(lower, upper):
    """Calculate 5% padding without overflowing on large finite values."""
    scale = max(abs(lower), abs(upper))
    if scale == 0:
        return 1.0
    if lower == upper:
        return max(scale * 0.05, 1.0)
    normalized_span = upper / scale - lower / scale
    return (normalized_span * 0.05) * scale


def _finite_bound(value):
    return max(-sys.float_info.max, min(sys.float_info.max, value))


def corrected_y_range(values, chart_type):
    """Return a readable numeric-axis range, including zero for bars."""
    numeric_values = pd.to_numeric(pd.Series(values), errors="coerce")
    finite_values = numeric_values[
        numeric_values.map(lambda value: pd.notna(value) and math.isfinite(float(value)))
    ]
    if finite_values.empty:
        return None

    lower = float(finite_values.min())
    upper = float(finite_values.max())
    padding = _finite_padding(lower, upper)

    if chart_type == "Bar chart":
        bar_lower = min(0.0, _finite_bound(lower - padding))
        bar_upper = max(0.0, _finite_bound(upper + padding))
        if bar_lower == bar_upper:
            return [-1.0, 1.0]
        return [bar_lower, bar_upper]

    return [_finite_bound(lower - padding), _finite_bound(upper + padding)]


def _check(check_id, title, status, explanation, impact, evidence,
           recommendation, limitations, metrics=None):
    return {
        "id": check_id,
        "title": title,
        "status": status,
        "explanation": explanation,
        "impact": impact,
        "evidence": evidence,
        "recommendation": recommendation,
        "limitations": limitations,
        "metrics": metrics or {},
    }


def _numeric_values(values):
    converted = pd.to_numeric(pd.Series(values), errors="coerce")
    return converted[
        converted.map(lambda value: pd.notna(value) and math.isfinite(float(value)))
    ]


def _category_profile(x_values):
    """Summarize usable X categories without changing the source values."""
    if x_values is None:
        return None
    categories = pd.Series(x_values).dropna()
    counts = categories.value_counts(dropna=True)
    repeated = counts[counts > 1]
    return {
        "rows": int(len(categories)),
        "unique_categories": int(len(counts)),
        "repeated_categories": int(len(repeated)),
        "duplicate_rows": int((repeated - 1).sum()) if not repeated.empty else 0,
    }


def _chart_suitability_check(chart_type, values, x_values):
    """Flag only constant Y data and crowded categorical bar charts."""
    if values.empty:
        return _check(
            "chart_data_suitability",
            "Chart and data suitability",
            NOT_APPLICABLE,
            "There are no finite numeric values available to assess chart suitability.",
            "A chart without usable values cannot communicate the selected measure.",
            "No finite numeric Y values were supplied.",
            "Choose a numeric column with usable values.",
            "This check uses simple structural criteria and cannot determine the user's analytical question.",
        )

    unique_y = int(values.nunique())
    profile = _category_profile(x_values)
    crowded_bar = (
        chart_type == "Bar chart"
        and profile is not None
        and profile["unique_categories"] > MAX_BAR_CATEGORIES
    )
    constant_y = unique_y == 1 and len(values) > 1

    if constant_y or crowded_bar:
        reasons = []
        if constant_y:
            reasons.append("all finite Y values are identical")
        if crowded_bar:
            reasons.append(
                f"the bar chart has {profile['unique_categories']} categories "
                f"(review threshold: more than {MAX_BAR_CATEGORIES})"
            )
        status = DETECTED
        evidence = "; ".join(reasons) + "."
        recommendation = (
            "Check whether this chart answers the intended question. For many "
            "categories, consider a focused subset or a clearly explained grouping; "
            "do not discard values silently."
        )
    elif len(values) < 2:
        status = NOT_APPLICABLE
        evidence = "Only one finite Y value is available."
        recommendation = "Add observations before interpreting a pattern or distribution."
    else:
        status = CLEAR
        evidence = f"{unique_y} distinct finite Y values are available."
        if chart_type == "Bar chart" and profile is not None:
            evidence += (
                f" The chart has {profile['unique_categories']} distinct X categories."
            )
        recommendation = "No issue was found by these basic suitability checks."

    return _check(
        "chart_data_suitability",
        "Chart and data suitability",
        status,
        "The check looks for constant Y values and, for bar charts, a large number of categories.",
        "Constant values may not show a meaningful comparison; many bars can make labels and differences hard to read.",
        evidence,
        recommendation,
        (
            f"More than {MAX_BAR_CATEGORIES} bar categories is a review heuristic, not a universal limit. "
            "The check does not know the user's question or domain conventions."
        ),
        {
            "finite_rows": int(len(values)),
            "distinct_y_values": unique_y,
            "bar_category_count": (
                profile["unique_categories"]
                if chart_type == "Bar chart" and profile is not None
                else None
            ),
            "bar_category_review_threshold": MAX_BAR_CATEGORIES,
        },
    )


def _repeated_category_check(chart_type, x_values):
    """Report repeated X values that can overlap bars; never aggregate them."""
    if chart_type != "Bar chart":
        return _check(
            "repeated_categories",
            "Repeated bar-chart categories",
            NOT_APPLICABLE,
            "This check applies to bar charts, where repeated X values can create overlapping bars.",
            "Overlapping bars can hide observations or make category totals ambiguous.",
            f"Selected chart type: {chart_type}.",
            "No duplicate-category action is recommended by this bar-specific check.",
            "Repeated X values can be meaningful for other chart types, including grouped box plots.",
        )
    if x_values is None:
        return _check(
            "repeated_categories",
            "Repeated bar-chart categories",
            NOT_APPLICABLE,
            "No X values were supplied for the bar chart.",
            "Overlapping bars can hide observations or make category totals ambiguous.",
            "X values are unavailable.",
            "Choose a categorical X column to inspect repeated categories.",
            "This check does not inspect an imported chart image.",
        )

    profile = _category_profile(x_values)
    has_duplicates = profile["duplicate_rows"] > 0
    return _check(
        "repeated_categories",
        "Repeated bar-chart categories",
        DETECTED if has_duplicates else CLEAR,
        "The check counts repeated X categories in the rows used to build the bar chart.",
        "Plotly draws a bar for each row; repeated X values can overlap instead of showing a category total.",
        (
            f"{profile['duplicate_rows']} duplicate row(s) occur across "
            f"{profile['repeated_categories']} repeated category value(s), "
            f"among {profile['rows']} plotted rows."
            if has_duplicates
            else f"All {profile['rows']} plotted rows have distinct X categories."
        ),
        (
            "Choose and state an aggregation rule, such as sum or mean, or use a chart "
            "that preserves individual observations. The app does not aggregate automatically."
            if has_duplicates
            else "No duplicate-category correction is needed."
        ),
        "Repeated categories may be intentional. This check does not infer the correct aggregation rule.",
        profile,
    )


def _extreme_value_check(values):
    """Screen for scale-dominating Tukey outliers without calling them errors."""
    if len(values) < 5:
        status = NOT_APPLICABLE
        evidence = f"Only {len(values)} finite value(s) are available; at least 5 are needed for this screen."
        metrics = {"finite_rows": int(len(values))}
    else:
        q1 = float(values.quantile(0.25))
        q3 = float(values.quantile(0.75))
        iqr = q3 - q1
        if not math.isfinite(iqr) or iqr <= 0:
            status = NOT_APPLICABLE
            evidence = "The interquartile range is zero or non-finite, so relative scale influence cannot be estimated."
            metrics = {
                "finite_rows": int(len(values)),
                "q1": q1,
                "q3": q3,
                "iqr": iqr if math.isfinite(iqr) else None,
            }
        else:
            lower_fence = q1 - EXTREME_OUTLIER_IQR_MULTIPLIER * iqr
            upper_fence = q3 + EXTREME_OUTLIER_IQR_MULTIPLIER * iqr
            outliers = values[(values < lower_fence) | (values > upper_fence)]
            data_min, data_max = float(values.min()), float(values.max())
            data_range = data_max - data_min
            ratio = data_range / iqr
            finite_ratio = ratio if math.isfinite(ratio) else None
            dominates = not outliers.empty and ratio >= EXTREME_RANGE_IQR_MULTIPLIER
            status = DETECTED if dominates else CLEAR
            evidence = (
                f"{len(outliers)} value(s) fall beyond the 3×IQR fences; "
                f"the full data range is {ratio:.4g}× the IQR."
                if math.isfinite(ratio)
                else f"{len(outliers)} value(s) fall beyond the 3×IQR fences; the full data range exceeds the finite IQR ratio."
            )
            metrics = {
                "finite_rows": int(len(values)),
                "q1": q1,
                "q3": q3,
                "iqr": iqr,
                "outlier_rows": int(len(outliers)),
                "range_iqr_ratio": finite_ratio,
                "outlier_fence_iqr_multiplier": EXTREME_OUTLIER_IQR_MULTIPLIER,
                "review_threshold_range_iqr_ratio": EXTREME_RANGE_IQR_MULTIPLIER,
            }

    return _check(
        "extreme_value_context",
        "Potentially influential extreme values",
        status,
        "The screen uses 3×IQR fences and checks whether the full range is at least 10× the IQR.",
        "A scale-dominating value can compress variation among the other observations.",
        evidence,
        (
            "Verify the extreme observations and provide context. Consider annotation or a separate view; do not remove values automatically."
            if status == DETECTED
            else "No scale-dominating extreme-value signal was found by this screen."
        ),
        "This is a statistical review signal, not proof of an error or misleading intent. "
        "Valid domain values may be extreme; the check does not inspect their meaning.",
        metrics,
    )


def audit_chart(
    chart_type,
    y_values,
    original_range,
    missing_chart_rows,
    unsorted_line,
    line_order_applicable=False,
    x_values=None,
):
    """Return one transparent result per check, including non-findings.

    ``original_range`` is ``None`` when the chart uses its automatic scale.
    A numeric amplification estimate is returned only for a positive, fully
    visible bar series where the zero and truncated baseline comparisons are
    both defined.
    """
    values = _numeric_values(y_values)
    checks = []
    is_bar = chart_type == "Bar chart"

    if not is_bar:
        checks.append(_check(
            "bar_axis_integrity",
            "Bar-chart baseline and data range",
            NOT_APPLICABLE,
            "This check applies to bar charts, where bar length is measured from a baseline.",
            "A non-zero baseline can exaggerate differences between bars.",
            f"Selected chart type: {chart_type}.",
            "No baseline change is recommended by this bar-specific check.",
            "This bar-specific check does not assess other chart types.",
        ))
    elif values.empty:
        checks.append(_check(
            "bar_axis_integrity",
            "Bar-chart baseline and data range",
            NOT_APPLICABLE,
            "The Y column has no finite numeric values to compare with the axis.",
            "Without usable values, the axis cannot be audited.",
            "No finite numeric Y values were supplied.",
            "Choose a numeric column with at least one finite value.",
            "The check does not infer or repair invalid source values.",
        ))
    elif original_range is None:
        data_min, data_max = float(values.min()), float(values.max())
        checks.append(_check(
            "bar_axis_integrity",
            "Bar-chart baseline and data range",
            CLEAR,
            "No manual Y-axis range is set; the chart uses Plotly's automatic bar scale.",
            "Keeping zero in view helps bar lengths represent their values proportionally.",
            f"Observed data range: {data_min:g} to {data_max:g}; no custom axis bounds were supplied.",
            "No axis correction is needed for the selected settings.",
            "The audit evaluates the chart settings generated by this app, not an imported image.",
        ))
    else:
        lower, upper = map(float, original_range)
        data_min, data_max = float(values.min()), float(values.max())
        clips_data = lower > data_min or upper < data_max
        excludes_zero = lower > 0 or upper < 0
        status = DETECTED if clips_data or excludes_zero else CLEAR
        details = [f"Observed data: {data_min:g} to {data_max:g}."]
        details.append(f"Selected Y-axis: {lower:g} to {upper:g}.")
        if clips_data:
            details.append("At least one observed value falls outside the selected axis range.")
        if excludes_zero:
            details.append("The selected axis range excludes zero.")
        checks.append(_check(
            "bar_axis_integrity",
            "Bar-chart baseline and data range",
            status,
            "The check compares the displayed Y-axis with the observed values and zero.",
            "Clipping values can hide observations; omitting zero can make bar differences look larger.",
            " ".join(details),
            (
                "Expand the range to include all observed values and zero."
                if status == DETECTED
                else "No axis correction is needed for the selected settings."
            ),
            "A non-zero baseline is a review signal, not proof of misleading intent. "
            "The check does not account for domain-specific reasons to zoom the scale.",
        ))

    if not is_bar:
        axis_name = "X-axis" if chart_type == "Histogram" else "Y-axis"
        if values.empty:
            visibility_status = NOT_APPLICABLE
            visibility_evidence = "No finite numeric chart values were supplied."
            visibility_metrics = {}
        else:
            data_min, data_max = float(values.min()), float(values.max())
            if original_range is None:
                visibility_status = CLEAR
                visibility_evidence = (
                    f"Observed data range: {data_min:g} to {data_max:g}; "
                    f"the chart uses an automatic {axis_name} range."
                )
                visibility_metrics = {
                    "data_min": data_min,
                    "data_max": data_max,
                    "axis_min": None,
                    "axis_max": None,
                }
            else:
                lower, upper = map(float, original_range)
                clips_low = lower > data_min
                clips_high = upper < data_max
                visibility_status = DETECTED if clips_low or clips_high else CLEAR
                visibility_evidence = (
                    f"Observed data range: {data_min:g} to {data_max:g}. "
                    f"Selected {axis_name}: {lower:g} to {upper:g}."
                )
                if clips_low:
                    visibility_evidence += " Values below the axis minimum are clipped."
                if clips_high:
                    visibility_evidence += " Values above the axis maximum are clipped."
                visibility_metrics = {
                    "data_min": data_min,
                    "data_max": data_max,
                    "axis_min": lower,
                    "axis_max": upper,
                    "clips_low": clips_low,
                    "clips_high": clips_high,
                }

        checks.append(_check(
            "axis_data_visibility",
            f"{axis_name} data visibility",
            visibility_status,
            f"The check compares the selected {axis_name} range with all finite plotted values.",
            (
                "Clipping X values can hide observations or remove histogram bins."
                if chart_type == "Histogram"
                else "Clipping Y values can hide whiskers, outliers, or parts of a box-plot distribution."
                if chart_type == "Box plot"
                else "Clipping line or scatter values can hide points or parts of a trend."
            ),
            visibility_evidence,
            (
                f"Expand the {axis_name} range to include all observed values."
                if visibility_status == DETECTED
                else f"No {axis_name} range correction is needed for the selected settings."
            ),
            f"This check evaluates {axis_name} bounds created in the app. It does not "
            "inspect an imported chart image.",
            visibility_metrics,
        ))

    amplification = _check(
        "difference_amplification",
        "Estimated visual amplification",
        NOT_APPLICABLE,
        "The estimate compares the ratio of visible bar lengths with the ratio of the underlying positive values.",
        "A truncated baseline may make the largest value appear disproportionately larger.",
        "No numeric estimate is available for the selected settings.",
        "Use a zero baseline or compare the chart with the recommended view.",
        "The estimate only applies to positive values, at least two distinct categories, "
        "a fully visible data range, and a baseline below the smallest value.",
    )

    if is_bar and not values.empty:
        data_min, data_max = float(values.min()), float(values.max())
        bounds = original_range
        if bounds is None:
            lower = 0.0
            upper = data_max
            automatic_zero_baseline = True
        else:
            lower, upper = map(float, bounds)
            automatic_zero_baseline = False

        distinct_categories = (
            pd.Series(x_values).dropna().nunique() if x_values is not None else None
        )
        too_few_categories = distinct_categories is not None and distinct_categories < 2
        fully_visible = lower <= data_min and upper >= data_max

        if too_few_categories:
            amplification["evidence"] = (
                "Only one distinct X category is available, so a between-category "
                "difference cannot be quantified."
            )
        elif data_min <= 0 or data_max <= data_min:
            amplification["evidence"] = (
                "The data include zero or negative values, or all values are equal; "
                "a positive-value ratio is undefined or uninformative."
            )
        elif not fully_visible:
            amplification["evidence"] = (
                "The selected axis clips the data, so comparing displayed and true "
                "bar-length ratios would be misleading."
            )
        elif automatic_zero_baseline or lower <= 0:
            amplification.update({
                "status": CLEAR,
                "evidence": "The displayed bars use a zero baseline; estimated amplification is 1.00×.",
                "recommendation": "No baseline correction is needed.",
                "metrics": {"amplification_factor": 1.0},
            })
        elif lower > 0 and lower < data_min:
            small_gap = data_min - lower
            large_gap = data_max - lower
            if small_gap > 0 and large_gap > 0:
                log_data_ratio = math.log(data_max) - math.log(data_min)
                log_displayed_ratio = math.log(large_gap) - math.log(small_gap)
                log_factor = log_displayed_ratio - log_data_ratio
                if (
                    log_data_ratio > math.log(sys.float_info.max)
                    or log_displayed_ratio > math.log(sys.float_info.max)
                ):
                    amplification["evidence"] = (
                        "The data or displayed ratio exceeds the finite numeric range; "
                        "no stable numerical estimate is reported."
                    )
                    checks.append(amplification)
                    amplification = None
                elif math.isfinite(log_factor) and log_factor <= math.log(sys.float_info.max):
                    factor = math.exp(log_factor)
                    status = DETECTED if factor > 1.0 + 1e-12 else CLEAR
                    data_ratio = math.exp(log_data_ratio)
                    displayed_ratio = math.exp(log_displayed_ratio)
                    amplification.update({
                        "status": status,
                        "evidence": (
                            f"Data ratio: {data_ratio:.4g}×. "
                            f"Displayed bar-length ratio: {displayed_ratio:.4g}×. "
                            f"Estimated relative amplification: {factor:.2f}×."
                        ),
                        "recommendation": (
                            "Include zero in the Y-axis range and compare the resulting chart."
                            if status == DETECTED
                            else "No measurable amplification was found for these values."
                        ),
                        "metrics": {
                            "data_ratio": data_ratio,
                            "displayed_ratio": displayed_ratio,
                            "amplification_factor": factor,
                        },
                    })
                else:
                    amplification["evidence"] = (
                        "The values are too extreme for a stable finite amplification estimate."
                    )

    if amplification is not None:
        checks.append(amplification)

    missing_status = DETECTED if missing_chart_rows else CLEAR
    if chart_type == "Histogram":
        missing_explanation = "A histogram needs a finite numeric value for each included row."
        missing_evidence = (
            f"{missing_chart_rows} row(s) were excluded because the histogram value "
            "is missing or non-finite."
            if missing_chart_rows
            else "No rows were excluded for missing or non-finite histogram values."
        )
    elif chart_type == "Box plot" and x_values is None:
        missing_explanation = "A box plot needs a finite numeric Y value for each included observation."
        missing_evidence = (
            f"{missing_chart_rows} row(s) were excluded because the Y value is missing or non-finite."
            if missing_chart_rows
            else "No rows were excluded for missing or non-finite Y values."
        )
    else:
        missing_explanation = "The chart requires a usable X value and a finite numeric Y value for each point."
        missing_evidence = (
            f"{missing_chart_rows} row(s) were excluded because X or Y is missing, "
            "or Y is not finite."
            if missing_chart_rows
            else "No rows were excluded for missing X or invalid Y values."
        )
    checks.append(_check(
        "incomplete_rows",
        "Rows omitted from the chart",
        missing_status,
        missing_explanation,
        "Omitted rows can change how complete or representative the chart appears.",
        missing_evidence,
        (
            "Review the affected rows and decide whether to correct, exclude, or explain them."
            if missing_chart_rows
            else "No action is needed for missing chart values."
        ),
        "This check reports row counts; it does not infer why values are missing.",
        {"excluded_rows": int(missing_chart_rows)},
    ))

    if chart_type != "Line chart":
        line_status = NOT_APPLICABLE
        line_evidence = f"Selected chart type: {chart_type}."
    elif not line_order_applicable:
        line_status = NOT_APPLICABLE
        line_evidence = "X values are not consistently numeric or date-like, so order cannot be inferred safely."
    elif unsorted_line:
        line_status = DETECTED
        line_evidence = "The original line connects numeric or date-like X values in file order, not sorted order."
    else:
        line_status = CLEAR
        line_evidence = "Numeric or date-like X values are already in ascending order."

    checks.append(_check(
        "line_x_order",
        "Line-chart X order",
        line_status,
        "The check compares file order with numeric or date order before connecting points.",
        "Connecting points in a different order can imply a false sequence or trend.",
        line_evidence,
        (
            "Use the sorted comparison chart or sort the source rows before interpreting the trend."
            if line_status == DETECTED
            else "No ordering change is recommended by this check."
        ),
        "Sorting only applies when every X value is consistently numeric or date-like; "
        "categorical sequence may carry its own meaning.",
    ))

    checks.append(_chart_suitability_check(chart_type, values, x_values))
    checks.append(_repeated_category_check(chart_type, x_values))
    checks.append(_extreme_value_check(values))

    return checks
