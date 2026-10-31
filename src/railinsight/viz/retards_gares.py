import pandas as pd
import plotly.graph_objects as go

from railinsight.utils.formatting import fmt_number

"""Figures de la Q2 : gares de départ à l'origine ou victimes des retards.

Chaque fonction reçoit un tableau et renvoie une figure Plotly, sans appel Streamlit.
"""

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


def figure_classement_gares(
    classement: pd.DataFrame, colonne: str, couleur: str
) -> go.Figure:
    """Affiche un classement de gares en barres horizontales.

    Args:
        classement: Gares déjà classées, de la plus grande valeur à la plus petite.
            Colonnes attendues : `gare_depart` et `colonne`.
        colonne: Colonne de volume à afficher.
        couleur: Couleur des barres.

    Returns:
        Une figure avec la première gare en haut.
    """
    # Plotly empile les barres du bas vers le haut : on inverse l'ordre.
    choix = classement.iloc[::-1]
    valeurs = choix[colonne]
    maximum = float(valeurs.max()) if not choix.empty else 0.0
    figure = go.Figure(
        go.Bar(
            x=valeurs,
            y=choix["gare_depart"],
            orientation="h",
            marker_color=couleur,
            text=[fmt_number(valeur) for valeur in valeurs],
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
            "title": "Retards estimés à l'arrivée (nombre de trains)",
            # Marge à droite pour que le chiffre ne soit pas coupé.
            "range": [0, (maximum or 1) * 1.15],
        },
        yaxis={"title": ""},
    )
    return figure
