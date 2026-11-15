"""Tests des graphiques interactifs de la Q1."""

import pandas as pd
import pytest

from railinsight.viz.liaisons_fiabilite import figure_comparaison_liaisons


@pytest.fixture
def donnees_mensuelles():
    """Deux liaisons avec des taux connus pour vérifier l'agrégation annuelle."""
    return pd.DataFrame(
        [
            ("PARIS → LYON", "2024-01-01", 100, 10),
            ("PARIS → LYON", "2024-02-01", 300, 90),
            ("LYON → LILLE", "2024-01-01", 100, 50),
            ("LYON → LILLE", "2024-02-01", 100, 0),
        ],
        columns=["liaison", "mois", "prevus", "incidents"],
    ).assign(
        mois=lambda table: pd.to_datetime(table["mois"]),
        taux_incidents=lambda table: table["incidents"] / table["prevus"],
    )


def test_comparaison_mensuelle_affiche_les_series_et_la_fenetre_covid(
    donnees_mensuelles,
):
    figure = figure_comparaison_liaisons(
        donnees_mensuelles,
        ["PARIS → LYON", "LYON → LILLE"],
        "2020-03",
        "2021-06",
    )

    assert len(figure.data) == 2
    assert list(figure.data[0].y) == pytest.approx([10, 30])
    assert len(figure.layout.shapes) == 1


def test_comparaison_annuelle_recalcule_un_ratio_de_sommes(donnees_mensuelles):
    figure = figure_comparaison_liaisons(
        donnees_mensuelles,
        ["PARIS → LYON", "LYON → LILLE"],
        "2020-03",
        "2021-06",
        pas_de_temps="Annuel",
    )

    assert len(figure.data) == 2
    assert list(figure.data[0].y) == pytest.approx([25])
    assert list(figure.data[1].y) == pytest.approx([25])
    assert len(figure.layout.shapes) == 0
