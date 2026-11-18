"""Tests des figures de la Q2."""

import pandas as pd
import pytest

from railinsight.analysis.causes_retards import DELAY_COLUMNS, Evolution
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

    figure = retards_gares.figure_classement_gares(
        classement, "retard_non_heritees", "#FF6B35"
    )

    assert len(figure.data[0].x) == 0
    assert figure.layout.xaxis.range[1] == pytest.approx(1.15)


@pytest.fixture
def evolution():
    return pd.DataFrame(
        {
            "annee": [2022, 2019, 2021],
            "retard_heritees": [30.0, 10.0, 20.0],
            "retard_non_heritees": [300.0, 100.0, 200.0],
            "retard_externes": [3.0, 1.0, 2.0],
        }
    )


def test_evolution_triee_dans_le_temps(evolution):
    figure = retards_gares.figure_evolution_gare(evolution, "annee")

    assert len(figure.data) == 3
    assert list(figure.data[0].x) == [2019, 2021, 2022]
    assert list(figure.data[1].y) == [100.0, 200.0, 300.0]
    assert figure.data[1].name == "Retards nés sur place"


def test_evolution_annuelle_graduation_entiere(evolution):
    figure = retards_gares.figure_evolution_gare(evolution, "annee")

    assert figure.layout.xaxis.dtick == 1
    assert figure.layout.xaxis.tickformat == "d"


def test_classement_avec_ligne_de_moyenne():
    classement = pd.DataFrame(
        {"gare_depart": ["PARIS", "LYON"], "taux_heritees": [0.10, 0.05]}
    )

    figure = retards_gares.figure_classement_gares(
        classement, "taux_heritees", "#003F88", en_part=True, reference=0.3
    )

    assert len(figure.layout.shapes) == 1
    assert "Moyenne" in figure.layout.annotations[0].text
    # La moyenne dépasse toutes les barres : l'axe s'élargit pour l'afficher.
    assert figure.layout.xaxis.range[1] == pytest.approx(0.3 * 1.15)


@pytest.fixture
def reseau_annuel():
    return pd.DataFrame(
        {
            "annee": [2020, 2019],
            "taux_heritees": [0.3, 0.2],
            "taux_non_heritees": [0.5, 0.6],
            "taux_externes": [0.2, 0.2],
        }
    )


def test_aire_parts_empile_les_trois_familles(reseau_annuel):
    figure = retards_gares.figure_aire_parts(
        reseau_annuel, Evolution(2019, 0.2, 2020, 0.3)
    )

    assert [trace.name for trace in figure.data] == [
        "Retards importés",
        "Retards nés sur place",
        "Causes extérieures",
    ]
    assert all(trace.stackgroup == "parts" for trace in figure.data)
    assert list(figure.data[0].x) == [2019, 2020]
    textes = [annotation.text for annotation in figure.layout.annotations]
    assert len(textes) == 2
    assert textes[0].startswith("20")
    assert textes[1].startswith("30")


def test_aire_parts_sans_evolution(reseau_annuel):
    figure = retards_gares.figure_aire_parts(reseau_annuel)

    assert len(figure.layout.annotations) == 0
