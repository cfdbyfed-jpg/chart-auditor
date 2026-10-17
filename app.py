
import math

import streamlit as st
import pandas as pd
import plotly.express as px
from auditor import (
    audit_chart,
    corrected_y_range,
    get_numeric_columns,
    line_sort_values,
)
from export_utils import (
    audit_csv_bytes,
    audit_json_bytes,
    figure_filename,
    figure_html_bytes,
)
from data_loader import CSVLoadError, load_csv
from localization import get_catalog, localize_findings, tr


def make_chart(
    frame, x_column, y_column, chart_type, title, x_label=None, y_label=None
):
    """Build a supported chart from the selected frame and columns."""
    if chart_type == "Histogram":
        figure = px.histogram(frame, x=x_column, title=title)
    elif chart_type == "Box plot":
        figure = px.box(frame, x=x_column, y=y_column, title=title)
    elif chart_type == "Bar chart":
        figure = px.bar(frame, x=x_column, y=y_column, title=title)
    elif chart_type == "Line chart":
        figure = px.line(
            frame,
            x=x_column,
            y=y_column,
            title=title,
            markers=True,
        )
    else:
        figure = px.scatter(frame, x=x_column, y=y_column, title=title)

    if x_label is not None:
        figure.update_xaxes(title_text=x_label)
    if y_label is not None:
        figure.update_yaxes(title_text=y_label)
    return figure


def sync_default_text_input(key, default_value):
    """Refresh translated defaults while preserving values edited by the user."""
    default_key = f"_{key}_default"
    if key not in st.session_state:
        st.session_state[key] = default_value
    elif st.session_state.get(default_key) == st.session_state[key]:
        st.session_state[key] = default_value
    st.session_state[default_key] = default_value

st.set_page_config(page_title="Uncharted", page_icon="📊", layout="wide")

st.session_state.setdefault("language", "ru")
language = st.sidebar.selectbox(
    get_catalog(st.session_state["language"])["language"]["label"],
    options=("ru", "en"),
    format_func=lambda code: get_catalog(code)["language"][code],
    key="language",
)

st.title("📊 Uncharted")
st.subheader(tr(language, "subtitle"))
st.write(tr(language, "description"))

st.divider()

st.header(tr(language, "section_upload"))

uploaded_file = st.file_uploader(
    tr(language, "upload_label"),
    type=["csv"],
    key="uploaded_csv",
)

