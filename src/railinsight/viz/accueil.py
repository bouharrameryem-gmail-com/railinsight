"""Figures de la page d'accueil : carte des gares et calendrier des retards."""

import html
import re
from collections.abc import Sequence

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from railinsight.analysis.geometrie import Ligne
from railinsight.analysis.indicateurs_reseau import gares_les_plus_touchees
from railinsight.ui.theme.tokens import GRAY_700, GRAY_900, SNCF_RED
from railinsight.utils.formatting import fmt_number, fmt_pct

# Même code couleur partout : plus c'est rouge, plus les TGV sont en retard.
# Sur fond sombre, le gris discret s'efface et le rouge ressort.
ECHELLE_CARTE = [[0.0, GRAY_700], [0.5, "#B0003A"], [1.0, SNCF_RED]]
# Sur fond blanc, on part d'un rose très pâle vers un rouge SNCF assombri.
ECHELLE_CALENDRIER = [[0.0, "#FBE9ED"], [0.5, "#F07A97"], [1.0, "#A8002C"]]
COULEUR_RESEAU = "rgba(255, 255, 255, 0.28)"
COULEUR_TEXTE_CARTE = "#F5F7FA"

CENTRE_FRANCE = {"lat": 46.6, "lon": 2.5}
ZOOM_FRANCE = 4.45
HAUTEUR_CARTE = 540
TAILLE_MIN, TAILLE_MAX = 7, 34
NOMBRE_NOMS = 3

MOIS_COURTS = [
    "janv.",
    "févr.",
    "mars",
    "avr.",
    "mai",
    "juin",
    "juil.",
    "août",
    "sept.",
    "oct.",
    "nov.",
    "déc.",
]
MOIS_LONGS = [
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
]


def nom_gare(gare: str) -> str:
    """Écrit un nom de gare en casse de phrase : « AVIGNON TGV » → « Avignon TGV »."""
    return re.sub(r"\bTgv\b", "TGV", gare.title())


def _nom_lisible(gare: str) -> str:
    """Nom de gare prêt à insérer dans le HTML d'une infobulle."""
    return html.escape(nom_gare(gare), quote=False)


def _destinations(destinations: Sequence[tuple[str, float]]) -> str:
    """Résume en HTML les liaisons les plus touchées d'une gare."""
    if not destinations:
        return ""
    lignes = "<br>".join(
        f"  {_nom_lisible(arrivee)} : {fmt_pct(taux)}" for arrivee, taux in destinations
    )
    return f"<br><br>Liaisons les plus touchées :<br>{lignes}"


def _membres(membres: Sequence[tuple[str, float]]) -> str:
    """Détaille en HTML les gares regroupées dans une même bulle."""
    if not membres:
        return ""
    lignes = "<br>".join(
        f"  {_nom_lisible(gare)} : {fmt_pct(taux)}" for gare, taux in membres
    )
    return f"<br><br>Gares regroupées :<br>{lignes}"


def _tailles(trains: pd.Series) -> np.ndarray:
    """Taille des bulles, proportionnelle à la racine du nombre de trains.

    La racine rend la surface de la bulle, et non son diamètre, proportionnelle
    au trafic : c'est la surface que l'œil compare.
    """
    racines = np.sqrt(trains.to_numpy(dtype=float))
    maximum = racines.max() if len(racines) else 0.0
    if maximum <= 0:
        return np.full(len(racines), TAILLE_MIN, dtype=float)
    return TAILLE_MIN + (TAILLE_MAX - TAILLE_MIN) * racines / maximum


def _trace_reseau(reseau: Sequence[Ligne]) -> go.Scattermap:
    """Toutes les LGV en une seule trace, séparées par des valeurs vides."""
    longitudes: list[float | None] = []
    latitudes: list[float | None] = []
    for ligne in reseau:
        longitudes.extend([lon for lon, _ in ligne] + [None])
        latitudes.extend([lat for _, lat in ligne] + [None])
    return go.Scattermap(
        lon=longitudes,
        lat=latitudes,
        mode="lines",
        line={"color": COULEUR_RESEAU, "width": 1.4},
        hoverinfo="skip",
        name="Lignes à grande vitesse",
    )


