"""Figures de la Q2 : gares de départ à l'origine ou victimes des retards.

Chaque fonction reçoit un tableau et renvoie une figure Plotly, sans appel Streamlit.
"""

import pandas as pd
import plotly.graph_objects as go

from railinsight.utils.formatting import fmt_number, fmt_pct

# Orange : couleur de la Q2 ; bleu : retards hérités ; gris : causes externes.
COULEURS_CATEGORIES = {
    "retard_heritees": "#003F88",
    "retard_non_heritees": "#FF6B35",
    "retard_externes": "#9BA3AE",
}

LIBELLES_CATEGORIES = {
    "retard_heritees": "Retards hérités",
    "retard_non_heritees": "Retards propres à la gare",
    "retard_externes": "Retards externes",
}

# Colonne de part correspondant à chaque colonne de volume.
PARTS_CATEGORIES = {
    "retard_heritees": "taux_heritees",
    "retard_non_heritees": "taux_non_heritees",
    "retard_externes": "taux_externes",
}

SEUIL_ETIQUETTE = 0.08


def figure_classement_gares(
    classement: pd.DataFrame,
    colonne: str,
    couleur: str,
    en_part: bool = False,
) -> go.Figure:
    """Affiche un classement de gares en barres horizontales.

    Args:
        classement: Gares déjà classées, de la plus grande valeur à la plus petite.
            Colonnes attendues : `gare_depart` et `colonne`.
        colonne: Colonne à afficher.
        couleur: Couleur des barres.
        en_part: Si True, `colonne` est une part (entre 0 et 1) affichée en
            pourcentage ; sinon c'est un nombre de trains.

    Returns:
        Une figure avec la première gare en haut.
    """
    # Plotly empile les barres du bas vers le haut : on inverse l'ordre.
    choix = classement.iloc[::-1]
    valeurs = choix[colonne]
    maximum = float(valeurs.max()) if not choix.empty else 0.0
    formater = fmt_pct if en_part else fmt_number
    figure = go.Figure(
        go.Bar(
            x=valeurs,
            y=choix["gare_depart"],
            orientation="h",
            marker_color=couleur,
            text=[formater(valeur) for valeur in valeurs],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}<br>%{text}<extra></extra>",
        )
    )
    figure.update_layout(
        height=35 * len(choix) + 120,
        showlegend=False,
        margin={"l": 0, "r": 40, "t": 10, "b": 0},
        xaxis={
            "title": (
                "Part dans les retards de la gare"
                if en_part
                else "Retards estimés à l'arrivée (nombre de trains)"
            ),
            "tickformat": ".0%" if en_part else None,
            # Marge à droite pour que le chiffre ne soit pas coupé.
            "range": [0, (maximum or 1) * 1.15],
        },
        yaxis={"title": ""},
    )
    return figure


def figure_repartition_causes(parts: pd.DataFrame) -> go.Figure:
    """Affiche, pour chaque gare, la répartition de ses retards par catégorie.

    Args:
        parts: Gares dans l'ordre d'affichage (première gare en haut).
            Colonnes attendues : `gare_depart` et les colonnes de
            PARTS_CATEGORIES.

    Returns:
        Une figure en barres empilées, chaque barre totalisant 100 %.
    """
    choix = parts.iloc[::-1]
    figure = go.Figure()
    for volume, colonne in PARTS_CATEGORIES.items():
        libelle = LIBELLES_CATEGORIES[volume]
        valeurs = choix[colonne].fillna(0)
        figure.add_trace(
            go.Bar(
                x=valeurs,
                y=choix["gare_depart"],
                orientation="h",
                name=libelle,
                marker_color=COULEURS_CATEGORIES[volume],
                text=[fmt_pct(v) if v >= SEUIL_ETIQUETTE else "" for v in valeurs],
                textposition="inside",
                textfont={"color": "white"},
                hovertemplate=f"%{{y}}<br>{libelle} : %{{x:.1%}}<extra></extra>",
            )
        )
    figure.update_layout(
        barmode="stack",
        height=35 * len(choix) + 160,
        margin={"l": 0, "r": 0, "t": 40, "b": 0},
        legend={"orientation": "h", "y": 1.02},
        xaxis={"title": "Part des retards de la gare", "tickformat": ".0%"},
        yaxis={"title": ""},
    )
    return figure


def figure_evolution_gare(table: pd.DataFrame, axe_temps: str = "date") -> go.Figure:
    """Affiche l'évolution des retards d'une gare, une courbe par catégorie.

    Args:
        table: Lignes d'une seule gare, issues du niveau `by_year` ou `by_month`.
            Colonnes attendues : `axe_temps` et les colonnes de volume de
            LIBELLES_CATEGORIES.
        axe_temps: `annee` ou `date`.

    Returns:
        Une figure avec une courbe par catégorie, triée dans le temps.
    """
    table = table.sort_values(axe_temps)
    figure = go.Figure()
    for colonne, libelle in LIBELLES_CATEGORIES.items():
        figure.add_trace(
            go.Scatter(
                x=table[axe_temps],
                y=table[colonne],
                mode="lines+markers",
                name=libelle,
                line={"color": COULEURS_CATEGORIES[colonne]},
                hovertemplate=f"{libelle}<br>%{{y:.0f}} trains<extra></extra>",
            )
        )
    figure.update_layout(
        height=420,
        margin={"l": 0, "r": 0, "t": 40, "b": 0},
        legend={"orientation": "h", "y": 1.1},
        xaxis={"title": ""},
        yaxis={"title": "Retards estimés à l'arrivée (nombre de trains)"},
    )
    if axe_temps == "annee":
        # Une graduation par année, sans décimale (2019, pas 2019,5).
        figure.update_xaxes(dtick=1, tickformat="d")
    return figure
