"""Tests des figures de la Q2."""

from railinsight.analysis.causes_retards import DELAY_COLUMNS
from railinsight.viz import retards_gares, figure_classement_gares
import pandas as pd


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

    figure = figure_classement_gares(classement, "retard_non_heritees", "#FF6B35")

    assert len(figure.data) == 1
    # La première gare du classement est dessinée en haut, donc en dernier.
    assert list(figure.data[0].y) == ["LILLE", "LYON", "PARIS"]
    assert list(figure.data[0].x) == [1000.0, 2000.0, 3000.0]
    assert "3" in figure.data[0].text[-1]
    assert figure.data[0].marker.color == "#FF6B35"
