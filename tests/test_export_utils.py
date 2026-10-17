import csv
import io
import json
import unittest

import plotly.express as px
import pandas as pd

from auditor import audit_chart
from localization import tr

from export_utils import (
    audit_csv_bytes,
    audit_json_bytes,
    figure_filename,
    figure_html_bytes,
)


class AuditReportExportTests(unittest.TestCase):
    def sample_check(self):
        return {
            "id": "bar_axis_integrity",
            "title": "Ось Y, категории; проверка",
            "status": "detected",
            "explanation": "Проверка: «значение»\nвторая строка",
            "impact": "Различие выглядит сильнее",
            "evidence": "Данные: 95–150, ось 100–140",
            "metrics": {"data_ratio": 1.5, "factor": 4.0},
            "recommendation": "Добавить ноль",
            "limitations": "Это сигнал, не доказательство.",
        }

    def test_csv_contains_all_fields_unicode_and_escaped_special_characters(self):
        content = audit_csv_bytes([self.sample_check()]).decode("utf-8-sig")
        rows = list(csv.DictReader(io.StringIO(content, newline="")))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Check"], "Ось Y, категории; проверка")
        self.assertEqual(rows[0]["Description"], "Проверка: «значение»\nвторая строка")
        self.assertEqual(json.loads(rows[0]["Numerical results"]), {
            "data_ratio": 1.5,
            "factor": 4.0,
        })
        self.assertEqual(rows[0]["Recommendation"], "Добавить ноль")
        self.assertEqual(rows[0]["Limitations"], "Это сигнал, не доказательство.")

    def test_json_contains_full_unicode_report(self):
        report = json.loads(audit_json_bytes([self.sample_check()]).decode("utf-8"))

        self.assertEqual(report["report"], "Uncharted chart audit")
        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["checks"][0]["title"], "Ось Y, категории; проверка")
        self.assertEqual(report["checks"][0]["metrics"]["factor"], 4.0)
        self.assertEqual(report["checks"][0]["limitations"], "Это сигнал, не доказательство.")

    def test_empty_report_exports_header_and_empty_checks(self):
        csv_content = audit_csv_bytes([]).decode("utf-8-sig")
        csv_rows = list(csv.reader(io.StringIO(csv_content, newline="")))
        report = json.loads(audit_json_bytes([]).decode("utf-8"))

        self.assertEqual(len(csv_rows), 1)
        self.assertIn("Check", csv_rows[0])
        self.assertEqual(report["checks"], [])

    def test_missing_optional_fields_have_safe_defaults(self):
        minimal = {"title": "Minimal", "status": "clear"}
        csv_rows = list(csv.DictReader(io.StringIO(
            audit_csv_bytes([minimal]).decode("utf-8-sig"), newline=""
        )))
        json_check = json.loads(audit_json_bytes([minimal]).decode("utf-8"))["checks"][0]

        self.assertEqual(csv_rows[0]["Evidence"], "")
        self.assertEqual(json.loads(csv_rows[0]["Numerical results"]), {})
        self.assertEqual(json_check["id"], "")
        self.assertEqual(json_check["metrics"], {})
        self.assertEqual(json_check["recommendation"], "")

    def audit_context(self):
        values = pd.Series([95, 100, 150])
        categories = pd.Series(["А", "Б", "В"])
        findings = audit_chart(
            "Bar chart", values, [102.5, 142.5], 0, False, x_values=categories
        )
        context = {
            "chart_type": "Bar chart",
            "axis_name": "Y-axis",
            "values": values,
            "original_range": [102.5, 142.5],
            "missing_rows": 0,
            "line_sort_kind": None,
            "unsorted_line": False,
            "x_values": categories,
        }
        return findings, context

    def test_russian_csv_and_json_exports_translate_report_content(self):
        findings, context = self.audit_context()
        csv_content = audit_csv_bytes(findings, "ru", **context).decode("utf-8-sig")
        rows = list(csv.DictReader(io.StringIO(csv_content, newline="")))
        report = json.loads(audit_json_bytes(findings, "ru", **context).decode("utf-8"))
        bar_check = next(
            check for check in report["checks"] if check["id"] == "bar_axis_integrity"
        )

        self.assertIn("Проверка", rows[0])
        self.assertEqual(rows[0]["Проверка"], "Основание столбцов и диапазон данных")
        self.assertEqual(rows[0]["Статус"], "Обнаружен сигнал")
        self.assertEqual(report["language"], "ru")
        self.assertEqual(report["report"], "Отчёт аудита графика Uncharted")
        self.assertEqual(bar_check["status"], "detected")
        self.assertEqual(bar_check["status_label"], "Обнаружен сигнал")
        self.assertIn("Наблюдаемые данные", bar_check["evidence"])
        self.assertIn("102,5", bar_check["evidence"])
        self.assertIn("Расширьте диапазон", bar_check["recommendation"])

    def test_english_export_has_english_headers_and_status_labels(self):
        findings, context = self.audit_context()
        rows = list(csv.DictReader(io.StringIO(
            audit_csv_bytes(findings, "en", **context).decode("utf-8-sig"), newline=""
        )))
        report = json.loads(audit_json_bytes(findings, "en", **context).decode("utf-8"))
        bar_check = next(
            check for check in report["checks"] if check["id"] == "bar_axis_integrity"
        )

        self.assertEqual(rows[0]["Check"], "Bar-chart baseline and data range")
        self.assertEqual(rows[0]["Status"], "Signal detected")
        self.assertEqual(report["language"], "en")
        self.assertEqual(bar_check["status_label"], "Signal detected")
        self.assertIn("Observed data", bar_check["evidence"])

    def test_empty_reports_keep_the_selected_language(self):
        russian_csv = list(csv.reader(io.StringIO(
            audit_csv_bytes([], "ru").decode("utf-8-sig"), newline=""
        )))
        russian_json = json.loads(audit_json_bytes([], "ru").decode("utf-8"))
        english_csv = list(csv.reader(io.StringIO(
            audit_csv_bytes([], "en").decode("utf-8-sig"), newline=""
        )))
        english_json = json.loads(audit_json_bytes([], "en").decode("utf-8"))

        self.assertEqual(russian_csv[0][0], "Код проверки")
        self.assertEqual(russian_json["language"], "ru")
        self.assertEqual(russian_json["checks"], [])
        self.assertEqual(english_csv[0][0], "Check ID")
        self.assertEqual(english_json["language"], "en")
        self.assertEqual(english_json["checks"], [])


