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


def figure_comparaison_liaisons(
    mensuel: pd.DataFrame,
    liaisons: list[str],
    covid_debut: str,
    covid_fin: str,
    pas_de_temps: str = "Mensuel",
) -> go.Figure:
    """Compare les taux de plusieurs liaisons à l'échelle mensuelle ou annuelle."""
    selection = mensuel.loc[mensuel["liaison"].isin(liaisons)].copy()
    if pas_de_temps == "Annuel":
        selection["annee"] = selection["mois"].dt.year
        selection = (
            selection.groupby(["liaison", "annee"], as_index=False)
            .agg(prevus=("prevus", "sum"), incidents=("incidents", "sum"))
            .assign(taux_incidents=lambda table: table["incidents"] / table["prevus"])
        )
        selection["date_affichage"] = pd.to_datetime(
            selection["annee"].astype(str) + "-01-01"
        )
        format_date = "%Y"
    else:
        selection["date_affichage"] = selection["mois"]
        format_date = "%b %Y"

    couleurs = ["#003F88", "#E8003D", "#2E7D32", "#FF6B35", "#6A0572"]
    figure = go.Figure()
    for index, liaison in enumerate(liaisons):
        serie = selection.loc[selection["liaison"] == liaison].sort_values(
            "date_affichage"
        )
        figure.add_trace(
            go.Scatter(
                x=serie["date_affichage"],
                y=serie["taux_incidents"] * 100,
                mode="lines+markers",
                name=liaison,
                line={"color": couleurs[index % len(couleurs)]},
                hovertemplate=(
                    f"{liaison}<br>%{{x|{format_date}}}"
                    "<br>Taux : %{y:.1f} %<extra></extra>"
                ),
            )
        )
    if pas_de_temps != "Annuel":
        figure.add_vrect(
            x0=pd.Period(covid_debut, freq="M").start_time,
            x1=pd.Period(covid_fin, freq="M").end_time,
            fillcolor="#9BA3AE",
            opacity=0.2,
            line_width=0,
            annotation_text="Fenêtre COVID",
            annotation_position="top left",
        )
    figure.update_layout(
        height=460,
        margin={"l": 0, "r": 10, "t": 35, "b": 0},
        legend={"orientation": "h", "y": -0.2},
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
