"""Run a small, reproducible benchmark of known chart-audit scenarios.

These hand-authored cases are sanity checks, not a representative sample of
real-world charts. They intentionally avoid claiming general model quality.
"""

from collections import defaultdict

from auditor import CLEAR, DETECTED, NOT_APPLICABLE, audit_chart


def _scenario(
    name,
    chart_type,
    values,
    axis_range,
    expected,
    *,
    missing_rows=0,
    unsorted_line=False,
    line_order_applicable=False,
    x_values=None,
):
    return {
        "name": name,
        "chart_type": chart_type,
        "values": values,
        "axis_range": axis_range,
        "missing_rows": missing_rows,
        "unsorted_line": unsorted_line,
        "line_order_applicable": line_order_applicable,
        "x_values": x_values,
        "expected": expected,
    }


SCENARIOS = [
    _scenario(
        "bar_zero_baseline",
        "Bar chart",
        [100, 150],
        [0, 160],
        {
            "bar_axis_integrity": CLEAR,
            "difference_amplification": CLEAR,
            "incomplete_rows": CLEAR,
            "line_x_order": NOT_APPLICABLE,
        },
        x_values=["A", "B"],
    ),
    _scenario(
        "bar_truncated_baseline",
        "Bar chart",
        [100, 150],
        [90, 160],
        {
            "bar_axis_integrity": DETECTED,
            "difference_amplification": DETECTED,
            "incomplete_rows": CLEAR,
            "line_x_order": NOT_APPLICABLE,
        },
        x_values=["A", "B"],
    ),
    _scenario(
        "bar_axis_clips_observations",
        "Bar chart",
        [95, 150],
        [100, 140],
        {
            "bar_axis_integrity": DETECTED,
            "difference_amplification": NOT_APPLICABLE,
            "incomplete_rows": CLEAR,
            "line_x_order": NOT_APPLICABLE,
        },
        x_values=["A", "B"],
    ),
    _scenario(
        "bar_negative_values_include_zero",
        "Bar chart",
        [-10, -5],
        [-12, 0],
        {
            "bar_axis_integrity": CLEAR,
            "difference_amplification": NOT_APPLICABLE,
            "incomplete_rows": CLEAR,
            "line_x_order": NOT_APPLICABLE,
        },
        x_values=["A", "B"],
    ),
    _scenario(
        "line_sorted_automatic_range",
        "Line chart",
        [1, 2, 3],
        None,
        {
            "bar_axis_integrity": NOT_APPLICABLE,
            "axis_data_visibility": CLEAR,
            "difference_amplification": NOT_APPLICABLE,
            "incomplete_rows": CLEAR,
            "line_x_order": CLEAR,
        },
        line_order_applicable=True,
        x_values=[1, 2, 3],
    ),
    _scenario(
        "line_clipped_and_unsorted",
        "Line chart",
        [1, 2, 3],
        [1.5, 2.5],
        {
            "bar_axis_integrity": NOT_APPLICABLE,
            "axis_data_visibility": DETECTED,
            "difference_amplification": NOT_APPLICABLE,
            "incomplete_rows": CLEAR,
            "line_x_order": DETECTED,
        },
        unsorted_line=True,
        line_order_applicable=True,
        x_values=[3, 1, 2],
    ),
    _scenario(
        "line_categorical_order_not_inferred",
        "Line chart",
        [1, 2, 3],
        None,
        {
            "bar_axis_integrity": NOT_APPLICABLE,
            "axis_data_visibility": CLEAR,
            "difference_amplification": NOT_APPLICABLE,
            "incomplete_rows": CLEAR,
            "line_x_order": NOT_APPLICABLE,
        },
        line_order_applicable=False,
        x_values=["Spring", "Summer", "Winter"],
    ),
    _scenario(
        "scatter_clipped_y_values",
        "Scatter plot",
        [0, 5, 10],
        [1, 8],
        {
            "bar_axis_integrity": NOT_APPLICABLE,
            "axis_data_visibility": DETECTED,
            "difference_amplification": NOT_APPLICABLE,
            "incomplete_rows": CLEAR,
            "line_x_order": NOT_APPLICABLE,
        },
        x_values=[0, 1, 2],
    ),
    _scenario(
        "scatter_full_y_range",
        "Scatter plot",
        [0, 5, 10],
        [-1, 11],
        {
            "bar_axis_integrity": NOT_APPLICABLE,
            "axis_data_visibility": CLEAR,
            "difference_amplification": NOT_APPLICABLE,
            "incomplete_rows": CLEAR,
            "line_x_order": NOT_APPLICABLE,
        },
        x_values=[0, 1, 2],
    ),
    _scenario(
        "histogram_clips_low_values",
        "Histogram",
        [0, 1, 2],
        [0.5, 2.5],
        {
            "bar_axis_integrity": NOT_APPLICABLE,
            "axis_data_visibility": DETECTED,
            "difference_amplification": NOT_APPLICABLE,
            "incomplete_rows": CLEAR,
            "line_x_order": NOT_APPLICABLE,
        },
    ),
    _scenario(
        "histogram_full_range_with_invalid_row",
        "Histogram",
        [0, 1, 2],
        [-0.5, 2.5],
        {
            "bar_axis_integrity": NOT_APPLICABLE,
            "axis_data_visibility": CLEAR,
            "difference_amplification": NOT_APPLICABLE,
            "incomplete_rows": DETECTED,
            "line_x_order": NOT_APPLICABLE,
        },
        missing_rows=1,
    ),
    _scenario(
        "box_plot_clips_whiskers",
        "Box plot",
        [95, 110, 125, 140, 150],
        [101, 144],
        {
            "bar_axis_integrity": NOT_APPLICABLE,
            "axis_data_visibility": DETECTED,
            "difference_amplification": NOT_APPLICABLE,
            "incomplete_rows": CLEAR,
            "line_x_order": NOT_APPLICABLE,
        },
    ),
    _scenario(
        "box_plot_automatic_full_range",
        "Box plot",
        [95, 110, 125, 140, 150],
        None,
        {
            "bar_axis_integrity": NOT_APPLICABLE,
            "axis_data_visibility": CLEAR,
            "difference_amplification": NOT_APPLICABLE,
            "incomplete_rows": CLEAR,
            "line_x_order": NOT_APPLICABLE,
        },
    ),
    _scenario(
        "box_plot_grouped_observations",
        "Box plot",
        [1, 2, 8, 9],
        None,
        {
            "bar_axis_integrity": NOT_APPLICABLE,
            "axis_data_visibility": CLEAR,
            "difference_amplification": NOT_APPLICABLE,
            "incomplete_rows": CLEAR,
            "line_x_order": NOT_APPLICABLE,
        },
        x_values=["A", "A", "B", "B"],
    ),
    _scenario(
        "bar_many_categories",
        "Bar chart",
        list(range(1, 26)),
        [0, 26],
        {
            "chart_data_suitability": DETECTED,
            "repeated_categories": CLEAR,
            "extreme_value_context": CLEAR,
        },
        x_values=[f"Category {index:02d}" for index in range(1, 26)],
    ),
    _scenario(
        "bar_repeated_categories",
        "Bar chart",
        [10, 20, 30],
        [0, 35],
        {
            "chart_data_suitability": CLEAR,
            "repeated_categories": DETECTED,
            "extreme_value_context": NOT_APPLICABLE,
        },
        x_values=["A", "A", "B"],
    ),
    _scenario(
        "bar_clear_category_count",
        "Bar chart",
        list(range(1, 13)),
        [0, 13],
        {
            "chart_data_suitability": CLEAR,
            "repeated_categories": CLEAR,
            "extreme_value_context": CLEAR,
        },
        x_values=[f"Category {index:02d}" for index in range(1, 13)],
    ),
    _scenario(
        "line_constant_values",
        "Line chart",
        [5, 5, 5],
        None,
        {
            "chart_data_suitability": DETECTED,
            "repeated_categories": NOT_APPLICABLE,
            "extreme_value_context": NOT_APPLICABLE,
        },
        line_order_applicable=True,
        x_values=[1, 2, 3],
    ),
    _scenario(
        "scatter_scale_dominated_by_extreme",
        "Scatter plot",
        list(range(1, 11)) + [1000],
        None,
        {
            "chart_data_suitability": CLEAR,
            "repeated_categories": NOT_APPLICABLE,
            "extreme_value_context": DETECTED,
        },
        x_values=list(range(11)),
    ),
    _scenario(
        "scatter_typical_variation",
        "Scatter plot",
        list(range(10, 17)),
        None,
        {
            "chart_data_suitability": CLEAR,
            "repeated_categories": NOT_APPLICABLE,
            "extreme_value_context": CLEAR,
        },
        x_values=list(range(7)),
    ),
    _scenario(
        "histogram_small_sample_extreme_check_inapplicable",
        "Histogram",
        [2, 3, 4, 5],
        None,
        {
            "chart_data_suitability": CLEAR,
            "repeated_categories": NOT_APPLICABLE,
            "extreme_value_context": NOT_APPLICABLE,
        },
    ),
]