if uploaded_file is not None:
    try:
        data = load_csv(uploaded_file)

        st.success(tr(language, "upload_success"))

        st.subheader(tr(language, "data_preview"))
        st.dataframe(data, width="stretch")

        col1, col2, col3 = st.columns(3)

        col1.metric(tr(language, "rows"), data.shape[0])
        col2.metric(tr(language, "columns"), data.shape[1])
        col3.metric(
            tr(language, "missing_values"),
            int(data.isna().sum().sum())
        )

        if data.empty:
            st.warning(tr(language, "header_only"))
            st.stop()

        st.divider()
        st.header(tr(language, "section_chart"))

        numeric_columns = get_numeric_columns(data)

        if not numeric_columns:
            st.warning(tr(language, "numeric_required"))
        else:
            category_columns = data.select_dtypes(
                exclude="number"
            ).columns.tolist()

            chart_type = st.selectbox(
                tr(language, "chart_type"),
                options=(
                    "Bar chart",
                    "Line chart",
                    "Scatter plot",
                    "Histogram",
                    "Box plot",
                ),
                format_func=lambda value: get_catalog(language)["chart_types"][value],
                key="chart_type",
            )

            if chart_type == "Histogram":
                x_column = st.selectbox(
                    tr(language, "numeric_values"),
                    options=numeric_columns,
                    key="numeric_values_column",
                )
                y_column = None
                axis_key = "x"
                axis_name = "X-axis"
                axis_label = tr(language, "axis_x")
                title = tr(language, "chart_distribution", column=x_column)
                chart_rows = data[[x_column]].copy()
                chart_rows[x_column] = pd.to_numeric(
                    chart_rows[x_column], errors="coerce"
                )
                finite_mask = chart_rows[x_column].map(
                    lambda value: pd.notna(value) and math.isfinite(float(value))
                )
                valid_mask = finite_mask
                values_column = x_column
            elif chart_type == "Box plot":
                y_column = st.selectbox(
                    tr(language, "numeric_values"),
                    options=numeric_columns,
                    key="numeric_values_column",
                )
                x_options = category_columns + [
                    column for column in numeric_columns if column != y_column
                ]
                x_column = st.selectbox(
                    tr(language, "group_by"),
                    options=[None] + x_options,
                    format_func=lambda column: (
                        tr(language, "all_observations") if column is None else column
                    ),
                    key="group_by_column",
                )
                st.caption(tr(language, "box_group_note"))
                axis_key = "y"
                axis_name = "Y-axis"
                axis_label = tr(language, "axis_y")
                title = (
                    tr(language, "chart_distribution", column=y_column)
                    if x_column is None
                    else tr(language, "chart_by", measure=y_column, category=x_column)
                )
                selected_columns = [y_column] if x_column is None else [x_column, y_column]
                chart_rows = data[selected_columns].copy()
                chart_rows[y_column] = pd.to_numeric(
                    chart_rows[y_column], errors="coerce"
                )
                finite_mask = chart_rows[y_column].map(
                    lambda value: pd.notna(value) and math.isfinite(float(value))
                )
                valid_mask = (
                    finite_mask
                    if x_column is None
                    else chart_rows[x_column].notna() & finite_mask
                )
                values_column = y_column
            else:
                y_column = st.selectbox(
                    tr(language, "axis_y"),
                    options=numeric_columns,
                    key="y_axis_column",
                )

                x_options = category_columns + [
                    column for column in numeric_columns if column != y_column
                ]
                if not x_options:
                    st.warning(tr(language, "two_columns"))
                    st.stop()

                x_column = st.selectbox(
                    tr(language, "axis_x"),
                    options=x_options,
                    key="x_axis_column",
                )
                axis_key = "y"
                axis_name = "Y-axis"
                axis_label = tr(language, "axis_y")
                title = tr(language, "chart_by", measure=y_column, category=x_column)
                chart_rows = data[[x_column, y_column]].copy()
                chart_rows[y_column] = pd.to_numeric(
                    chart_rows[y_column], errors="coerce"
                )
                finite_mask = chart_rows[y_column].map(
                    lambda value: pd.notna(value) and math.isfinite(float(value))
                )
                valid_mask = chart_rows[x_column].notna() & finite_mask
                values_column = y_column

            default_x_label = (
                ""
                if chart_type == "Box plot" and x_column is None
                else x_column
            )
            default_y_label = tr(language, "count") if chart_type == "Histogram" else y_column
            sync_default_text_input("chart_title_input", title)
            sync_default_text_input("x_label_input", default_x_label)
            sync_default_text_input("y_label_input", default_y_label)
            with st.expander(tr(language, "chart_options")):
                title = st.text_input(
                    tr(language, "chart_title"), key="chart_title_input"
                )
                label_col1, label_col2 = st.columns(2)
                with label_col1:
                    x_label = st.text_input(
                        tr(language, "x_label"), key="x_label_input"
                    )
                with label_col2:
                    y_label = st.text_input(
                        tr(language, "y_label"), key="y_label_input"
                    )

            missing_chart_rows = int((~valid_mask).sum())
            chart_rows = chart_rows.loc[valid_mask].copy()

            if chart_rows.empty:
                st.warning(tr(language, "no_usable_rows"))
            else:
                axis_values = chart_rows[values_column]
                data_min = float(axis_values.min())
                data_max = float(axis_values.max())
                if chart_type == "Histogram":
                    excluded_rows_message = tr(language, "exclude_histogram")
                elif chart_type == "Box plot" and x_column is None:
                    excluded_rows_message = tr(language, "exclude_box_all")
                else:
                    excluded_rows_message = tr(language, "exclude_xy")
                st.caption(tr(
                    language, "charting_rows", used=len(chart_rows), total=len(data)
                ) + " " + excluded_rows_message)

                st.subheader(tr(language, "original_settings"))
                custom_range = st.checkbox(
                    tr(language, "custom_range", axis=axis_label),
                    value=False,
                    key="custom_axis_range",
                )
                original_range = None
                if custom_range:
                    input_step = max(max(abs(data_min), abs(data_max)) * 0.01, 0.1)
                    bound_col1, bound_col2 = st.columns(2)
                    with bound_col1:
                        y_lower = st.number_input(
                            tr(language, "minimum", axis=axis_label),
                            value=data_min,
                            step=input_step,
                            key=f"original_{axis_key}_min",
                        )
                    with bound_col2:
                        y_upper = st.number_input(
                            tr(language, "maximum", axis=axis_label),
                            value=data_max,
                            step=input_step,
                            key=f"original_{axis_key}_max",
                        )
                    if y_lower >= y_upper:
                        st.error(tr(language, "range_error"))
                    else:
                        original_range = [float(y_lower), float(y_upper)]

                original_fig = make_chart(
                    chart_rows, x_column, y_column, chart_type, title,
                    x_label=x_label, y_label=y_label,
                )
                if original_range is not None:
                    if chart_type == "Histogram":
                        original_fig.update_xaxes(range=original_range)
                    else:
                        original_fig.update_yaxes(range=original_range)

                sorted_rows = chart_rows.copy()
                unsorted_line = False
                sort_kind = None
                if chart_type == "Line chart":
                    sort_values, sort_kind = line_sort_values(
                        sorted_rows[x_column]
                    )
                    if sort_values is not None:
                        unsorted_line = not sort_values.is_monotonic_increasing
                        sorted_rows = (
                            sorted_rows.assign(_uncharted_sort=sort_values)
                            .sort_values("_uncharted_sort", kind="stable")
                            .drop(columns="_uncharted_sort")
                        )

                corrected_fig = make_chart(
                    sorted_rows, x_column, y_column, chart_type,
                    f"{title}{tr(language, 'recommended_suffix')}",
                    x_label=x_label, y_label=y_label,
                )
                corrected_range = corrected_y_range(axis_values, chart_type)
                if chart_type == "Histogram":
                    corrected_fig.update_xaxes(range=corrected_range)
                else:
                    corrected_fig.update_yaxes(range=corrected_range)

                raw_findings = audit_chart(
                    chart_type,
                    axis_values,
                    original_range,
                    missing_chart_rows,
                    unsorted_line,
                    line_order_applicable=sort_kind is not None,
                    x_values=chart_rows[x_column] if x_column is not None else None,
                )
                findings_context = {
                    "chart_type": chart_type,
                    "axis_name": axis_name,
                    "values": axis_values,
                    "original_range": original_range,
                    "missing_rows": missing_chart_rows,
                    "line_sort_kind": sort_kind,
                    "unsorted_line": unsorted_line,
                    "x_values": chart_rows[x_column] if x_column is not None else None,
                }
                findings = localize_findings(
                    raw_findings, language, **findings_context
                )

                st.divider()
                st.header(tr(language, "section_audit"))
                status_icons = {
                    "detected": "⚠️",
                    "clear": "✅",
                    "not_applicable": "➖",
                }
                for finding in findings:
                    status = finding["status"]
                    with st.expander(
                        f"{status_icons[status]} {finding['title']} — "
                        f"{finding['status_label']}",
                        expanded=status == "detected",
                    ):
                        st.write(finding["explanation"])
                        st.write(f"**{tr(language, 'evidence')}:** {finding['evidence']}")
                        st.write(f"**{tr(language, 'why_matters')}:** {finding['impact']}")
                        st.write(f"**{tr(language, 'recommendation')}:** {finding['recommendation']}")
                        st.caption(f"{tr(language, 'limitations')}: {finding['limitations']}")

                if sort_kind:
                    st.caption(
                        tr(language, "sorted_line", kind=tr(
                            language,
                            "sort_numeric" if sort_kind == "numeric" else "sort_date",
                        ))
                    )

                st.header(tr(language, "section_compare"))
                original_col, corrected_col = st.columns(2)
                with original_col:
                    st.subheader(tr(language, "original"))
                    st.plotly_chart(
                        original_fig,
                        width="stretch",
                        key="original_chart",
                    )
                    if original_range is None:
                        st.caption(tr(language, "axis_auto", axis=axis_label))
                    else:
                        st.caption(
                            tr(language, "axis_range", axis=axis_label,
                               minimum=f"{original_range[0]:g}",
                               maximum=f"{original_range[1]:g}")
                        )
                with corrected_col:
                    st.subheader(tr(language, "recommended"))
                    st.plotly_chart(
                        corrected_fig,
                        width="stretch",
                        key="corrected_chart",
                    )
                    if chart_type == "Bar chart":
                        st.caption(tr(language, "scale_bar"))
                    elif chart_type == "Histogram":
                        st.caption(tr(language, "scale_histogram"))
                    else:
                        st.caption(tr(language, "scale_other"))

                st.divider()
                st.header(tr(language, "section_export"))
                report_col, json_col = st.columns(2)
                with report_col:
                    st.download_button(
                        tr(language, "download_csv"),
                        data=audit_csv_bytes(
                            raw_findings, language, **findings_context
                        ),
                        file_name="uncharted_audit_report.csv",
                        mime="text/csv; charset=utf-8",
                        key="download_audit_csv",
                        width="stretch",
                    )
                with json_col:
                    st.download_button(
                        tr(language, "download_json"),
                        data=audit_json_bytes(
                            raw_findings, language, **findings_context
                        ),
                        file_name="uncharted_audit_report.json",
                        mime="application/json",
                        key="download_audit_json",
                        width="stretch",
                    )

                original_export_col, corrected_export_col = st.columns(2)
                with original_export_col:
                    try:
                        original_html = figure_html_bytes(original_fig)
                    except Exception as error:
                        st.warning(tr(language, "export_original_error", error=error))
                    else:
                        st.download_button(
                            tr(language, "download_original"),
                            data=original_html,
                            file_name=figure_filename(title, "original"),
                            mime="text/html",
                            key="download_original_chart",
                            width="stretch",
                        )
                with corrected_export_col:
                    try:
                        corrected_html = figure_html_bytes(corrected_fig)
                    except Exception as error:
                        st.warning(tr(language, "export_recommended_error", error=error))
                    else:
                        st.download_button(
                            tr(language, "download_recommended"),
                            data=corrected_html,
                            file_name=figure_filename(title, "recommended"),
                            mime="text/html",
                            key="download_recommended_chart",
                            width="stretch",
                        )

    except CSVLoadError as error:
        st.error(tr(language, error.code))
    except Exception as error:
        st.error(tr(language, "process_error", error=error))

else:
    st.info(tr(language, "upload_prompt"))
