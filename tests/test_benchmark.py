import unittest

from evaluation.benchmark import SCENARIOS, evaluate_benchmark


class BenchmarkTests(unittest.TestCase):
    def test_synthetic_scenarios_match_expected_audit_statuses(self):
        report = evaluate_benchmark()

        self.assertEqual(report["scenario_count"], len(SCENARIOS))
        self.assertEqual(report["matched_scenarios"], len(SCENARIOS))
        self.assertEqual(
            report["matched_status_count"], report["expected_status_count"]
        )
        self.assertTrue(all(scenario["matched"] for scenario in report["scenarios"]))

    def test_benchmark_covers_all_chart_types_and_audit_rules(self):
        report = evaluate_benchmark()

        chart_types = {scenario["chart_type"] for scenario in SCENARIOS}
        self.assertEqual(chart_types, {
            "Bar chart", "Line chart", "Scatter plot", "Histogram", "Box plot"
        })
        self.assertEqual(set(report["per_check"]), {
            "axis_data_visibility",
            "bar_axis_integrity",
            "chart_data_suitability",
            "difference_amplification",
            "extreme_value_context",
            "incomplete_rows",
            "line_x_order",
            "repeated_categories",
        })

    def test_confusion_counts_exclude_not_applicable_statuses(self):
        report = evaluate_benchmark()
        bar_axis = report["per_check"]["bar_axis_integrity"]

        self.assertEqual(bar_axis["true_positive"], 2)
        self.assertEqual(bar_axis["false_positive"], 0)
        self.assertEqual(bar_axis["false_negative"], 0)
        self.assertEqual(bar_axis["not_applicable"], 10)


if __name__ == "__main__":
    unittest.main()