class PlotlyExportTests(unittest.TestCase):
    def test_original_and_recommended_figures_export_as_separate_interactive_html(self):
        original = px.bar(x=["A", "B"], y=[95, 150], title="Original values")
        recommended = px.bar(x=["A", "B"], y=[95, 150], title="Recommended scale")

        original_html = figure_html_bytes(original)
        recommended_html = figure_html_bytes(recommended)

        self.assertNotEqual(original_html, recommended_html)
        self.assertIn(b"plotly.js", original_html)
        self.assertIn(b"Original values", original_html)
        self.assertIn(b"Recommended scale", recommended_html)
        self.assertEqual(figure_filename("Reported_Value by Category", "original"),
                         "uncharted_reported_value_by_category_original.html")
        self.assertEqual(figure_filename("Reported_Value by Category", "recommended"),
                         "uncharted_reported_value_by_category_recommended.html")

    def test_html_export_preserves_selected_language_chart_titles_and_axis_labels(self):
        russian_title = tr("ru", "chart_by", measure="Продажи", category="Месяц")
        english_title = tr("en", "chart_by", measure="Sales", category="Month")
        russian = px.bar(x=["Январь"], y=[10], title=russian_title)
        russian.update_xaxes(title_text=tr("ru", "axis_x"))
        english = px.bar(x=["January"], y=[10], title=english_title)
        english.update_xaxes(title_text=tr("en", "axis_x"))

        russian_html = figure_html_bytes(russian)
        english_html = figure_html_bytes(english)

        self.assertIn(b"\\u041f\\u0440\\u043e\\u0434\\u0430\\u0436\\u0438", russian_html)
        self.assertIn(b"\\u041e\\u0441\\u044c X", russian_html)
        self.assertIn(b"Sales by Month", english_html)
        self.assertIn(b"X-axis", english_html)


if __name__ == "__main__":
    unittest.main()
