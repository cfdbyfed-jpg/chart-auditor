import unittest
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

try:
    import pyarrow.lib  # noqa: F401
except ImportError:
    PYARROW_AVAILABLE = False
else:
    PYARROW_AVAILABLE = True


def dataframe_context():
    return (
        nullcontext()
        if PYARROW_AVAILABLE
        else patch("streamlit.dataframe", autospec=True)
    )


def language_selector(app):
    return next(item for item in app.selectbox if item.key == "language")


class StreamlitAppSmokeTests(unittest.TestCase):
    def run_uploaded_app(self, content, chart_type=None, language="ru"):
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        with dataframe_context():
            app = AppTest.from_file(str(app_path)).run()
            if language != "ru":
                language_selector(app).select(language).run()
            app.file_uploader[0].set_value((
                "smoke.csv",
                content,
                "text/csv",
            )).run()
            if chart_type is not None:
                selector = next(
                    item for item in app.selectbox if item.key == "chart_type"
                )
                selector.select(chart_type).run()
        return app

    def test_initial_page_defaults_to_russian_and_has_upload_prompt(self):
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        with dataframe_context():
            app = AppTest.from_file(str(app_path)).run()

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.file_uploader), 1)
        self.assertIn("Загрузите CSV-файл, чтобы начать.", [item.value for item in app.info])
        self.assertEqual(language_selector(app).value, "ru")

    def test_csv_upload_builds_comparison_audit_and_exports_in_russian(self):
        content = b"Category,Reported_Value\nA,10\nA,20\nB,30\n"
        for chart_type in (
            "Bar chart",
            "Line chart",
            "Scatter plot",
            "Histogram",
            "Box plot",
        ):
            with self.subTest(chart_type=chart_type):
                app = self.run_uploaded_app(content, chart_type=chart_type)

                self.assertEqual(len(app.exception), 0)
                self.assertEqual(
                    len(app.get("plotly_chart")), 2,
                    "Unexpected app errors: "
                    f"{[item.value for item in app.error]}; "
                    f"exceptions={[item.message for item in app.exception]}",
                )
                self.assertEqual(len(app.get("download_button")), 4)

        bar_app = self.run_uploaded_app(content, chart_type="Bar chart")
        self.assertEqual(
            {item.label for item in bar_app.text_input},
            {"Заголовок графика", "Подпись оси X", "Подпись оси Y"},
        )
        self.assertTrue(any(
            "Повторяющиеся категории столбчатой диаграммы" in expander.label
            and "Обнаружен сигнал" in expander.label
            for expander in bar_app.get("expander")
        ))

    def test_language_switch_persists_after_upload_and_chart_interaction(self):
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        with dataframe_context():
            app = AppTest.from_file(str(app_path)).run()
            language_selector(app).select("en").run()
            app.file_uploader[0].set_value((
                "smoke.csv",
                b"Category,Reported_Value\nA,10\nB,20\n",
                "text/csv",
            )).run()
            next(item for item in app.selectbox if item.key == "chart_type").select(
                "Line chart"
            ).run()

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(language_selector(app).value, "en")
        self.assertIn("3. Check for possible distortions", [item.value for item in app.header])
        self.assertIn(
            "Download full audit report (JSON)",
            [item.label for item in app.get("download_button")],
        )

    def test_language_switch_updates_chart_titles_and_export_labels(self):
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        with dataframe_context():
            app = AppTest.from_file(str(app_path)).run()
            app.file_uploader[0].set_value((
                "smoke.csv",
                b"Category,Reported_Value\nA,10\nB,20\n",
                "text/csv",
            )).run()
            language_selector(app).select("en").run()

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.get("plotly_chart")), 2)
        self.assertEqual(
            next(item for item in app.text_input if item.key == "chart_title_input").value,
            "Reported_Value by Category",
        )
        self.assertIn(
            "Download audit report (CSV)",
            [item.label for item in app.get("download_button")],
        )

    def test_empty_and_header_only_csv_show_clear_russian_messages(self):
        empty_app = self.run_uploaded_app(b"")
        self.assertEqual(len(empty_app.exception), 0)
        self.assertTrue(any("пуст" in item.value.lower() for item in empty_app.error))

        header_only_app = self.run_uploaded_app(b"Category,Reported_Value\n")
        self.assertEqual(len(header_only_app.exception), 0)
        self.assertTrue(any(
            "нет строк с данными" in item.value.lower()
            for item in header_only_app.warning
        ))

    def test_non_numeric_csv_explains_what_input_is_needed_in_russian(self):
        app = self.run_uploaded_app(b"name,date\nA,2026-01-01\nB,2026-01-02\n")

        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("числовой столбец" in item.value.lower() for item in app.warning))

    def test_csv_error_messages_are_translated_after_language_switch(self):
        app = self.run_uploaded_app(b"", language="en")
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("uploaded file is empty" in item.value.lower() for item in app.error))


if __name__ == "__main__":
    unittest.main()
