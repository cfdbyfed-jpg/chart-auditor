"""CSV loading helpers with user-facing validation errors."""

import pandas as pd


class CSVLoadError(ValueError):
    """An input CSV could not be read in a useful form."""

    def __init__(self, message, code):
        super().__init__(message)
        self.code = code


def load_csv(uploaded_file):
    """Read a CSV upload and translate common parse failures into clear messages."""
    try:
        return pd.read_csv(uploaded_file)
    except pd.errors.EmptyDataError as error:
        raise CSVLoadError(
            "The uploaded file is empty or does not contain a CSV header row.",
            "csv_empty_error",
        ) from error
    except UnicodeDecodeError as error:
        raise CSVLoadError(
            "The file encoding could not be read. Save the CSV as UTF-8 and upload it again.",
            "csv_encoding_error",
        ) from error
    except pd.errors.ParserError as error:
        raise CSVLoadError(
            "The CSV rows could not be parsed. Check the delimiter, quotes, and row lengths.",
            "csv_parse_error",
        ) from error
