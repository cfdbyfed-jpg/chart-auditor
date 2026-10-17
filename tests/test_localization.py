import unittest

import pandas as pd

from auditor import audit_chart
from localization import get_catalog, localize_findings, tr


class LocalizationTests(unittest.TestCase):
    def test_catalogs_load_and_default_ui_strings_are_russian(self):
        self.assertEqual(tr("ru", "upload_prompt"), "Загрузите CSV-файл, чтобы начать.")
        self.assertEqual(tr("en", "upload_prompt"), "Upload a CSV file to get started.")
        self.assertEqual(get_catalog("unsupported")["language"]["label"], "Язык / Language")

    def test_bar_audit_result_is_fully_localized_without_changing_status_or_metrics(self):
        values = pd.Series([95.0, 100.0, 150.0])
        categories = pd.Series(["A", "B", "C"])
        findings = audit_chart(
            "Bar chart", values, [102.5, 142.5], 0, False, x_values=categories
        )
        translated = localize_findings(
            findings,
            "ru",
            chart_type="Bar chart",
            axis_name="Y-axis",
            values=values,
            original_range=[102.5, 142.5],
            missing_rows=0,
            line_sort_kind=None,
            unsorted_line=False,
            x_values=categories,
        )
        bar_check = next(item for item in translated if item["id"] == "bar_axis_integrity")
        repeated_check = next(item for item in translated if item["id"] == "repeated_categories")

        self.assertEqual(bar_check["status"], "detected")
        self.assertEqual(bar_check["status_label"], "Обнаружен сигнал")
        self.assertIn("Наблюдаемые данные", bar_check["evidence"])
        self.assertIn("102,5", bar_check["evidence"])
        self.assertIn("Расширьте диапазон", bar_check["recommendation"])
        self.assertEqual(repeated_check["status"], "clear")
        self.assertIn("уникальные категории X", repeated_check["evidence"])
        self.assertEqual(
            next(item for item in findings if item["id"] == "bar_axis_integrity")["metrics"],
            bar_check["metrics"],
        )

    def test_axis_visibility_and_line_order_are_localized_in_both_languages(self):
        values = pd.Series([95.0, 110.0, 150.0])
        x_values = pd.Series([3, 1, 2])
        findings = audit_chart(
            "Line chart", values, [100, 140], 0, True,
            line_order_applicable=True, x_values=x_values,
        )
        context = {
            "chart_type": "Line chart",
            "axis_name": "Y-axis",
            "values": values,
            "original_range": [100, 140],
            "missing_rows": 0,
            "line_sort_kind": "numeric",
            "unsorted_line": True,
            "x_values": x_values,
        }

        russian = localize_findings(findings, "ru", **context)
        english = localize_findings(findings, "en", **context)
        ru_visibility = next(item for item in russian if item["id"] == "axis_data_visibility")
        ru_order = next(item for item in russian if item["id"] == "line_x_order")
        en_order = next(item for item in english if item["id"] == "line_x_order")

        self.assertIn("Видимость данных на оси Y", ru_visibility["title"])
        self.assertIn("Значения ниже минимума оси обрезаны", ru_visibility["evidence"])
        self.assertIn("порядке файла", ru_order["evidence"])
        self.assertIn("not sorted order", en_order["evidence"])
        self.assertEqual(en_order["status"], "detected")

    def test_all_audit_checks_have_localized_text_for_each_chart_type(self):
        values = pd.Series([95.0, 100.0, 105.0, 110.0, 150.0])
        x_values = pd.Series(["A", "B", "A", "C", "D"])
        cases = (
            ("Bar chart", x_values, None),
            ("Line chart", pd.Series([5, 1, 4, 2, 3]), "numeric"),
            ("Scatter plot", x_values, None),
            ("Histogram", None, None),
            ("Box plot", x_values, None),
        )

        for chart_type, chart_x, sort_kind in cases:
            with self.subTest(chart_type=chart_type):
                findings = audit_chart(
                    chart_type,
                    values,
                    [98, 140],
                    0,
                    sort_kind is not None,
                    line_order_applicable=sort_kind is not None,
                    x_values=chart_x,
                )
                localized = localize_findings(
                    findings,
                    "ru",
                    chart_type=chart_type,
                    axis_name="X-axis" if chart_type == "Histogram" else "Y-axis",
                    values=values,
                    original_range=[98, 140],
                    missing_rows=0,
                    line_sort_kind=sort_kind,
                    unsorted_line=sort_kind is not None,
                    x_values=chart_x,
                )
                self.assertEqual(len(localized), len(findings))
                self.assertTrue(all(item.get("status_label") for item in localized))
                self.assertTrue(all(item.get("title") for item in localized))
                self.assertTrue(all(item.get("evidence") for item in localized))
                self.assertFalse(any(
                    item["title"] == raw["title"]
                    for raw, item in zip(findings, localized)
                ))


if __name__ == "__main__":
    unittest.main()
