"""Figures pour l'analyse de fiabilité des liaisons (Q1)."""

import pandas as pd
import plotly.graph_objects as go


def figure_classement_liaisons(classement: pd.DataFrame) -> go.Figure:
    """Affiche les liaisons les moins fiables par taux d'incidents."""
    choix = classement.iloc[::-1]
    taux = choix["taux_incidents"] * 100
    figure = go.Figure(
        go.Bar(
            x=taux,
            y=choix.index,
            orientation="h",
            marker_color="#003F88",
            text=[f"{valeur:.1f} %" for valeur in taux],
            textposition="outside",
            cliponaxis=False,
            customdata=choix[["prevus", "incidents"]].to_numpy(),
            hovertemplate=(
                "%{y}<br>Taux d'incidents : %{x:.1f} %"
                "<br>Trains prévus : %{customdata[0]:,.0f}"
                "<br>Incidents : %{customdata[1]:,.0f}<extra></extra>"
            ),
        )
    )
    maximum = float(taux.max()) if not taux.empty else 0.0
    figure.update_layout(
        height=38 * len(choix) + 110,
        showlegend=False,
        margin={"l": 0, "r": 55, "t": 10, "b": 0},
        xaxis={
            "title": "Trains annulés ou en retard de plus de 15 min (%)",
            "range": [0, (maximum or 1) * 1.18],
        },
        yaxis={"title": ""},
    )
    return figure


def figure_evolution_liaison(
    mensuel: pd.DataFrame,
    liaison: str,
    covid_debut: str,
    covid_fin: str,
) -> go.Figure:
    """Trace le taux mensuel d'une liaison et repère la fenêtre COVID."""
    serie = mensuel.loc[mensuel["liaison"] == liaison].sort_values("mois")
    figure = go.Figure(
        go.Scatter(
            x=serie["mois"],
            y=serie["taux_incidents"] * 100,
            mode="lines+markers",
            name=liaison,
            line={"color": "#003F88"},
            hovertemplate="%{x|%b %Y}<br>Taux : %{y:.1f} %<extra></extra>",
        )
    )
    figure.add_vrect(
        x0=pd.Period(covid_debut, freq="M").start_time,
        x1=pd.Period(covid_fin, freq="M").end_time,
        fillcolor="#9BA3AE",
        opacity=0.2,
        line_width=0,
        annotation_text="Fenêtre COVID exclue de cette tendance",
        annotation_position="top left",
    )
    figure.update_layout(
        height=440,
        margin={"l": 0, "r": 10, "t": 35, "b": 0},
        xaxis={"title": ""},
        yaxis={"title": "Trains annulés ou en retard de plus de 15 min (%)"},
    )
    return figure


def figure_classement_duree(classement: pd.DataFrame) -> go.Figure:
    """Compare le taux d'incidents corrigé de la durée des liaisons."""
    choix = classement.dropna(subset=["taux_ajuste"]).copy()
    choix = choix.sort_values("taux_ajuste", ascending=False).head(15).iloc[::-1]
    figure = go.Figure(
        go.Bar(
            x=choix["taux_ajuste"] * 100,
            y=choix.index,
            orientation="h",
            marker_color="#1F5FA8",
            customdata=choix["taux_incidents"] * 100,
            hovertemplate=(
                "%{y}<br>Taux ajusté : %{x:.1f} %"
                "<br>Taux brut : %{customdata:.1f} %<extra></extra>"
            ),
        )
    )
    figure.update_layout(
        height=38 * len(choix) + 110,
        margin={"l": 0, "r": 20, "t": 10, "b": 0},
        xaxis={"title": "Taux d'incidents ajusté à la durée moyenne (%)"},
        yaxis={"title": ""},
    )
    return figure