def figure_carte_gares(
    gares: pd.DataFrame,
    reseau: Sequence[Ligne] | None = None,
    nombre_noms: int = NOMBRE_NOMS,
) -> go.Figure:
    """Carte des gares de départ, colorées selon leur taux de retard.

    Args:
        gares: Résultat de `placer_gares` ou de `regrouper_gares_proches` :
            `gare`, `latitude`, `longitude`, `trains`, `taux_retard`,
            `destinations` et, facultatif, `membres`.
        reseau: Tracé des LGV affiché en fond, ou None.
        nombre_noms: Nombre de gares les plus touchées nommées sur la carte.
    """
    figure = go.Figure()
    if reseau:
        figure.add_trace(_trace_reseau(reseau))

    survol = [
        f"<b>{_nom_lisible(ligne.gare)}</b><br>"
        f"{fmt_pct(ligne.taux_retard)} des TGV en retard de plus de 15 min<br>"
        f"{fmt_number(ligne.trains)} trains au départ"
        f"{_destinations(ligne.destinations)}"
        f"{_membres(getattr(ligne, 'membres', ()))}"
        for ligne in gares.itertuples()
    ]
    figure.add_trace(
        go.Scattermap(
            lon=gares["longitude"],
            lat=gares["latitude"],
            mode="markers",
            marker={
                "size": _tailles(gares["trains"]),
                "color": gares["taux_retard"],
                "colorscale": ECHELLE_CARTE,
                "opacity": 0.9,
                "colorbar": {
                    "title": {"text": "TGV en retard", "side": "top"},
                    "tickformat": ".0%",
                    "orientation": "h",
                    "thickness": 8,
                    "len": 0.3,
                    "x": 0.02,
                    "xanchor": "left",
                    "y": 0.03,
                    "yanchor": "bottom",
                    "bgcolor": "rgba(14, 14, 20, 0.65)",
                    "tickfont": {"color": COULEUR_TEXTE_CARTE},
                    "title_font": {"color": COULEUR_TEXTE_CARTE},
                    "outlinewidth": 0,
                },
            },
            text=survol,
            hovertemplate="%{text}<extra></extra>",
            name="Gares",
        )
    )

    pires = gares_les_plus_touchees(gares, nombre_noms)
    figure.add_trace(
        go.Scattermap(
            lon=pires["longitude"],
            lat=pires["latitude"],
            mode="text",
            text=[_nom_lisible(gare) for gare in pires["gare"]],
            textposition="top center",
            textfont={"color": COULEUR_TEXTE_CARTE, "size": 13},
            hoverinfo="skip",
            name="Gares les plus touchées",
        )
    )

    figure.update_layout(
        map={"style": "carto-darkmatter", "center": CENTRE_FRANCE, "zoom": ZOOM_FRANCE},
        height=HAUTEUR_CARTE,
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        showlegend=False,
        hoverlabel={"bgcolor": "white", "font": {"color": GRAY_900}},
    )
    return figure


def figure_calendrier(par_mois: pd.DataFrame, annee_atypique: int = 2020) -> go.Figure:
    """Calendrier de chaleur : un mois par case, une année par ligne.

    Args:
        par_mois: Résultat de `taux_par_mois`.
        annee_atypique: Année signalée d'un astérisque (confinements).
    """
    grille = par_mois.pivot_table(
        index="annee", columns="mois_numero", values="taux_retard"
    ).reindex(columns=range(1, 13))
    annees = [int(annee) for annee in grille.index]
    survol = [
        [
            ""
            if pd.isna(grille.loc[annee, mois])
            else f"{MOIS_LONGS[mois - 1]} {annee} : "
            f"{fmt_pct(grille.loc[annee, mois])} des TGV en retard de plus de 15 min"
            for mois in range(1, 13)
        ]
        for annee in annees
    ]
    figure = go.Figure(
        go.Heatmap(
            z=grille.to_numpy(),
            x=MOIS_COURTS,
            y=[
                f"{annee} *" if annee == annee_atypique else str(annee)
                for annee in annees
            ],
            colorscale=ECHELLE_CALENDRIER,
            xgap=3,
            ygap=3,
            text=survol,
            hovertemplate="%{text}<extra></extra>",
            colorbar={"tickformat": ".0%", "thickness": 10, "outlinewidth": 0},
        )
    )
    figure.update_layout(
        height=80 + 34 * len(annees),
        margin={"l": 60, "r": 20, "t": 10, "b": 30},
        plot_bgcolor="white",
        xaxis={"side": "top", "showgrid": False, "ticks": "", "showline": False},
        yaxis={
            "autorange": "reversed",
            "showgrid": False,
            "ticks": "",
            "showline": False,
            "type": "category",
        },
    )
    return figure