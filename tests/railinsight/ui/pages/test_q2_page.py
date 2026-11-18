"""Tests de la page Q2 : sections, réglages, portrait et erreurs visibles."""

import logging
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

TITRES_PAR_DEFAUT = [
    "Un retard peut naître sur place, être importé, ou venir de l'extérieur",
    "PARIS est en tête des deux côtés : elle fabrique et encaisse le plus de retards",
    "Aucune gare n'atteint le seuil choisi",
    "2 gares fabriquent et encaissent à la fois",
    "Choisissez une gare : la page vous la raconte",
]


@pytest.fixture
def page_q2(monkeypatch, raw):
    """Affiche la page avec des données locales contrôlées."""
    st.cache_data.clear()
    monkeypatch.setattr(
        "railinsight.backend.retards_gares.charger_donnees", lambda: raw
    )
    yield AppTest.from_file(str(PAGE), default_timeout=30)
    st.cache_data.clear()


def _texte(page, morceau):
    """Indique si un bloc Markdown de la page contient le morceau cherché."""
    return any(morceau in bloc.value for bloc in page.markdown)


def _total_retards(page):
    """Renvoie la légende qui donne le nombre total de retards."""
    return next(
        legende.value
        for legende in page.caption
        if "trains arrivés en retard" in legende.value
    )


def test_page_deroule_les_cinq_sections(page_q2):
    page_q2.run()

    assert not page_q2.exception
    assert not page_q2.error
    assert not page_q2.warning
    assert [titre.value for titre in page_q2.subheader] == TITRES_PAR_DEFAUT
    # Aire des parts, 2 classements en volume, gares carrefours,
    # comparaison de la gare choisie et son évolution.
    assert len(page_q2.get("plotly_chart")) == 6
    assert "160 trains arrivés en retard" in _total_retards(page_q2)
    volets = [volet.label for volet in page_q2.expander]
    assert "Méthode et limites" in volets
    assert "Voir le détail des rangs" in volets


def test_sections_numerotees_avec_leur_question(page_q2):
    page_q2.run()

    for numero, question in enumerate(
        [
            "D'où vient un retard ?",
            "Qui fabrique, qui encaisse ?",
            "Et à trafic égal ?",
            "Qui est des deux côtés ?",
            "Et votre gare ?",
        ],
        start=1,
    ):
        assert _texte(page_q2, f"{numero:02d}</span>")
        assert _texte(page_q2, question)


def test_question_en_grand_et_chiffres_cles(page_q2):
    page_q2.run()

    assert _texte(page_q2, "Quand votre TGV arrive en retard")
    assert _texte(page_q2, "font-size:2rem")
    assert len(page_q2.metric) == 4
    assert page_q2.metric[0].value == "2"  # PARIS et LYON


def test_portrait_de_la_gare_par_defaut(page_q2):
    page_q2.run()

    portrait = next(
        bloc.value for bloc in page_q2.markdown if "font-size:1.3rem" in bloc.value
    )
    assert "des retards sont importés" in portrait
    assert "%</strong>" in portrait
    assert "proche de la moyenne des gares" in portrait
    assert "la 1re gare sur 2" in portrait
    assert "à lire avec prudence" in portrait


def test_vue_par_mois_nomme_le_mois_le_plus_charge(page_q2):
    page_q2.run()

    page_q2.radio[0].set_value("Par mois").run()

    assert not page_q2.exception
    assert not page_q2.error
    assert _texte(page_q2, "Son mois le plus chargé est janvier 2024")


def test_exclure_2020_change_les_chiffres(page_q2):
    page_q2.run()
    total_sans_2020 = _total_retards(page_q2)

    page_q2.toggle[0].set_value(False).run()

    assert not page_q2.exception
    assert not page_q2.error
    assert _total_retards(page_q2) != total_sans_2020


def test_seuil_a_zero_affiche_les_classements_en_parts(page_q2):
    page_q2.run()

    page_q2.slider[0].set_value(0).run()

    assert not page_q2.exception
    assert not page_q2.error
    assert len(page_q2.get("plotly_chart")) == 8
    assert page_q2.subheader[2].value.startswith(
        "Rapportée à son trafic, PARIS est la plus exposée"
    )


def test_reglage_journalise(page_q2, caplog):
    caplog.set_level(logging.INFO, logger="railinsight")
    page_q2.run()

    page_q2.toggle[0].set_value(False).run()

    assert "exclure_2020 = False" in caplog.text


def test_donnees_invalides_affichent_un_avertissement(page_q2, monkeypatch):
    def echouer():
        raise DonneesInvalides("Fichier invalide.")

    monkeypatch.setattr("railinsight.backend.retards_gares.charger_donnees", echouer)

    page_q2.run()

    assert not page_q2.exception
    assert not page_q2.error
    assert page_q2.warning[0].value == "Fichier invalide."
