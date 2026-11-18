"""Graphique de fiabilité observée et prévue pour Q1."""

import plotly.graph_objects as go

from railinsight.analysis.prevision_fiabilite import (
    MODELES,
    PrevisionFiabilite,
)


def figure_prevision_fiabilite(resultat: PrevisionFiabilite) -> go.Figure:
    """Sépare les observations des trois prévisions mensuelles bornées."""
    historique = resultat.historique.tail(24)
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=historique["mois"],
            y=historique["fiabilite"] * 100,
            name="Fiabilité observée",
            mode="lines+markers",
            line={"color": "#003F88"},
        )
    )
    for colonne, nom, couleur in [
        ("fiabilite", "Prévision retenue", "#E8003D"),
        ("reference", MODELES["saisonnier"], "#9BA3AE"),
    ]:
        figure.add_trace(
            go.Scatter(
                x=resultat.previsions["mois"],
                y=resultat.previsions[colonne] * 100,
                name=nom,
                mode="lines+markers",
                line={"color": couleur, "dash": "dash"},
            )
        )
    figure.update_traces(
        hovertemplate=(
            "%{x|%Y-%m}<br>Fiabilité : %{y:.1f} %<extra>%{fullData.name}</extra>"
        )
    )
    figure.update_layout(
        height=440,
        margin={"l": 0, "r": 10, "t": 25, "b": 0},
        legend={"orientation": "h", "y": -0.2},
        xaxis={"title": "", "tickformat": "%Y-%m"},
        yaxis={"title": "Fiabilité mensuelle (%)", "range": [0, 100]},
    )
    return figure
