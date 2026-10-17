# Uncharted — Chart Integrity Auditor

[🚀 Try Uncharted Live](https://chart-auditor-ckzu7qsioqrvgqnhykdctg.streamlit.app/) — Инструмент для анализа графиков и выявления потенциально вводящей в заблуждение визуализации.

Uncharted is a Streamlit application for exploring how chart settings affect the reading of data. It builds charts from uploaded CSV files, checks a set of transparent audit signals, and compares the selected view with a recommended scale. A signal is a reason to review a chart, not proof of misleading intent.

## Live demo and screenshots

- **Live demo:** Not deployed yet. Add the Streamlit Community Cloud URL here after publication.
- **Screenshots:** Add screenshots of the interface and chart comparison here after publication.

Do not upload confidential, personal, or regulated data to a public demo. The application code analyzes uploads in the active Streamlit session and does not explicitly write uploaded CSV files to disk or send them to external services. This does not guarantee how the hosting platform handles data; use non-sensitive sample data in a public deployment.

## Features

- Upload a CSV, inspect its rows and columns, and review row, column, and missing-value counts.
- Switch the full interface between Russian and English. Russian is the default language.
- Build five Plotly chart types: bar chart, line chart, scatter plot, histogram, and box plot.
- Select columns, edit chart titles and axis labels, and optionally set an axis range for the original view.
- Review audit status, evidence, numerical results, recommendations, and limitations.
- Compare the original chart with a recommended view that includes the observed data range. Bar-chart recommendations include zero as the baseline.
- Download the audit report as CSV or JSON, and download each chart separately as interactive HTML.
- Run unit tests and a synthetic expected-outcome benchmark.

## Audit checks

- **Bar-chart baseline and data range:** checks whether the selected Y range clips data or excludes zero.
- **Estimated visual amplification:** estimates how much a truncated baseline may change apparent positive bar-length differences when the estimate is meaningful.
- **Y-axis data visibility:** checks whether selected axis bounds hide plotted values. For histograms, the corresponding check applies to the X range.
- **Rows omitted from the chart:** reports rows excluded because required X/Y values are missing or Y values are non-finite.
- **Line-chart X order:** checks whether numeric or date-like X values are connected in file order instead of ascending order; it does not infer the intended order of categories.
- **Chart and data suitability:** flags constant Y values and bar charts with more than 20 distinct categories for review. The category threshold is a heuristic.
- **Repeated bar-chart categories:** identifies repeated X values that may overlap. The app does not silently sum, average, or remove observations.
- **Potentially influential extreme values:** uses a 3×IQR screen and requires the full range to be at least 10× the IQR to raise a signal. Extreme values are not treated as errors and are never removed.

Checks are rule-based and inspect the chart settings and data supplied to the app. They do not determine author intent, know the domain context, inspect uploaded chart images, or cover every design choice. Review the evidence and limitations before changing a chart.

## Languages and exports

Choose **Русский** or **English** from the sidebar. Russian is selected by default, and the choice remains active during interactions in the current Streamlit session. Interface text, audit explanations and recommendations, chart defaults, report text, and chart titles/axis labels use the selected language. Source column names and values remain as provided in the CSV.

CSV and JSON reports include the localized check text and status label; JSON also retains stable check IDs and status codes. Each HTML file contains one interactive Plotly chart with its current title and axis labels.

## Run locally

Requirements: Python 3.12 is the current Streamlit Community Cloud default; use a supported Python version and select the same version locally and in Cloud. Dependencies are pinned in `requirements.txt`.

On Windows, open PowerShell in the project root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

If Python 3.12 is not installed, create the environment with another supported Python version and choose that same version when deploying. The app opens in a browser. Upload `examples/uncharted_demo.csv` to try the included sample data.

## Tests and synthetic evaluation

Run the test suite from the project root:

```powershell
python -m unittest discover -s tests -v
```

Run the synthetic benchmark:

```powershell
python -m evaluation.benchmark
```

The benchmark contains 21 designed scenarios covering all five chart types and compares their expected statuses with the auditor's results. The recorded run matched 87 of 87 expected statuses. These hand-authored scenarios are not a representative real-world dataset and do not establish general precision, recall, or F1-score. See [`evaluation/README.md`](evaluation/README.md) for the method and limitations.

## Project structure

```text
app.py                          Streamlit interface and Plotly chart creation
auditor.py                      Rule-based checks and recommended numeric ranges
data_loader.py                  CSV parsing and input validation
export_utils.py                 CSV, JSON, and interactive HTML export
localization.py                 Locale loading and translated audit presentation
locales/ru.json                 Russian interface and audit text
locales/en.json                 English interface and audit text
examples/uncharted_demo.csv     Sample data for manual exploration
tests/                          Unit and Streamlit AppTest smoke tests
evaluation/                     Synthetic expected-outcome benchmark
requirements.txt                Pinned direct Python dependencies
README_RU.md                     Russian project overview
STREAMLIT_CLOUD_DEPLOYMENT_RU.md Russian self-service deployment guide
```

## Known limitations

- The app builds charts from CSV data; it does not inspect screenshots or arbitrary chart images.
- It charts one selected measure at a time and does not provide pie/proportion charts or compare scales across multiple series.
- Missing-value checks report excluded row counts, not why values are missing.
- Large-category and extreme-value thresholds are review heuristics, not universal standards.
- Manual axis ranges may be valid for a domain-specific reason.
- Community Cloud has platform resource limits and may hibernate apps after inactivity. See the [official status and limitations page](https://docs.streamlit.io/deploy/streamlit-community-cloud/status).
- The hosted app has not been deployed yet; no public URL is available.

## Dependencies

Python, Streamlit, Pandas, and Plotly. Versions are pinned in `requirements.txt`. The app does not require API keys, a database, or external services.

## Deployment

See [`STREAMLIT_CLOUD_DEPLOYMENT_RU.md`](STREAMLIT_CLOUD_DEPLOYMENT_RU.md) for the Russian step-by-step guide. Deployment uses GitHub as the source repository and `app.py` as the entrypoint. For current platform instructions, refer to the official [Community Cloud deployment guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy).
