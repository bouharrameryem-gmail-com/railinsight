"""Tests de l'accueil via la navigation Streamlit, sans accès réseau."""

from pathlib import Path

import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from railinsight.exceptions import DonneesInvalides

# st.page_link requires st.navigation context, so tests must run through the
# full app entrypoint (app.py) rather than home.py directly.
_ROOT = Path(__file__).parents[3]


def donnees_accueil():
    return pd.DataFrame(
        {
            "mois": pd.period_range("2024-10", "2026-09", freq="M").astype(str),
            "gare_depart": "PARIS LYON",
            "gare_arrivee": "LYON PART DIEU",
            "liaison": "LYON PART DIEU - PARIS LYON",
            "prevus": 100.0,
            "annules": 10.0,
            "circules": 90.0,
            "retards_sup_15min": [9.0] * 12 + [18.0] * 12,
        }
    )


@pytest.fixture(autouse=True)
def source_hors_reseau(monkeypatch):
    """Garde les tests de l'accueil indépendants de la disponibilité de SNCF."""
    monkeypatch.setattr(
        "railinsight.ui.source_donnees.afficher_source_donnees", lambda: True
    )
    monkeypatch.setattr(
        "railinsight.backend.profils_ponctualite.charger_donnees_clean",
        donnees_accueil,
    )
    st.cache_data.clear()
    yield
    st.cache_data.clear()


def test_home_page_renders():
    at = AppTest.from_file(str(_ROOT / "app.py"), default_timeout=30)
    at.run()
    assert not at.exception


def test_home_page_has_content():
    at = AppTest.from_file(str(_ROOT / "app.py"), default_timeout=30)
    at.run()
    assert at.title[0].value == "Comprendre la ponctualité et la fiabilité des TGV"
    assert not at.info
    assert len(at.expander) == 3
    assert any("national" in texte.value for texte in at.markdown)
    assert any("octobre 2025" in texte.value for texte in at.markdown)
    assert any("septembre 2026" in texte.value for texte in at.markdown)
    assert at.metric[0].value == "1"
    assert not at.error
    assert len(at.get("plotly_chart")) == 1


def test_indicateurs_incomplets_sans_faux_zero(monkeypatch):
    donnees = pd.DataFrame(
        {
            "mois": ["2026-09"],
            "gare_depart": ["A"],
            "gare_arrivee": ["B"],
            "liaison": ["A - B"],
            "prevus": [100.0],
            "annules": [float("nan")],
            "circules": [float("nan")],
            "retards_sup_15min": [float("nan")],
        }
    )
    monkeypatch.setattr(
        "railinsight.backend.profils_ponctualite.charger_donnees_clean",
        lambda: donnees,
    )
    at = AppTest.from_file(str(_ROOT / "app.py"), default_timeout=30).run()
    assert not at.exception
    assert "1 mois" in at.warning[0].value
    assert at.metric[1].value == "Non disponible"
    assert at.metric[2].value == "Non disponible"
    assert any("ligne(s) exclue(s)" in c.value for c in at.caption)
    assert len(at.get("page_link")) == 4


def test_erreur_bilan_garde_navigation(monkeypatch):
    def erreur():
        raise DonneesInvalides("Données de test indisponibles")

    monkeypatch.setattr(
        "railinsight.backend.profils_ponctualite.charger_donnees_clean", erreur
    )
    at = AppTest.from_file(str(_ROOT / "app.py"), default_timeout=30).run()
    assert not at.exception
    assert "Indicateurs indisponibles" in at.error[0].value
    assert len(at.get("page_link")) == 4


def test_variations_en_points_sur_perimetre_comparable():
    at = AppTest.from_file(str(_ROOT / "app.py"), default_timeout=30).run()
    assert not at.exception
    assert at.metric[1].delta == "+10,0 pts"
    assert at.metric[2].delta == "+0,0 pts"
    assert not any("Évolution non disponible" in c.value for c in at.caption)


def test_quatre_analyses_presentees_avant_le_bilan_et_la_carte():
    at = AppTest.from_file(str(_ROOT / "app.py"), default_timeout=30).run()
    assert not at.exception
    assert not at.main.button
    liens = [(lien.proto.label, lien.proto.page) for lien in at.get("page_link")]
    assert liens == [
        ("Comparer les liaisons et leurs tendances", "q1_liaisons_fiabilite"),
        ("Explorer les retards par gare", "q2_departure_stations"),
        ("Découvrir les profils de ponctualité", "ponctualite_liaisons"),
        ("Consulter les scores de fiabilité", "q4_score_fiabilite"),
    ]
    assert [
        element.type
        for element in at.main
        if element.type in {"page_link", "metric", "plotly_chart"}
    ] == [
        *["page_link"] * 4,
        *["metric"] * 3,
        "plotly_chart",
    ]


def test_filtre_carte_et_couverture_inconnue(monkeypatch):
    source = donnees_accueil()
    autre = source.assign(
        gare_depart="NANTES", gare_arrivee="RENNES", liaison="NANTES - RENNES"
    )
    inconnue = source.assign(
        gare_depart="INCONNUE", gare_arrivee="RENNES", liaison="INCONNUE - RENNES"
    )
    monkeypatch.setattr(
        "railinsight.backend.profils_ponctualite.charger_donnees_clean",
        lambda: pd.concat([source, autre, inconnue], ignore_index=True),
    )
    at = AppTest.from_file(str(_ROOT / "app.py"), default_timeout=30).run()
    assert not at.exception
    assert any("Coordonnées absentes" in w.value for w in at.warning)
    assert len(at.dataframe[0].value) == 3
    at.selectbox[0].set_value("NANTES").run()
    assert not at.exception
    assert not at.warning
    assert len(at.dataframe[0].value) == 1
    assert at.dataframe[0].value.iloc[0, 0] == "NANTES ↔ RENNES"
    at.selectbox[0].set_value("INCONNUE").run()
    assert not at.exception
    assert not at.get("plotly_chart")
    assert any("coordonnées de cette sélection" in info.value for info in at.info)
    assert len(at.dataframe[0].value) == 1


def test_gare_disparue_reinitialise_le_filtre():
    at = AppTest.from_file(str(_ROOT / "app.py"), default_timeout=30)
    at.session_state["accueil_gare_carte"] = "GARE SUPPRIMÉE"
    at.run()
    assert not at.exception
    assert at.selectbox[0].value == "Tout le réseau"
