import math
import unittest
import warnings

import pandas as pd

from auditor import (
    CLEAR,
    DETECTED,
    NOT_APPLICABLE,
    audit_chart,
    corrected_y_range,
    get_numeric_columns,
    line_sort_values,
)


def find_check(results, check_id):
    return next(result for result in results if result["id"] == check_id)


class AuditorTests(unittest.TestCase):
    def audit_bar(self, values, axis_range, categories=None, missing=0):
        if categories is None:
            categories = [f"category-{index}" for index in range(len(values))]
        return audit_chart(
            "Bar chart",
            pd.Series(values),
            axis_range,
            missing,
            False,
            x_values=categories,
        )

    def test_zero_baseline_is_clear_with_no_amplification(self):
        results = self.audit_bar([100, 150], [0, 160])

        self.assertEqual(find_check(results, "bar_axis_integrity")["status"], CLEAR)
        estimate = find_check(results, "difference_amplification")
        self.assertEqual(estimate["status"], CLEAR)
        self.assertAlmostEqual(estimate["metrics"]["amplification_factor"], 1.0)

    def test_nonzero_baseline_reports_exact_amplification(self):
        results = self.audit_bar([100, 150], [90, 160])
        baseline = find_check(results, "bar_axis_integrity")
        estimate = find_check(results, "difference_amplification")

        self.assertEqual(baseline["status"], DETECTED)
        self.assertEqual(estimate["status"], DETECTED)
        self.assertAlmostEqual(estimate["metrics"]["data_ratio"], 1.5)
        self.assertAlmostEqual(estimate["metrics"]["displayed_ratio"], 6.0)
        self.assertAlmostEqual(estimate["metrics"]["amplification_factor"], 4.0)

    def test_automatic_bar_scale_is_not_flagged(self):
        results = self.audit_bar([95, 150], None)

        self.assertEqual(find_check(results, "bar_axis_integrity")["status"], CLEAR)
        self.assertEqual(find_check(results, "difference_amplification")["status"], CLEAR)

    def test_axis_that_clips_data_is_flagged_without_ratio(self):
        results = self.audit_bar([95, 150], [100, 140])
        baseline = find_check(results, "bar_axis_integrity")
        estimate = find_check(results, "difference_amplification")

        self.assertEqual(baseline["status"], DETECTED)
        self.assertIn("falls outside", baseline["evidence"])
        self.assertEqual(estimate["status"], NOT_APPLICABLE)
        self.assertEqual(estimate["metrics"], {})

    def test_equal_values_do_not_produce_amplification(self):
        result = find_check(self.audit_bar([10, 10], [0, 12]), "difference_amplification")
        self.assertEqual(result["status"], NOT_APPLICABLE)

    def test_zero_or_negative_values_do_not_produce_positive_ratio(self):
        for values in ([0, 10], [-5, 10], [-10, -5]):
            with self.subTest(values=values):
                result = find_check(self.audit_bar(values, [-12, 12]), "difference_amplification")
                self.assertEqual(result["status"], NOT_APPLICABLE)

    def test_single_category_does_not_produce_between_category_ratio(self):
        result = find_check(
            self.audit_bar([100, 150], [90, 160], categories=["A", "A"]),
            "difference_amplification",
        )
        self.assertEqual(result["status"], NOT_APPLICABLE)
        self.assertIn("one distinct X category", result["evidence"])

    def test_empty_or_nonnumeric_values_are_not_applicable(self):
        for values in ([], ["bad", "input"]):
            with self.subTest(values=values):
                results = self.audit_bar(values, [0, 10])
                self.assertEqual(
                    find_check(results, "bar_axis_integrity")["status"],
                    NOT_APPLICABLE,
                )
                self.assertEqual(
                    find_check(results, "difference_amplification")["status"],
                    NOT_APPLICABLE,
                )

    def test_missing_rows_are_reported_and_clean_rows_pass(self):
        results = self.audit_bar([100, None, 150], [0, 160], missing=1)
        incomplete = find_check(results, "incomplete_rows")

        self.assertEqual(incomplete["status"], DETECTED)
        self.assertEqual(incomplete["metrics"]["excluded_rows"], 1)

        clean = find_check(self.audit_bar([100, 150], [0, 160]), "incomplete_rows")
        self.assertEqual(clean["status"], CLEAR)

    def test_line_order_check_distinguishes_sorted_unsorted_and_inapplicable(self):
        unsorted = audit_chart(
            "Line chart", [1, 2, 3], None, 0, True,
            line_order_applicable=True,
        )
        self.assertEqual(find_check(unsorted, "line_x_order")["status"], DETECTED)

        sorted_results = audit_chart(
            "Line chart", [1, 2, 3], None, 0, False,
            line_order_applicable=True,
        )
        self.assertEqual(find_check(sorted_results, "line_x_order")["status"], CLEAR)

        categorical = audit_chart(
            "Line chart", [1, 2], None, 0, False,
            line_order_applicable=False,
        )
        self.assertEqual(find_check(categorical, "line_x_order")["status"], NOT_APPLICABLE)

    def test_line_and_scatter_y_axis_clipping_is_reported(self):
        for chart_type, axis_range in (
            ("Line chart", [2, 4]),
            ("Scatter plot", [0, 2]),
        ):
            with self.subTest(chart_type=chart_type):
                results = audit_chart(
                    chart_type, [1, 2, 3], axis_range, 0, False
                )
                visibility = find_check(results, "axis_data_visibility")

                self.assertEqual(visibility["status"], DETECTED)
                self.assertIn("clipped", visibility["evidence"])
                self.assertTrue(
                    visibility["metrics"]["clips_low"]
                    or visibility["metrics"]["clips_high"]
                )

    def test_line_and_scatter_full_or_automatic_y_axis_is_clear(self):
        for chart_type, axis_range in (
            ("Line chart", [0, 4]),
            ("Scatter plot", None),
        ):
            with self.subTest(chart_type=chart_type):
                results = audit_chart(
                    chart_type, [1, 2, 3], axis_range, 0, False
                )
                visibility = find_check(results, "axis_data_visibility")

                self.assertEqual(visibility["status"], CLEAR)

    def test_bar_chart_does_not_duplicate_its_axis_clipping_check(self):
        results = self.audit_bar([1, 2, 3], [0, 4])

        self.assertNotIn("axis_data_visibility", {result["id"] for result in results})

    def test_histogram_checks_x_axis_visibility_without_bar_baseline_rules(self):
        results = audit_chart("Histogram", [1, 2, 3, 4], [1.5, 3.5], 0, False)
        visibility = find_check(results, "axis_data_visibility")

        self.assertEqual(visibility["title"], "X-axis data visibility")
        self.assertEqual(visibility["status"], DETECTED)
        self.assertIn("Values below", visibility["evidence"])
        self.assertIn("Values above", visibility["evidence"])
        self.assertEqual(find_check(results, "bar_axis_integrity")["status"], NOT_APPLICABLE)
        self.assertEqual(find_check(results, "difference_amplification")["status"], NOT_APPLICABLE)

    def test_histogram_automatic_range_and_missing_values_are_reported(self):
        results = audit_chart("Histogram", [1, None, 3], None, 1, False)

        self.assertEqual(find_check(results, "axis_data_visibility")["status"], CLEAR)
        self.assertEqual(find_check(results, "incomplete_rows")["status"], DETECTED)
        self.assertIn("histogram value", find_check(results, "incomplete_rows")["evidence"])

    def test_histogram_recommended_range_preserves_negative_and_positive_values(self):
        axis_range = corrected_y_range([-10, 20], "Histogram")

        self.assertLess(axis_range[0], -10)
        self.assertGreater(axis_range[1], 20)

    def test_box_plot_uses_y_axis_visibility_and_all_observation_rows(self):
        results = audit_chart("Box plot", [1, 2, 3, 4], [1.5, 3.5], 1, False)
        visibility = find_check(results, "axis_data_visibility")
        incomplete = find_check(results, "incomplete_rows")

        self.assertEqual(visibility["title"], "Y-axis data visibility")
        self.assertEqual(visibility["status"], DETECTED)
        self.assertIn("box-plot distribution", visibility["impact"])
        self.assertNotIn("line or scatter", visibility["impact"])
        self.assertEqual(incomplete["status"], DETECTED)
        self.assertIn("Y value", incomplete["evidence"])
        self.assertEqual(find_check(results, "bar_axis_integrity")["status"], NOT_APPLICABLE)

    def test_single_categorical_x_value_has_no_inferable_line_order(self):
        values, kind = line_sort_values(pd.Series(["A"]))
        self.assertIsNone(values)
        self.assertIsNone(kind)

    def test_categorical_line_x_does_not_emit_date_inference_warnings(self):
        with warnings.catch_warnings(record=True) as emitted:
            warnings.simplefilter("always")
            values, kind = line_sort_values(pd.Series(["North", "South", "West"]))

        self.assertIsNone(values)
        self.assertIsNone(kind)
        self.assertEqual(emitted, [])

        dates, kind = line_sort_values(pd.Series(["2026-01-02", "2026-01-01"]))
        self.assertEqual(kind, "date")
        self.assertTrue(dates.is_monotonic_decreasing)

    def test_numeric_column_discovery_handles_no_numeric_columns(self):
        frame = pd.DataFrame({"name": ["A", "B"], "date": ["2026-01-01", "2026-01-02"]})
        self.assertEqual(get_numeric_columns(frame), [])
        frame["value"] = [1, 2]
        self.assertEqual(get_numeric_columns(frame), ["value"])

    def test_corrected_ranges_are_valid_for_zero_negative_and_extreme_values(self):
        self.assertEqual(corrected_y_range([0, 0], "Bar chart"), [-1.0, 1.0])
        negative_range = corrected_y_range([-10, -5], "Bar chart")
        self.assertLess(negative_range[0], -10)
        self.assertEqual(negative_range[1], 0.0)

        extreme_range = corrected_y_range([-1e308, 1e308], "Line chart")
        self.assertTrue(all(math.isfinite(bound) for bound in extreme_range))

    def test_extreme_ratios_are_left_unestimated_when_not_representable(self):
        result = find_check(
            self.audit_bar([1e-300, 1e300], [5e-301, 1.1e300]),
            "difference_amplification",
        )
        self.assertEqual(result["status"], NOT_APPLICABLE)
        self.assertEqual(result["metrics"], {})
        self.assertIn("exceeds the finite numeric range", result["evidence"])

    def test_bar_category_count_and_repeated_categories_are_reviewed(self):
        many = audit_chart(
            "Bar chart", list(range(25)), [0, 25], 0, False,
            x_values=[f"category-{index}" for index in range(25)],
        )
        suitability = find_check(many, "chart_data_suitability")
        self.assertEqual(suitability["status"], DETECTED)
        self.assertEqual(suitability["metrics"]["bar_category_count"], 25)

        repeated = audit_chart(
            "Bar chart", [10, 20, 30], [0, 35], 0, False,
            x_values=["A", "A", "B"],
        )
        duplicate_check = find_check(repeated, "repeated_categories")
        self.assertEqual(duplicate_check["status"], DETECTED)
        self.assertEqual(duplicate_check["metrics"]["duplicate_rows"], 1)
        self.assertIn("does not aggregate", duplicate_check["recommendation"])

    def test_repeated_categories_are_not_flagged_for_box_plot(self):
        results = audit_chart(
            "Box plot", [1, 2, 3, 4], None, 0, False,
            x_values=["A", "A", "B", "B"],
        )
        self.assertEqual(
            find_check(results, "repeated_categories")["status"],
            NOT_APPLICABLE,
        )

    def test_constant_data_and_extreme_values_are_reviewed_conservatively(self):
        constant = audit_chart("Line chart", [5, 5, 5], None, 0, False)
        self.assertEqual(
            find_check(constant, "chart_data_suitability")["status"],
            DETECTED,
        )
        self.assertEqual(
            find_check(constant, "extreme_value_context")["status"],
            NOT_APPLICABLE,
        )

        extreme = audit_chart(
            "Scatter plot", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1000], None, 0, False
        )
        result = find_check(extreme, "extreme_value_context")
        self.assertEqual(result["status"], DETECTED)
        self.assertEqual(result["metrics"]["outlier_rows"], 1)
        self.assertIn("not proof", result["limitations"])

    def test_typical_variation_does_not_trigger_extreme_value_signal(self):
        results = audit_chart(
            "Line chart", [10, 11, 12, 13, 14, 15, 16], None, 0, False
        )
        self.assertEqual(
            find_check(results, "extreme_value_context")["status"], CLEAR
        )


if __name__ == "__main__":
    unittest.main()
