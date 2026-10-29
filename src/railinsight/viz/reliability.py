"""Graphiques Plotly pour le tableau de bord de fiabilité (Q1)."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def plot_worst_routes_bar(ranking: pd.DataFrame) -> go.Figure:
    """Diagramme en barres horizontales du taux d'incidents par liaison.

    Args:
        ranking: DataFrame indexé par ``route`` avec une colonne ``rate``
            (sortie de ``analysis.reliability.rank_routes``).

    Returns:
        Une figure Plotly, liaisons triées de la plus fiable à la moins
        fiable du haut vers le bas.
    """
    data = ranking.sort_values("rate").reset_index()
    data["rate_pct"] = data["rate"] * 100
    fig = px.bar(
        data,
        x="rate_pct",
        y="route",
        orientation="h",
        labels={"rate_pct": "Taux d'incidents (%)", "route": ""},
        title="Liaisons les moins fiables du réseau",
        color="rate_pct",
        color_continuous_scale="Reds",
    )
    fig.update_layout(coloraxis_showscale=False)
    return fig


def plot_route_evolution(
    monthly: pd.DataFrame,
    routes: list[str],
    covid_start: pd.Period,
    covid_end: pd.Period,
) -> go.Figure:
    """Évolution mensuelle du taux d'incidents pour un ensemble de liaisons.

    Args:
        monthly: Taux d'incidents par (``route``, ``month``), sortie de
            ``analysis.reliability.compute_monthly_rates``.
        routes: Liaisons à tracer.
        covid_start: Premier mois de la période COVID, mise en évidence par
            une zone grisée.
        covid_end: Dernier mois de la période COVID.

    Returns:
        Une figure Plotly avec une ligne par liaison et la période COVID
        grisée.
    """
    data = monthly[monthly["route"].isin(routes)].copy()
    data["month_ts"] = data["month"].dt.to_timestamp()
    data["rate_pct"] = data["rate"] * 100

    fig = px.line(
        data,
        x="month_ts",
        y="rate_pct",
        color="route",
        markers=True,
        labels={
            "month_ts": "",
            "rate_pct": "Taux d'incidents (%)",
            "route": "Liaison",
        },
        title="Évolution du taux d'incidents dans le temps",
    )
    fig.add_vrect(
        x0=covid_start.to_timestamp(),
        x1=covid_end.to_timestamp(),
        fillcolor="grey",
        opacity=0.15,
        line_width=0,
        annotation_text="Période COVID (exclue de la tendance)",
        annotation_position="top left",
    )
    return fig
