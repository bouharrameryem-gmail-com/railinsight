"""Tests de la page Streamlit Q1."""

from pathlib import Path

import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from railinsight.analysis.liaisons_fiabilite import (
    calculer_analyse_liaisons_fiabilite,
)

PAGE = (
    Path(__file__).parents[4]
    / "src"
    / "railinsight"
    / "ui"
    / "pages"
    / "q1_liaisons_fiabilite.py"
)


@pytest.fixture
def page_q1(monkeypatch):
    """Affiche Q1 avec des données locales contrôlées."""
    donnees = pd.DataFrame(
        [
            ("2024-01", "PARIS", "LYON", 100, 0, 10, 60),
            ("2024-02", "PARIS", "LYON", 100, 0, 20, 60),
            ("2024-01", "LYON", "LILLE", 100, 0, 30, 120),
            ("2024-02", "LYON", "LILLE", 100, 0, 20, 120),
        ],
        columns=[
            "date",
            "gare_depart",
            "gare_arrivee",
            "prevus",
            "annules",
            "retards_sup_15min",
            "duree_moyenne",
        ],
    )
    donnees["date"] = pd.to_datetime(donnees["date"])
    donnees["circules"] = donnees["prevus"] - donnees["annules"]
    analyse = calculer_analyse_liaisons_fiabilite(
        donnees, covid_debut="2020-03", covid_fin="2021-06"
    )
    st.cache_data.clear()
    monkeypatch.setattr(
        "railinsight.backend.liaisons_fiabilite.charger_analyse_liaisons_fiabilite",
        lambda: analyse,
    )
    yield AppTest.from_file(str(PAGE), default_timeout=30)
    st.cache_data.clear()


def test_page_affiche_classement_tendances_et_methodologie(page_q1):
    page_q1.run()

    assert not page_q1.exception
    assert not page_q1.error
    assert not page_q1.warning
    assert [onglet.label for onglet in page_q1.tabs] == [
        "Classement",
        "Évolution et tendances",
        "À durée égale",
    ]
    assert len(page_q1.get("plotly_chart")) == 3
    assert any(volet.label == "Méthode et limites" for volet in page_q1.expander)


def test_nombre_de_liaisons_est_interactif(page_q1):
    page_q1.run()
    page_q1.number_input[0].set_value(1).run()

    assert not page_q1.exception
    assert not page_q1.error
    assert len(page_q1.get("plotly_chart")) == 3
