"""Tests de la séparation visuelle entre observations et prévisions."""

import pandas as pd
import pytest

from railinsight.analysis.prevision_fiabilite import prevoir_fiabilite
from railinsight.viz.prevision_fiabilite import figure_prevision_fiabilite


def test_graphique_affiche_historique_previsions_et_reference():
    mensuel = pd.DataFrame(
        {
            "mois": pd.date_range("2022-01", periods=48, freq="MS"),
            "liaison": "A → B",
            "prevus": 100,
            "incidents": 20,
        }
    )
    resultat = prevoir_fiabilite(mensuel, "A → B")
    figure = figure_prevision_fiabilite(resultat)

    assert len(figure.data) == 3
    assert len(figure.data[0].x) == 24
    assert list(figure.data[0].y) == pytest.approx([80] * 24)
    assert len(figure.data[1].x) == 3
    assert figure.data[1].line.dash == "dash"
    assert figure.data[2].line.dash == "dash"
    assert max(figure.data[0].x) < min(figure.data[1].x)
    assert list(figure.data[1].y) == pytest.approx([80] * 3)
    assert tuple(figure.layout.yaxis.range) == (0, 100)
