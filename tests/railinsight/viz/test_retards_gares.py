"""Tests des figures de la Q2."""

import pandas as pd
import pytest

from railinsight.analysis.causes_retards import DELAY_COLUMNS
from railinsight.viz import retards_gares


def test_constantes_couvrent_toutes_les_categories():
    for constante in (
        retards_gares.COULEURS_CATEGORIES,
        retards_gares.LIBELLES_CATEGORIES,
        retards_gares.PARTS_CATEGORIES,
    ):
        assert list(constante) == DELAY_COLUMNS


def test_classement_ordre_et_valeurs():
    classement = pd.DataFrame(
        {
            "gare_depart": ["PARIS", "LYON", "LILLE"],
            "retard_non_heritees": [3000.0, 2000.0, 1000.0],
        }
    )

    figure = retards_gares.figure_classement_gares(
        classement, "retard_non_heritees", "#FF6B35"
    )

    assert len(figure.data) == 1
    # La première gare du classement est dessinée en haut, donc en dernier.
    assert list(figure.data[0].y) == ["LILLE", "LYON", "PARIS"]
    assert list(figure.data[0].x) == [1000.0, 2000.0, 3000.0]
    assert "3" in figure.data[0].text[-1]
    assert figure.data[0].marker.color == "#FF6B35"


def test_classement_en_part():
    classement = pd.DataFrame(
        {"gare_depart": ["PARIS", "LYON"], "taux_non_heritees": [0.8, 0.5]}
    )

    figure = retards_gares.figure_classement_gares(
        classement, "taux_non_heritees", "#FF6B35", en_part=True
    )

    assert "80" in figure.data[0].text[-1]
    assert "%" in figure.data[0].text[-1]
    assert figure.layout.xaxis.tickformat == ".0%"
    assert figure.layout.xaxis.range[1] == pytest.approx(0.8 * 1.15)


def test_classement_vide_ne_plante_pas():
    classement = pd.DataFrame({"gare_depart": [], "retard_non_heritees": []})

    figure = retards_gares.figure_classement_gares(classement, "retard_non_heritees", "#FF6B35")

    assert len(figure.data[0].x) == 0
    assert figure.layout.xaxis.range[1] == pytest.approx(1.15)