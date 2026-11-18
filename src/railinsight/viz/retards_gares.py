"""Figures de la Q2 : gares de départ à l'origine ou victimes des retards.

Chaque fonction reçoit un tableau et renvoie une figure Plotly.
"""

import pandas as pd
import plotly.graph_objects as go

from railinsight.analysis.causes_retards import Evolution
from railinsight.utils.formatting import fmt_number, fmt_pct

# Orange : couleur de la Q2 ; bleu : retards importés ; gris : causes extérieures.
COULEURS_CATEGORIES = {
    "retard_heritees": "#003F88",
    "retard_non_heritees": "#FF6B35",
    "retard_externes": "#9BA3AE",
}

LIBELLES_CATEGORIES = {
    "retard_heritees": "Retards importés",
    "retard_non_heritees": "Retards nés sur place",
    "retard_externes": "Causes extérieures",
}

# Colonne de part correspondant à chaque colonne de volume.
PARTS_CATEGORIES = {
    "retard_heritees": "taux_heritees",
    "retard_non_heritees": "taux_non_heritees",
    "retard_externes": "taux_externes",
}

# Ordre des bandes de l'aire empilée : les retards importés en bas.
ORDRE_EMPILEMENT = ["retard_heritees", "retard_non_heritees", "retard_externes"]

SEUIL_ETIQUETTE = 0.08
COULEUR_REFERENCE = "#4A5568"
COULEUR_GRILLE = "#EEF0F2"


def _epurer(figure: go.Figure, grille_y: bool = False) -> go.Figure:
    """Retire ce qui ne porte pas d'information : fond gris, quadrillage, axe zéro.

    Args:
        figure: Figure à épurer, modifiée sur place.
        grille_y: Si True, garde une grille horizontale très légère, utile pour
            lire les valeurs d'une courbe.

    Returns:
        La même figure.
    """
    figure.update_layout(plot_bgcolor="white")
    figure.update_xaxes(showgrid=False, zeroline=False)
    figure.update_yaxes(showgrid=grille_y, gridcolor=COULEUR_GRILLE, zeroline=False)
    return figure


def figure_classement_gares(
    classement: pd.DataFrame,
    colonne: str,
    couleur: str,
    en_part: bool = False,
    reference: float | None = None,
) -> go.Figure:
    """Affiche un classement de gares en barres horizontales, valeurs écrites.

    Args:
        classement: Gares déjà classées, de la plus grande valeur à la plus petite.
            Colonnes attendues : `gare_depart` et `colonne`.
        colonne: Colonne à afficher.
        couleur: Couleur des barres.
        en_part: Si True, `colonne` est une part (entre 0 et 1) affichée en
            pourcentage ; sinon c'est un nombre de trains.
        reference: Valeur de comparaison, par exemple la moyenne de toutes les
            gares, tracée en ligne verticale pointillée.

    Returns:
        Une figure avec la première gare en haut.
    """
    # Plotly empile les barres du bas vers le haut : on inverse l'ordre.
    choix = classement.iloc[::-1]
    valeurs = choix[colonne]
    maximum = float(valeurs.max()) if not choix.empty else 0.0
    maximum = max(maximum, reference or 0.0)
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
    if reference is not None:
        figure.add_vline(
            x=reference,
            line_dash="dot",
            line_color=COULEUR_REFERENCE,
            annotation_text=f"Moyenne : {formater(reference)}",
            annotation_position="top right",
        )
    figure.update_layout(
        height=35 * len(choix) + 90,
        showlegend=False,
        margin={"l": 0, "r": 40, "t": 30, "b": 0},
        xaxis={
            # Les valeurs sont écrites sur les barres : l'axe n'apporte rien.
            "title": "",
            "showticklabels": False,
            "tickformat": ".0%" if en_part else None,
            # Marge à droite pour que le chiffre ne soit pas coupé.
            "range": [0, (maximum or 1) * 1.15],
        },
        yaxis={"title": ""},
    )
    return _epurer(figure)


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
    return _epurer(figure)


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
    return _epurer(figure, grille_y=True)


def figure_aire_parts(
    reseau: pd.DataFrame, evolution: Evolution | None = None
) -> go.Figure:
    """Empile, année par année, la part de chaque famille de causes.

    Args:
        reseau: Résultat de `parts_reseau` au niveau `annee`.
        evolution: Si fournie, la part des retards importés est écrite à ses
            deux années, au milieu de la bande du bas.

    Returns:
        Une aire empilée dont chaque année totalise 100 %.
    """
    reseau = reseau.sort_values("annee")
    figure = go.Figure()
    for volume in ORDRE_EMPILEMENT:
        libelle = LIBELLES_CATEGORIES[volume]
        figure.add_trace(
            go.Scatter(
                x=reseau["annee"],
                y=reseau[PARTS_CATEGORIES[volume]],
                name=libelle,
                mode="lines",
                stackgroup="parts",
                line={"width": 0.5, "color": COULEURS_CATEGORIES[volume]},
                fillcolor=COULEURS_CATEGORIES[volume],
                hovertemplate=f"{libelle} : %{{y:.1%}}<extra></extra>",
            )
        )
    if evolution is not None:
        for annee, valeur, ancrage in (
            (evolution.annee_debut, evolution.valeur_debut, "left"),
            (evolution.annee_fin, evolution.valeur_fin, "right"),
        ):
            figure.add_annotation(
                x=annee,
                y=valeur / 2,
                text=fmt_pct(valeur, 0),
                xanchor=ancrage,
                showarrow=False,
                font={"color": "white", "size": 14},
            )
    figure.update_layout(
        height=340,
        margin={"l": 0, "r": 0, "t": 30, "b": 0},
        legend={"orientation": "h", "y": 1.12},
        hovermode="x unified",
        xaxis={"title": "", "dtick": 1, "tickformat": "d"},
        yaxis={"title": "", "tickformat": ".0%", "range": [0, 1]},
    )
    return _epurer(figure, grille_y=True)