"""Tests du score et du dessin issus du notebook Q4."""

import pandas as pd
import pytest

from railinsight.analysis.graphe_reseau import positions_gares
from railinsight.analysis.nettoyage import nettoyer_regularite
from railinsight.analysis.score_fiabilite import (
    ParametresScore,
    calculer_score,
    categoriser,
    preparer_table_score,
    scores_par_liaison,
)
from railinsight.viz.fiabilite import (
    figure_classement,
    figure_reseau,
)


def test_score_reprend_la_formule_du_notebook(donnees_fiabilite):
    table = preparer_table_score(nettoyer_regularite(donnees_fiabilite))
    notes = scores_par_liaison(table[table["mois"] == "2024-01"], ParametresScore())
    ligne = notes.set_index("liaison").loc["LYON - PARIS"]
    retard = (100 * 2 + 288 * 6) / 388
    attendu = 100 * (1 - 0.5 * (12 / 400 / 0.06) - 0.5 * (retard / 12))
    assert ligne["prevus"] == 400
    assert ligne["retard_moyen"] == pytest.approx(retard)
    assert ligne["note"] == pytest.approx(attendu)
    assert set(notes["liaison"]) == {"LYON - PARIS", "BRUXELLES - PARIS"}
    assert notes["note"].is_monotonic_decreasing


def test_categories_aux_seuils():
    notes = pd.Series([0, 39.99, 40, 55, 70, 85, 100, float("nan")])
    categories = categoriser(notes)
    assert categories.iloc[:-1].tolist() == [
        "À risque",
        "À risque",
        "Peu fiable",
        "Moyenne",
        "Fiable",
        "Très fiable",
        "Très fiable",
    ]
    assert pd.isna(categories.iloc[-1])


@pytest.mark.parametrize(
    "poids,annulation,retard",
    [
        (-1, 0.06, 12),
        (2, 0.06, 12),
        (0.5, 0, 12),
        (0.5, 0.06, -1),
        (float("nan"), 0.06, 12),
        (0.5, float("inf"), 12),
    ],
)
def test_parametres_invalides(poids, annulation, retard):
    with pytest.raises(ValueError):
        ParametresScore(poids, annulation, retard)


def test_notes_bornees_et_retard_absent():
    totaux = pd.DataFrame(
        {
            "prevus": [100, 100, 100, 100],
            "annules": [0, 50, 0, 100],
            "circules_mesures": [100, 50, 100, 0],
            "minutes_retard": [0, 1500, -100, 0],
        }
    )
    notes = calculer_score(totaux, ParametresScore())["note"]
    assert notes.iloc[:3].tolist() == [100, 0, 100]
    assert pd.isna(notes.iloc[3])


def test_retard_manquant_ne_dilue_pas_la_moyenne(donnees_fiabilite):
    brut = donnees_fiabilite.iloc[[0, 1]].copy()
    brut.loc[1, "retard_moyen_arrivee"] = -20
    table = preparer_table_score(nettoyer_regularite(brut))
    ligne = scores_par_liaison(table, ParametresScore()).iloc[0]
    assert ligne["prevus"] == 400
    assert ligne["annules"] == 12
    assert ligne["circules_mesures"] == 100
    assert ligne["retard_moyen"] == 2


def test_nettoyage_ecarte_les_lignes_invalides(donnees_fiabilite, caplog):
    brut = donnees_fiabilite.copy()
    brut.loc[0, "annules"] = -1
    brut.loc[1, "prevus"] = 0
    brut.loc[2, "date"] = "invalide"
    brut.loc[3, "gare_depart"] = ""
    table = preparer_table_score(nettoyer_regularite(brut))
    assert len(table) == 2
    assert "retirée(s)" in caplog.text


def test_positions_stables_et_filtre_gare(donnees_fiabilite):
    table = preparer_table_score(nettoyer_regularite(donnees_fiabilite))
    notes = scores_par_liaison(table, ParametresScore())
    aretes = list(zip(table["gare_a"], table["gare_b"], strict=True))
    positions = positions_gares(aretes)
    assert positions == positions_gares(reversed(aretes))
    figure = figure_reseau(notes, positions, gare="PARIS")
    assert set(figure.data[-1].text) == {"PARIS", "LYON", "BRUXELLES"}
    textes = [texte for trace in figure.data[:-1] for texte in (trace.text or [])]
    assert len(textes) == 2
    assert all("Note :" in texte and "Trains supprimés :" in texte for texte in textes)
    for trace in figure.data[:-1]:
        assert trace.legendgroup
    assert figure.data[0].legendgroup == figure.data[1].legendgroup


@pytest.mark.parametrize("meilleures", [True, False])
def test_classement_notes_et_ordre(donnees_fiabilite, meilleures):
    table = preparer_table_score(nettoyer_regularite(donnees_fiabilite))
    notes = scores_par_liaison(table, ParametresScore())
    figure = figure_classement(notes, 1, meilleures)
    attendue = notes.iloc[0 if meilleures else -1]
    assert len(figure.data) == 1
    assert list(figure.data[0].y) == [attendue["liaison"]]
    assert list(figure.data[0].x) == [attendue["note"]]
    assert list(figure.layout.yaxis.categoryarray) == [attendue["liaison"]]
