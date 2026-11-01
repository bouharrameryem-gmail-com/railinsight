"""Tests de la page Q2 : onglets, filtres et erreurs visibles."""

from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from railinsight.exceptions import DonneesInvalides

PAGE = (
    Path(__file__).parents[4]
    / "src"
    / "railinsight"
    / "ui"
    / "pages"
    / "q2_departure_stations.py"
)


@pytest.fixture
def page_q2(monkeypatch, raw):
    """Affiche la page avec des données locales contrôlées."""
    st.cache_data.clear()
    monkeypatch.setattr(
        "railinsight.backend.retards_gares.charger_donnees", lambda: raw
    )
    yield AppTest.from_file(str(PAGE), default_timeout=30)
    st.cache_data.clear()


def test_page_affiche_chiffres_onglets_et_graphiques(page_q2):
    page_q2.run()

    assert not page_q2.exception
    assert not page_q2.error
    assert not page_q2.warning
    assert [onglet.label for onglet in page_q2.tabs] == [
        "Classements",
        "Causes et croisement",
        "Évolution",
    ]
    assert len(page_q2.metric) == 4
    assert page_q2.metric[0].value == "2"  # PARIS et LYON
    # 2 classements + répartition des causes + évolution d'une gare
    assert len(page_q2.get("plotly_chart")) == 4
    assert any(volet.label == "Méthode et limites" for volet in page_q2.expander)


def test_exclure_2020_change_le_total(page_q2):
    page_q2.run()
    total_sans_2020 = page_q2.metric[1].value

    page_q2.toggle[0].set_value(False).run()

    assert not page_q2.exception
    assert not page_q2.error
    assert page_q2.metric[1].value != total_sans_2020


def test_mode_parts_applique_le_seuil_minimal(page_q2):
    page_q2.run()

    page_q2.radio[0].set_value("Parts").run()

    # Les deux gares ont moins de 1 000 retards : aucune n'est classée.
    assert not page_q2.exception
    assert any("Aucune gare" in info.value for info in page_q2.info)
    assert len(page_q2.get("plotly_chart")) == 2

    page_q2.slider[0].set_value(0).run()

    assert not any("Aucune gare" in info.value for info in page_q2.info)
    assert len(page_q2.get("plotly_chart")) == 4


def test_evolution_par_mois(page_q2):
    page_q2.run()

    page_q2.radio[1].set_value("Par mois").run()

    assert not page_q2.exception
    assert not page_q2.error
    assert len(page_q2.get("plotly_chart")) == 4


def test_donnees_invalides_affichent_un_avertissement(page_q2, monkeypatch):
    def echouer():
        raise DonneesInvalides("Fichier invalide.")

    monkeypatch.setattr("railinsight.backend.retards_gares.charger_donnees", echouer)

    page_q2.run()

    assert not page_q2.exception
    assert not page_q2.error
    assert page_q2.warning[0].value == "Fichier invalide."