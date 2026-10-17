import io
import unittest

import pandas as pd

from data_loader import CSVLoadError, load_csv


class CSVLoadTests(unittest.TestCase):
    def test_valid_unicode_csv_is_loaded(self):
        uploaded = io.BytesIO("категория,значение\nА,12\nБ,15\n".encode("utf-8"))

        frame = load_csv(uploaded)

        self.assertEqual(list(frame.columns), ["категория", "значение"])
        self.assertEqual(frame["значение"].tolist(), [12, 15])

    def test_empty_csv_has_a_clear_error(self):
        with self.assertRaisesRegex(CSVLoadError, "empty"):
            load_csv(io.BytesIO(b""))

    def test_malformed_csv_has_a_clear_error(self):
        uploaded = io.BytesIO(b'category,value\nA,"unterminated\n')

        with self.assertRaisesRegex(CSVLoadError, "could not be parsed"):
            load_csv(uploaded)

    def test_unsupported_encoding_has_a_clear_error(self):
        with self.assertRaisesRegex(CSVLoadError, "UTF-8"):
            load_csv(io.BytesIO(b"category,value\nA,\xff\n"))

    def test_header_only_csv_is_returned_as_empty_frame_for_ui_handling(self):
        frame = load_csv(io.BytesIO(b"category,value\n"))

        self.assertTrue(frame.empty)
        self.assertEqual(list(frame.columns), ["category", "value"])


if __name__ == "__main__":
    unittest.main()
