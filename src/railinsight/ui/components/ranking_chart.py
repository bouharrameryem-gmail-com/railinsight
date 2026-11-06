"""Horizontal ranking bar chart — reusable for Q1 (Michelle) and Q2 (Éric).

Usage:
    ranking_chart(df, label_col="gare", metric_col="retard_moyen",
                  title="Gares les plus en retard", top_n=15)
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from railinsight.ui.components.chart_container import chart_container
from railinsight.ui.theme.tokens import SNCF_RED


def ranking_chart(
    df: pd.DataFrame,
    label_col: str,
    metric_col: str,
    title: str,
    top_n: int = 15,
    ascending: bool = False,
    color: str = SNCF_RED,
    format_as_pct: bool = False,
    how_to_read: str = "",
    show_top_n_slider: bool = False,
    key: str | None = None,
) -> None:
    """Render a horizontal bar chart ranking labels by a numeric metric.

    Args:
        df: DataFrame with at least label_col and metric_col.
        label_col: Column of categorical labels (station names, route names…).
        metric_col: Numeric column to rank by.
        title: Chart title shown above the figure.
        top_n: Number of rows to display (default 15).
        ascending: If True, show lowest values first (best performers).
        color: Bar fill color.
        format_as_pct: If True, format x-axis ticks and bar labels as %.
        how_to_read: Optional reading guide shown in an expander.
        show_top_n_slider: If True, render a slider to adjust top_n interactively.
        key: Streamlit widget key for the slider (required if show_top_n_slider).
    """
    data = (
        df[[label_col, metric_col]]
        .dropna()
        .sort_values(metric_col, ascending=ascending)
    )

    if show_top_n_slider and key:
        actual_n = st.slider(
            "Nombre à afficher",
            min_value=5,
            max_value=min(50, len(data)),
            value=min(top_n, len(data)),
            key=key,
        )
    else:
        actual_n = min(top_n, len(data))

    # Take last N rows when ascending=False (highest values are at the bottom
    # after ascending sort), then reverse so highest is at the top of the chart.
    if ascending:
        display = data.head(actual_n)
    else:
        display = data.tail(actual_n).iloc[::-1]

    text_vals = (
        [f"{v:.1%}" for v in display[metric_col]]
        if format_as_pct
        else [f"{v:.3f}" for v in display[metric_col]]
    )

    fig = go.Figure(
        go.Bar(
            x=display[metric_col],
            y=display[label_col],
            orientation="h",
            marker_color=color,
            text=text_vals,
            textposition="outside",
            cliponaxis=False,
        )
    )
    fig.update_layout(
        margin={"l": 200, "r": 80, "t": 10, "b": 40},
        height=max(300, actual_n * 30),
        xaxis={
            "tickformat": ".1%" if format_as_pct else None,
            "title": metric_col.replace("_", " "),
        },
        yaxis={"title": ""},
        showlegend=False,
    )
    chart_container(fig, title=title, how_to_read=how_to_read)
