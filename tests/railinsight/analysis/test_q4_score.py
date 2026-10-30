"""Tests du score de fiabilité (Q4)."""

import pandas as pd
import pytest

from railinsight.analysis.q4_score_fiabilite import (
    REFERENCE,
    add_score,
    aggregate_by_link,
    compare_variants,
    default_variants,
    prepare_data,
)
from railinsight.backend.q4_score_fiabilite import compute_reliability
from railinsight.config import ScoreFiabilite
from railinsight.exceptions import DonneesInvalides


@pytest.fixture
def raw():
    return pd.DataFrame(
        {
            "date": ["2024-01", "2024-01", "2024-01", "2024-02", "2024-01", "2024-01"],
            "gare_depart": ["Paris", "Lyon", "Nantes", "Nantes", "Lille", "Marseille"],
            "gare_arrivee": ["Lyon", "Paris", "Paris", "Paris", "Paris", "Paris"],
            "prevus": [100.0, 100.0, 100.0, 100.0, 50.0, 0.0],
            "annules": [6.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "retard_moyen_arrivee": [12.0, 0.0, 0.0, -472.0, 3.0, 0.0],
        }
    )


def scored(raw, **kwargs):
    return add_score(aggregate_by_link(prepare_data(raw), min_trains=100), **kwargs)


def test_score_par_liaison(raw):
    copie = raw.copy()
    links = scored(raw).set_index("liaison")

    pd.testing.assert_frame_equal(raw, copie)
    # la liaison sous 100 trains et la ligne sans train prévu sont écartées
    assert set(links.index) == {"LYON - PARIS", "NANTES - PARIS"}
    lyon = links.loc["LYON - PARIS"]
    assert lyon["taux_annulation"] == pytest.approx(3.0)
    assert lyon["retard_moyen"] == pytest.approx(1128 / 194)
    assert lyon["score"] == pytest.approx(50.77, abs=0.01)
    assert lyon["categorie"] == "Peu fiable"


def test_retard_impossible_invalide_sans_perdre_la_ligne(raw):
    nantes = scored(raw).set_index("liaison").loc["NANTES - PARIS"]
    assert nantes["prevus"] == 200  # la ligne à -472 min est conservée
    assert nantes["retard_moyen"] == 0  # mais son retard est ignoré
    assert nantes["score"] == pytest.approx(100)
    assert nantes["categorie"] == "Très fiable"


def test_filtre_periode(raw):
    table = prepare_data(raw, start="2024-02")
    assert table["mois"].unique().tolist() == ["2024-02"]


def test_colonne_manquante(raw):
    with pytest.raises(DonneesInvalides, match="prevus"):
        prepare_data(raw.drop(columns=["prevus"]))


def test_comparaison_de_variantes(raw):
    totals = aggregate_by_link(prepare_data(raw), min_trains=100)
    params = {"weight": 0.5, "cap_cancellation": 6.0, "cap_delay": 12.0}
    variants = {REFERENCE: params, "identique": params}
    result = compare_variants(totals, variants, top_n=1)

    assert list(result.index) == ["identique"]
    assert result.loc["identique", "correlation"] == pytest.approx(1.0)
    assert result.loc["identique", "top_overlap"] == 1
    assert REFERENCE in default_variants(**params)


def test_backend_sans_fichier(raw):
    params = ScoreFiabilite(
        periode_debut=None,
        periode_fin=None,
        min_trains=100,
        poids=0.5,
        cap_annulation=6.0,
        cap_retard=12.0,
        gare_a_suivre=None,
        top_n=1,
    )
    result = compute_reliability(raw, params)

    assert result["links"]["liaison"].tolist() == ["NANTES - PARIS", "LYON - PARIS"]
    assert set(result["network"].index) >= {"score", "taux_annulation"}
    assert len(result["robustness"]) == 4
