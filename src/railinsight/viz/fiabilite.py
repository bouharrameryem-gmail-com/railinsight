"""Figures du score de fiabilité : schéma du réseau, classement, nuage et évolution.

Chaque fonction reçoit un tableau et renvoie une figure Plotly, sans appel Streamlit.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from railinsight.analysis.score_fiabilite import NOMS_CATEGORIES
from railinsight.utils.formatting import fmt_number, fmt_pct

# Bleu : fiable ; rouge : à risque.
COULEURS_CATEGORIES = {
    "Très fiable": "#1f5fa8",
    "Fiable": "#74b3d9",
    "Moyenne": "#f2d04b",
    "Peu fiable": "#f08a24",
    "À risque": "#b2182b",
}

_LIAISONS_MIN_POUR_NOMMER_GARE = 5


def formater_minutes(valeur: float) -> str:
    """Formate une durée en minutes avec une virgule : 4,2 min."""
    return f"{valeur:.1f}".replace(".", ",") + " min"


def _texte_survol(ligne) -> str:
    """Résume les indicateurs d'une liaison au survol."""
    return (
        f"{ligne.liaison}<br>Note : {ligne.note:.0f} sur 100 ({ligne.categorie})"
        f"<br>Trains supprimés : {fmt_pct(ligne.taux_annulation)}"
        f"<br>Retard moyen : {formater_minutes(ligne.retard_moyen)}"
        f"<br>Trains prévus : {fmt_number(int(ligne.prevus))}"
    )


def figure_reseau(
    liaisons: pd.DataFrame,
    positions: dict[str, tuple[float, float]],
    gare: str | None = None,
) -> go.Figure:
    """Dessine les liaisons selon leur note, éventuellement autour d'une gare."""
    if gare is not None:
        liaisons = liaisons[(liaisons["gare_a"] == gare) | (liaisons["gare_b"] == gare)]

    figure = go.Figure()
    # Les liaisons fiables sont dessinées en dernier pour rester visibles.
    for categorie in reversed(NOMS_CATEGORIES):
        sous = liaisons[liaisons["categorie"] == categorie]
        if sous.empty:
            continue
        x, y = [], []
        for ligne in sous.itertuples():
            x_a, y_a = positions[ligne.gare_a]
            x_b, y_b = positions[ligne.gare_b]
            x += [x_a, x_b, None]
            y += [y_a, y_b, None]
        couleur = COULEURS_CATEGORIES[categorie]
        figure.add_trace(
            go.Scatter(
                x=x,
                y=y,
                mode="lines",
                line={"width": 2, "color": couleur},
                name=categorie,
                legendgroup=categorie,
                hoverinfo="skip",
            )
        )
        # Point au milieu de chaque trait : c'est lui qui affiche le détail au survol
        figure.add_trace(
            go.Scatter(
                x=[
                    (positions[a][0] + positions[b][0]) / 2
                    for a, b in zip(sous["gare_a"], sous["gare_b"], strict=True)
                ],
                y=[
                    (positions[a][1] + positions[b][1]) / 2
                    for a, b in zip(sous["gare_a"], sous["gare_b"], strict=True)
                ],
                mode="markers",
                marker={"size": 8, "color": couleur},
                text=[_texte_survol(ligne) for ligne in sous.itertuples()],
                hoverinfo="text",
                showlegend=False,
                legendgroup=categorie,
            )
        )

    gares = sorted(set(liaisons["gare_a"]) | set(liaisons["gare_b"]))
    nombre_liaisons = pd.concat([liaisons["gare_a"], liaisons["gare_b"]]).value_counts()
    noms = [
        (
            g
            if gare is not None or nombre_liaisons[g] >= _LIAISONS_MIN_POUR_NOMMER_GARE
            else ""
        )
        for g in gares
    ]
    figure.add_trace(
        go.Scatter(
            x=[positions[g][0] for g in gares],
            y=[positions[g][1] for g in gares],
            mode="markers+text",
            text=noms,
            textposition="top center",
            marker={"size": 7, "color": "#333333"},
            hovertext=[f"{g} : {nombre_liaisons[g]} liaison(s)" for g in gares],
            hoverinfo="text",
            name="Gares",
        )
    )
    figure.update_layout(
        height=650,
        margin={"l": 0, "r": 0, "t": 10, "b": 0},
        plot_bgcolor="white",
        xaxis={"visible": False},
        yaxis={"visible": False},
        legend={"orientation": "h", "y": -0.02},
    )
    return figure


def figure_classement(
    liaisons: pd.DataFrame, n: int, meilleures: bool = True
) -> go.Figure:
    """Affiche les `n` meilleures ou moins bonnes notes sous forme de barres."""
    choix = liaisons.head(n) if meilleures else liaisons.tail(n)
    figure = px.bar(
        choix.iloc[::-1],
        x="note",
        y="liaison",
        orientation="h",
        color="categorie",
        color_discrete_map=COULEURS_CATEGORIES,
        range_x=[0, 100],
        labels={
            "note": "Note sur 100",
            "liaison": "",
            "categorie": "Catégorie",
            "taux_annulation": "Trains annulés",
            "retard_moyen": "Retard moyen (min)",
        },
        hover_data={
            "taux_annulation": ":.1%",
            "retard_moyen": ":.1f",
            "categorie": False,
        },
    )
    figure.update_traces(texttemplate="%{x:.0f}")
    figure.update_layout(
        showlegend=False,
        height=35 * len(choix) + 120,
        yaxis={"categoryorder": "array", "categoryarray": choix.iloc[::-1]["liaison"]},
    )
    return figure


def figure_annulations_retards(liaisons: pd.DataFrame) -> go.Figure:
    """Compare les annulations et le retard moyen de chaque liaison."""
    figure = px.scatter(
        liaisons,
        x="taux_annulation",
        y="retard_moyen",
        color="categorie",
        color_discrete_map=COULEURS_CATEGORIES,
        category_orders={"categorie": NOMS_CATEGORIES},
        size="prevus",
        size_max=25,
        hover_name="liaison",
        hover_data={
            "note": ":.0f",
            "taux_annulation": ":.1%",
            "retard_moyen": ":.1f",
            "prevus": True,
            "categorie": False,
        },
        labels={
            "taux_annulation": "Trains supprimés (part des trains prévus)",
            "retard_moyen": "Retard moyen à l'arrivée (minutes)",
            "categorie": "Catégorie",
        },
    )
    figure.update_xaxes(tickformat=".0%")
    figure.update_layout(height=520)
    return figure


def figure_evolution(par_mois: pd.DataFrame) -> go.Figure:
    """Note mois par mois (résultat de `scores_par_mois`)."""
    figure = px.line(
        par_mois,
        x="mois",
        y="note",
        markers=True,
        labels={"mois": "Mois", "note": "Note sur 100"},
    )
    figure.update_yaxes(range=[0, 100])
    figure.update_layout(height=380)
    return figure