def evaluate_benchmark(scenarios=None):
    """Compare actual check statuses with the benchmark's expected labels."""
    scenarios = SCENARIOS if scenarios is None else scenarios
    results = []
    totals = defaultdict(lambda: {
        "expected_statuses": 0,
        "exact_matches": 0,
        "true_positive": 0,
        "false_positive": 0,
        "false_negative": 0,
        "true_negative": 0,
        "not_applicable": 0,
        "mismatches": 0,
    })

    for scenario in scenarios:
        actual = {
            finding["id"]: finding["status"]
            for finding in audit_chart(
                scenario["chart_type"],
                scenario["values"],
                scenario["axis_range"],
                scenario["missing_rows"],
                scenario["unsorted_line"],
                line_order_applicable=scenario["line_order_applicable"],
                x_values=scenario["x_values"],
            )
        }
        comparisons = []
        for check_id, expected_status in scenario["expected"].items():
            actual_status = actual.get(check_id, "missing")
            is_match = actual_status == expected_status
            counts = totals[check_id]
            counts["expected_statuses"] += 1
            counts["exact_matches"] += int(is_match)
            counts["mismatches"] += int(not is_match)

            if expected_status == NOT_APPLICABLE:
                counts["not_applicable"] += 1
            elif expected_status == DETECTED and actual_status == DETECTED:
                counts["true_positive"] += 1
            elif expected_status == CLEAR and actual_status == DETECTED:
                counts["false_positive"] += 1
            elif expected_status == DETECTED and actual_status == CLEAR:
                counts["false_negative"] += 1
            elif expected_status == CLEAR and actual_status == CLEAR:
                counts["true_negative"] += 1

            comparisons.append({
                "check_id": check_id,
                "expected": expected_status,
                "actual": actual_status,
                "matched": is_match,
            })

        results.append({
            "name": scenario["name"],
            "chart_type": scenario["chart_type"],
            "matched": all(item["matched"] for item in comparisons),
            "checks": comparisons,
        })

    expected_count = sum(item["expected_statuses"] for item in totals.values())
    matched_count = sum(item["exact_matches"] for item in totals.values())
    return {
        "scenario_count": len(results),
        "matched_scenarios": sum(item["matched"] for item in results),
        "expected_status_count": expected_count,
        "matched_status_count": matched_count,
        "per_check": dict(sorted(totals.items())),
        "scenarios": results,
    }


def main():
    report = evaluate_benchmark()
    print("Uncharted synthetic audit benchmark")
    print(
        f"Scenarios matched: {report['matched_scenarios']}/"
        f"{report['scenario_count']}"
    )
    print(
        f"Expected check statuses matched: {report['matched_status_count']}/"
        f"{report['expected_status_count']}"
    )
    for check_id, result in report["per_check"].items():
        print(
            f"- {check_id}: {result['exact_matches']}/"
            f"{result['expected_statuses']} exact status matches; "
            f"TP={result['true_positive']}, FP={result['false_positive']}, "
            f"FN={result['false_negative']}, TN={result['true_negative']}, "
            f"N/A={result['not_applicable']}"
        )
    print(
        "These are designed synthetic sanity cases; the counts do not estimate "
        "performance on real-world charts."
    )
    return 0 if report["matched_scenarios"] == report["scenario_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
