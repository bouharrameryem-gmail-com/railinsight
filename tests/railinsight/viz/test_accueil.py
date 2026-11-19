"""Tests des figures de la page d'accueil."""

import pandas as pd
import pytest

from railinsight.analysis.indicateurs_reseau import taux_par_mois
from railinsight.viz.accueil import (
    TAILLE_MAX,
    TAILLE_MIN,
    figure_calendrier,
    figure_carte_gares,
    nom_gare,
)

GARES = pd.DataFrame(
    {
        "gare": ["PARIS LYON", "LYON PART DIEU", "AVIGNON TGV", "PETITE GARE"],
        "latitude": [48.84, 45.76, 43.92, 46.0],
        "longitude": [2.37, 4.86, 4.79, 3.0],
        "trains": [40000, 10000, 8000, 50],
        "taux_retard": [0.10, 0.20, 0.15, 0.90],
        "destinations": [(("MARSEILLE ST CHARLES", 0.3),), (), (), ()],
    }
)


def test_nom_gare():
    assert nom_gare("AVIGNON TGV") == "Avignon TGV"
    assert nom_gare("PARIS LYON") == "Paris Lyon"


def test_carte_sans_reseau():
    figure = figure_carte_gares(GARES)

    gares, noms = figure.data
    tailles = list(gares.marker.size)
    assert tailles[0] == pytest.approx(TAILLE_MAX)
    assert tailles == sorted(tailles, reverse=True)
    assert min(tailles) >= TAILLE_MIN
    assert "Marseille St Charles : 30,0" in gares.text[0]
    # La petite gare, malgré son taux, n'est pas nommée.
    assert list(noms.text) == ["Lyon Part Dieu", "Avignon TGV", "Paris Lyon"]
    assert figure.layout.map.style == "carto-darkmatter"


def test_carte_avec_reseau():
    reseau = [[(2.0, 48.0), (3.0, 47.0)], [(4.0, 45.0), (5.0, 44.0)]]

    figure = figure_carte_gares(GARES, reseau)

    lignes = figure.data[0]
    assert lignes.mode == "lines"
    assert list(lignes.lon) == [2.0, 3.0, None, 4.0, 5.0, None]
    assert len(figure.data) == 3


def test_carte_sans_trafic():
    figure = figure_carte_gares(GARES.assign(trains=0))
    assert set(figure.data[0].marker.size) == {TAILLE_MIN}


def test_calendrier():
    par_mois = taux_par_mois(
        pd.DataFrame(
            {
                "date": pd.to_datetime(["2020-01-01", "2020-02-01", "2021-01-01"]),
                "retards_sup_15min": [10.0, 20.0, 30.0],
                "circules": [100.0, 100.0, 100.0],
            }
        )
    )

    figure = figure_calendrier(par_mois)

    carte = figure.data[0]
    assert list(carte.y) == ["2020 *", "2021"]
    assert carte.z.shape == (2, 12)
    assert carte.z[1][0] == pytest.approx(0.3)
    assert carte.text[0][1].startswith("février 2020 : 20,0")
    assert carte.text[1][5] == ""


def test_carte_detaille_les_gares_regroupees():
    regroupees = GARES.head(1).assign(
        gare="PARIS", membres=[(("PARIS LYON", 0.1), ("PARIS NORD", 0.2))]
    )

    texte = figure_carte_gares(regroupees).data[0].text[0]

    assert "Gares regroupées" in texte
    assert "Paris Nord : 20,0" in texte